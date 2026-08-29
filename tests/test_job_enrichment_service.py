from uuid import uuid4

from app.db.database import SessionLocal
from app.models.job import Job
from app.models.raw_job import RawJob
from app.services.job_enrichment_service import (
    backfill_job_enrichment,
)


def test_backfill_job_enrichment_is_safe_to_rerun():
    source_job_id = (
        f"enrich-{uuid4().hex[:16]}"
    )
    session = SessionLocal()

    try:
        job = Job(
            source="104",
            source_job_id=source_job_id,
            title="Python FastAPI 工程師",
            company_name="Enrichment 測試公司",
            location="台北市",
            description=(
                "使用 Python、FastAPI 與 PostgreSQL"
            ),
            job_category="UNKNOWN",
            tech_stack=[],
            url=(
                "https://www.104.com.tw/job/"
                f"{source_job_id}"
            ),
            experience="1年以上",
            content_hash="old-hash",
        )
        raw_job = RawJob(
            source="104",
            source_job_id=source_job_id,
            source_url=job.url,
            raw_data={
                "search": {},
                "detail": {
                    "jobDetail": {
                        "salary": (
                            "月薪45,000~60,000元"
                        )
                    }
                },
            },
            content_hash="raw-hash",
        )
        session.add_all([job, raw_job])
        session.flush()

        first = backfill_job_enrichment(
            session,
            [source_job_id],
        )
        session.flush()
        first_hash = job.content_hash

        second = backfill_job_enrichment(
            session,
            [source_job_id],
        )
        session.flush()

        assert first == {
            "scanned": 1,
            "updated": 1,
            "salary_updated": 1,
        }
        assert job.salary_text == (
            "月薪45,000~60,000元"
        )
        assert job.tech_stack == [
            "Python",
            "FastAPI",
            "PostgreSQL",
        ]
        assert job.content_hash == first_hash
        assert second == {
            "scanned": 1,
            "updated": 0,
            "salary_updated": 0,
        }
    finally:
        session.rollback()
        session.close()
