from sqlalchemy import func, select

from app.crawler.job_classifier import (
    classify_job,
)
from app.crawler.job_enrichment import (
    extract_salary_text,
)
from app.crawler.tech_extractor import (
    extract_tech_stack,
)
from app.crawler.transform import (
    generate_content_hash,
)
from app.models.job import Job
from app.models.raw_job import RawJob


def _latest_raw_data_by_job_id(
    session,
    source_job_ids=None,
):
    rank = func.row_number().over(
        partition_by=RawJob.source_job_id,
        order_by=(
            RawJob.crawled_at.desc(),
            RawJob.id.desc(),
        ),
    ).label("snapshot_rank")

    ranked_statement = select(
        RawJob.source_job_id,
        RawJob.raw_data,
        rank,
    )

    if source_job_ids is not None:
        ranked_statement = (
            ranked_statement.where(
                RawJob.source_job_id.in_(
                    source_job_ids
                )
            )
        )

    ranked = ranked_statement.subquery()
    rows = session.execute(
        select(
            ranked.c.source_job_id,
            ranked.c.raw_data,
        ).where(
            ranked.c.snapshot_rank == 1
        )
    ).all()

    return dict(rows)


def backfill_job_enrichment(
    session,
    source_job_ids=None,
):
    """只以 clean jobs 與最新 raw snapshot 回填，可安全重跑。"""

    job_statement = select(Job).order_by(
        Job.id
    )

    if source_job_ids is not None:
        source_job_ids = tuple(
            str(value)
            for value in source_job_ids
        )
        job_statement = job_statement.where(
            Job.source_job_id.in_(
                source_job_ids
            )
        )

    jobs = session.scalars(
        job_statement
    ).all()
    raw_by_job_id = (
        _latest_raw_data_by_job_id(
            session,
            source_job_ids,
        )
    )

    updated_count = 0
    salary_updated_count = 0

    for job in jobs:
        original_state = (
            job.job_category,
            tuple(job.tech_stack or []),
            job.salary_text,
            job.content_hash,
        )

        job.job_category = classify_job(
            job.title,
            job.description or "",
        )
        job.tech_stack = extract_tech_stack(
            job.title,
            job.description or "",
        )

        raw_data = raw_by_job_id.get(
            job.source_job_id
        )
        salary_text = None
        if raw_data:
            salary_text = extract_salary_text(
                raw_data.get("detail", {})
            )

        if (
            salary_text is not None
            and job.salary_text != salary_text
        ):
            job.salary_text = salary_text
            salary_updated_count += 1

        # salary_text 現在是 source content 的一部分；同步重算 hash，
        # 避免下次 refresh 只因 hash 演算法升級而誤報 JD 更新。
        job.content_hash = generate_content_hash(
            {
                "job_name": job.title,
                "company_name": (
                    job.company_name
                ),
                "location": job.location or "",
                "description": (
                    job.description or ""
                ),
                "experience": (
                    job.experience or ""
                ),
                "education": (
                    job.education or ""
                ),
                "salary_text": (
                    job.salary_text or ""
                ),
            }
        )

        current_state = (
            job.job_category,
            tuple(job.tech_stack or []),
            job.salary_text,
            job.content_hash,
        )
        if current_state != original_state:
            updated_count += 1

    return {
        "scanned": len(jobs),
        "updated": updated_count,
        "salary_updated": (
            salary_updated_count
        ),
    }
