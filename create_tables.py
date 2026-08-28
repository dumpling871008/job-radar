from app.db.base import Base
from app.db.database import engine

from app.models.job import Job
from app.models.raw_job import RawJob
from app.models.crawler_run import CrawlerRun
from app.models.crawler_failure import CrawlerFailure


def create_tables():

    Base.metadata.create_all(
        bind=engine
    )

    print("資料表建立完成！")


if __name__ == "__main__":
    create_tables()