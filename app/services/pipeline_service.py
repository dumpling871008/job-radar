from uuid import uuid4
from copy import deepcopy

from app.services.crawler_lock_service import (
    acquire_crawler_lock,
)
from app.services.crawler_run_service import (
    finish_crawler_run,
    start_crawler_run,
)
from app.services.crawler_service import (
    crawl_jobs,
)
from app.services.job_service import save_jobs
from app.services.raw_job_service import (
    save_raw_jobs,
)
from app.db.database import SessionLocal
from app.services.crawler_settings_service import (
    CrawlerSettingsService,
)


PIPELINE_TRIGGER_TYPES = {
    "MANUAL",
    "DASHBOARD",
    "SCHEDULED",
}


def reserve_pipeline():
    """Reserve the PostgreSQL lock before queuing work."""
    return acquire_crawler_lock()


def load_runtime_config():
    with SessionLocal() as session:
        runtime_config = (
            CrawlerSettingsService(
                session
            ).get_runtime_config()
        )
        # 正常情況是純讀取；若 singleton 遺失而建立 default，
        # 在此安全持久化，避免每次 run 重複初始化。
        session.commit()
        return runtime_config


def run_pipeline(
    trigger_type="MANUAL",
    reservation=None,
):
    normalized_trigger = (
        trigger_type.strip().upper()
    )

    if (
        normalized_trigger
        not in PIPELINE_TRIGGER_TYPES
    ):
        if reservation is not None:
            reservation.release()

        raise ValueError(
            "不支援的 crawler trigger_type："
            f"{trigger_type}"
        )

    lock_reservation = (
        reservation
        or acquire_crawler_lock()
    )

    if lock_reservation is None:
        return {
            "started": False,
            "reason": "already_running",
        }

    run_id = uuid4().hex
    crawler_stats = {}
    raw_stats = {}
    db_stats = {}
    run_record_started = False

    try:
        # 每次 run 只讀取一次；後續皆使用此 immutable snapshot。
        runtime_config = deepcopy(
            load_runtime_config()
        )
        start_crawler_run(
            run_id=run_id,
            trigger_type=(
                normalized_trigger
            ),
            config_snapshot=(
                deepcopy(runtime_config)
            ),
        )
        run_record_started = True

        jobs, raw_jobs, crawler_stats = (
            crawl_jobs(
                run_id=run_id,
                runtime_config=(
                    runtime_config
                ),
            )
        )

        print("=" * 50)
        print("開始寫入 Raw Layer...")

        raw_stats = save_raw_jobs(
            raw_jobs,
            crawler_run_id=run_id,
        )

        print("=" * 50)
        print("開始寫入 Clean Layer...")

        db_stats = save_jobs(jobs)

        if (
            crawler_stats.get(
                "failed_count",
                0,
            )
            > 0
        ):
            final_status = (
                "PARTIAL_SUCCESS"
            )
        else:
            final_status = "SUCCESS"

        finish_crawler_run(
            run_id=run_id,
            status=final_status,
            crawler_stats=crawler_stats,
            raw_stats=raw_stats,
            db_stats=db_stats,
        )

        return {
            "started": True,
            "run_id": run_id,
            "status": final_status,
            "crawler_stats": crawler_stats,
            "raw_stats": raw_stats,
            "db_stats": db_stats,
        }

    except Exception as error:
        audit_error = None

        if run_record_started:
            try:
                finish_crawler_run(
                    run_id=run_id,
                    status="FAILED",
                    crawler_stats=(
                        crawler_stats
                    ),
                    raw_stats=raw_stats,
                    db_stats=db_stats,
                    error_message=str(error),
                )
            except Exception as finish_error:
                audit_error = str(
                    finish_error
                )
                print(
                    "Crawler run FAILED 狀態"
                    "寫入失敗："
                    f"{finish_error}"
                )

        print("=" * 50)
        print("Crawler 執行失敗")
        print(f"Run ID：{run_id}")
        print(f"錯誤：{error}")

        return {
            "started": True,
            "run_id": run_id,
            "status": "FAILED",
            "error_message": str(error),
            "audit_error": audit_error,
            "crawler_stats": crawler_stats,
            "raw_stats": raw_stats,
            "db_stats": db_stats,
        }

    finally:
        lock_reservation.release()
