from app.models.job import Job
from app.models.job_application import JobApplication
from app.models.raw_job import RawJob
from app.models.crawler_run import CrawlerRun
from app.models.crawler_failure import CrawlerFailure
from app.models.crawler_keyword import CrawlerKeyword
from app.models.crawler_setting import CrawlerSetting


__all__ = [
    "Job",
    "JobApplication",
    "RawJob",
    "CrawlerRun",
    "CrawlerFailure",
    "CrawlerKeyword",
    "CrawlerSetting",
]
