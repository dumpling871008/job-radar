from alembic import context

from app.db.base import Base
from app.db.database import DATABASE_URL, engine
from app.models.crawler_failure import CrawlerFailure
from app.models.crawler_run import CrawlerRun
from app.models.job import Job
from app.models.job_application import JobApplication
from app.models.raw_job import RawJob


target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
