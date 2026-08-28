from uuid import uuid4

from app.crawler.transform import generate_content_hash
from app.db.database import SessionLocal
from app.repositories.job_repository import JobRepository


def build_test_job(
    job_no,
    description="需要 Python",
):
    job = {
        "job_name": "測試資料工程師",
        "company_name": "測試公司",
        "location": "台北市",
        "job_no": job_no,
        "url": f"https://www.104.com.tw/job/{job_no}",
        "description_summary": "測試摘要",
        "description": description,
        "experience": "1年以上",
        "education": "大學以上",
    }

    job["content_hash"] = generate_content_hash(job)

    return job


def test_job_repository_upsert():

    # 每次測試都產生不同 ID
    # 避免跟資料庫原本的資料撞到
    job_no = f"test-{uuid4().hex}"

    session = SessionLocal()

    try:
        repository = JobRepository(session)

        # =========================
        # 第一次：NEW
        # =========================

        first_job = build_test_job(
            job_no=job_no,
            description="需要 Python",
        )

        result = repository.upsert(
            first_job
        )

        session.flush()

        assert result == "new"

        saved_job = (
            repository.find_by_source_job_id(
                job_no
            )
        )

        assert saved_job is not None
        assert saved_job.title == "測試資料工程師"
        assert saved_job.description == "需要 Python"
        assert saved_job.content_updated_at is None
        assert (
            saved_job.last_detail_checked_at
            is not None
        )

        original_first_seen_at = (
            saved_job.first_seen_at
        )
        original_detail_checked_at = (
            saved_job.last_detail_checked_at
        )


        # =========================
        # 第二次：UNCHANGED
        # =========================

        same_job = build_test_job(
            job_no=job_no,
            description="需要 Python",
        )

        result = repository.upsert(
            same_job
        )

        session.flush()

        assert result == "unchanged"
        assert saved_job.content_updated_at is None
        assert (
            saved_job.last_detail_checked_at
            >= original_detail_checked_at
        )
        assert (
            saved_job.first_seen_at
            == original_first_seen_at
        )


        # =========================
        # 第三次：UPDATED
        # =========================

        changed_job = build_test_job(
            job_no=job_no,
            description=(
                "需要 Python、PostgreSQL、Airflow"
            ),
        )

        result = repository.upsert(
            changed_job
        )

        session.flush()

        assert result == "updated"

        updated_job = (
            repository.find_by_source_job_id(
                job_no
            )
        )

        assert (
            updated_job.description
            == "需要 Python、PostgreSQL、Airflow"
        )

        assert (
            updated_job.content_hash
            == changed_job["content_hash"]
        )

        assert (
            updated_job.content_updated_at
            is not None
        )

        assert (
            updated_job.first_seen_at
            == original_first_seen_at
        )

        batch_jobs = (
            repository.find_by_source_job_ids(
                [job_no, "missing-job-id"]
            )
        )

        assert [
            job.source_job_id
            for job in batch_jobs
        ] == [job_no]

    finally:

        # 很重要：
        # 測試資料不要真的留在 PostgreSQL
        session.rollback()
        session.close()
