from sqlalchemy import func, select

from app.models.crawler_run import CrawlerRun


class CrawlerRunRepository:

    def __init__(self, session):
        self.session = session


    def create(
        self,
        run_id,
        trigger_type="MANUAL",
    ):

        crawler_run = CrawlerRun(
            run_id=run_id,
            trigger_type=trigger_type,
            status="RUNNING",
        )

        self.session.add(
            crawler_run
        )

        return crawler_run


    def get(self, run_id):

        return self.session.get(
            CrawlerRun,
            run_id,
        )


    def count_runs(self):

        statement = select(
            func.count(
                CrawlerRun.run_id
            )
        )

        return self.session.scalar(
            statement
        ) or 0


    def list_runs(
        self,
        *,
        offset=0,
        limit=20,
    ):

        statement = (
            select(CrawlerRun)
            .order_by(
                CrawlerRun.started_at.desc()
            )
            .offset(offset)
            .limit(limit)
        )

        return self.session.scalars(
            statement
        ).all()
