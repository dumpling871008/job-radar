from app.models.raw_job import RawJob


class RawJobRepository:

    def __init__(self, session):
        self.session = session


    def add_snapshot(
        self,
        *,
        source,
        source_job_id,
        source_url,
        raw_data,
        content_hash,
        crawler_run_id=None,
    ):

        raw_job = RawJob(
            crawler_run_id=crawler_run_id,
            source=source,
            source_job_id=source_job_id,
            source_url=source_url,
            raw_data=raw_data,
            content_hash=content_hash,
        )

        self.session.add(raw_job)

        return raw_job