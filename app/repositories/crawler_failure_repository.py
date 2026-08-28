from sqlalchemy import func, select

from app.models.crawler_failure import (
    CrawlerFailure,
)


class CrawlerFailureRepository:

    def __init__(self, session):
        self.session = session


    def add(
        self,
        *,
        run_id,
        stage,
        error_message,
        source_job_id=None,
        attempt_count=1,
        http_status=None,
        error_type=None,
    ):

        failure = CrawlerFailure(
            run_id=run_id,
            source_job_id=source_job_id,
            stage=stage,
            attempt_count=attempt_count,
            http_status=http_status,
            error_type=error_type,
            error_message=error_message,
        )

        self.session.add(failure)

        return failure


    def count_failures(self):

        statement = select(
            func.count(
                CrawlerFailure.id
            )
        )

        return self.session.scalar(
            statement
        ) or 0


    def list_failures(
        self,
        *,
        offset=0,
        limit=20,
    ):

        statement = (
            select(CrawlerFailure)
            .order_by(
                CrawlerFailure.created_at.desc()
            )
            .offset(offset)
            .limit(limit)
        )

        return self.session.scalars(
            statement
        ).all()
