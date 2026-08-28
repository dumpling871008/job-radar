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