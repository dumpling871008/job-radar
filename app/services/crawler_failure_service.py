from app.db.database import SessionLocal

from app.repositories.crawler_failure_repository import (
    CrawlerFailureRepository,
)


def save_crawler_failure(
    *,
    run_id,
    stage,
    error_message,
    source_job_id=None,
    attempt_count=1,
    http_status=None,
    error_type=None,
):

    with SessionLocal() as session:

        repository = (
            CrawlerFailureRepository(
                session
            )
        )

        repository.add(
            run_id=run_id,
            source_job_id=source_job_id,
            stage=stage,
            attempt_count=attempt_count,
            http_status=http_status,
            error_type=error_type,
            error_message=error_message,
        )

        session.commit()