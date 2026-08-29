from datetime import (
    datetime,
    timezone,
)

from app.db.database import (
    SessionLocal,
)

from app.repositories.crawler_run_repository import (
    CrawlerRunRepository,
)


def start_crawler_run(
    run_id,
    trigger_type="MANUAL",
    config_snapshot=None,
):

    with SessionLocal() as session:

        repository = (
            CrawlerRunRepository(
                session
            )
        )

        repository.create(
            run_id=run_id,
            trigger_type=trigger_type,
            config_snapshot=(
                config_snapshot
            ),
        )

        session.commit()


def finish_crawler_run(
    run_id,
    status,
    crawler_stats=None,
    raw_stats=None,
    db_stats=None,
    error_message=None,
):

    crawler_stats = (
        crawler_stats or {}
    )

    raw_stats = (
        raw_stats or {}
    )

    db_stats = (
        db_stats or {}
    )

    with SessionLocal() as session:

        repository = (
            CrawlerRunRepository(
                session
            )
        )

        crawler_run = (
            repository.get(
                run_id
            )
        )

        if crawler_run is None:

            raise RuntimeError(
                f"找不到 crawler run："
                f"{run_id}"
            )

        crawler_run.status = status

        crawler_run.finished_at = (
            datetime.now(
                timezone.utc
            )
        )

        crawler_run.search_count = (
            crawler_stats.get(
                "search_count",
                0,
            )
        )

        crawler_run.selected_count = (
            crawler_stats.get(
                "selected_count",
                0,
            )
        )

        crawler_run.detail_success_count = (
            crawler_stats.get(
                "success_count",
                0,
            )
        )

        crawler_run.detail_failed_count = (
            crawler_stats.get(
                "failed_count",
                0,
            )
        )

        crawler_run.raw_inserted_count = (
            raw_stats.get(
                "inserted_count",
                0,
            )
        )

        crawler_run.new_count = (
            db_stats.get(
                "new_count",
                0,
            )
        )

        crawler_run.updated_count = (
            db_stats.get(
                "updated_count",
                0,
            )
        )

        crawler_run.unchanged_count = (
            db_stats.get(
                "unchanged_count",
                0,
            )
        )

        crawler_run.error_message = (
            error_message
        )

        session.commit()
