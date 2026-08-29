from app.services import pipeline_service
import main as main_module


class FakeReservation:

    def __init__(self):
        self.released = False


    def release(self):
        self.released = True


def runtime_config(max_details=100):
    return {
        "keywords": [
            {
                "keyword": "Python 工程師",
                "target_count": 30,
            }
        ],
        "max_detail_fetches": max_details,
        "max_search_pages_per_keyword": 8,
        "detail_refresh_hours": 48,
        "request_interval_seconds": 2.0,
    }


def test_run_pipeline_with_lock_runs_pipeline(
    monkeypatch,
):
    reservation = FakeReservation()
    calls = []

    monkeypatch.setattr(
        pipeline_service,
        "acquire_crawler_lock",
        lambda: reservation,
    )
    config = runtime_config()
    monkeypatch.setattr(
        pipeline_service,
        "load_runtime_config",
        lambda: config,
    )
    monkeypatch.setattr(
        pipeline_service,
        "start_crawler_run",
        lambda **kwargs: calls.append(
            ("start", kwargs)
        ),
    )
    monkeypatch.setattr(
        pipeline_service,
        "crawl_jobs",
        lambda run_id, runtime_config: (
            ["clean-job"],
            ["raw-job"],
            {
                "search_count": 1,
                "selected_count": 1,
                "success_count": 1,
                "failed_count": 0,
            },
        ),
    )
    monkeypatch.setattr(
        pipeline_service,
        "save_raw_jobs",
        lambda raw_jobs, crawler_run_id: {
            "inserted_count": 1
        },
    )
    monkeypatch.setattr(
        pipeline_service,
        "save_jobs",
        lambda jobs: {
            "new_count": 1,
            "updated_count": 0,
            "unchanged_count": 0,
        },
    )
    monkeypatch.setattr(
        pipeline_service,
        "finish_crawler_run",
        lambda **kwargs: calls.append(
            ("finish", kwargs)
        ),
    )

    result = pipeline_service.run_pipeline(
        trigger_type="MANUAL"
    )

    assert result["started"] is True
    assert result["status"] == "SUCCESS"
    assert calls[0][0] == "start"
    assert calls[0][1][
        "config_snapshot"
    ] == config
    assert calls[-1][1]["status"] == (
        "SUCCESS"
    )
    assert reservation.released is True


def test_run_pipeline_returns_already_running(
    monkeypatch,
):
    monkeypatch.setattr(
        pipeline_service,
        "acquire_crawler_lock",
        lambda: None,
    )

    def unexpected_crawl(run_id):
        raise AssertionError(
            "crawler 不應被啟動"
        )

    monkeypatch.setattr(
        pipeline_service,
        "crawl_jobs",
        unexpected_crawl,
    )

    result = pipeline_service.run_pipeline()

    assert result == {
        "started": False,
        "reason": "already_running",
    }


def test_pipeline_exception_marks_run_failed(
    monkeypatch,
):
    reservation = FakeReservation()
    finishes = []

    monkeypatch.setattr(
        pipeline_service,
        "acquire_crawler_lock",
        lambda: reservation,
    )
    monkeypatch.setattr(
        pipeline_service,
        "load_runtime_config",
        lambda: runtime_config(),
    )
    monkeypatch.setattr(
        pipeline_service,
        "start_crawler_run",
        lambda **kwargs: None,
    )

    def failed_crawl(
        run_id,
        runtime_config,
    ):
        raise RuntimeError(
            "mock crawler failure"
        )

    monkeypatch.setattr(
        pipeline_service,
        "crawl_jobs",
        failed_crawl,
    )
    monkeypatch.setattr(
        pipeline_service,
        "finish_crawler_run",
        lambda **kwargs: finishes.append(
            kwargs
        ),
    )

    result = pipeline_service.run_pipeline()

    assert result["status"] == "FAILED"
    assert result["error_message"] == (
        "mock crawler failure"
    )
    assert finishes == [
        {
            "run_id": result["run_id"],
            "status": "FAILED",
            "crawler_stats": {},
            "raw_stats": {},
            "db_stats": {},
            "error_message": (
                "mock crawler failure"
            ),
        }
    ]


def test_pipeline_exception_releases_lock(
    monkeypatch,
):
    reservation = FakeReservation()

    monkeypatch.setattr(
        pipeline_service,
        "acquire_crawler_lock",
        lambda: reservation,
    )
    monkeypatch.setattr(
        pipeline_service,
        "load_runtime_config",
        lambda: runtime_config(),
    )
    monkeypatch.setattr(
        pipeline_service,
        "start_crawler_run",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        pipeline_service,
        "crawl_jobs",
        lambda run_id, runtime_config: (_ for _ in ()).throw(
            RuntimeError("failure")
        ),
    )
    monkeypatch.setattr(
        pipeline_service,
        "finish_crawler_run",
        lambda **kwargs: None,
    )

    pipeline_service.run_pipeline()

    assert reservation.released is True


def test_cli_uses_shared_run_pipeline(
    monkeypatch,
):
    calls = []

    monkeypatch.setattr(
        main_module,
        "run_pipeline",
        lambda trigger_type: (
            calls.append(trigger_type)
            or {
                "started": False,
                "reason": "already_running",
            }
        ),
    )

    main_module.main()

    assert calls == ["MANUAL"]


def test_pipeline_loads_runtime_config_once_per_run(
    monkeypatch,
):
    reservation = FakeReservation()
    configs = [runtime_config(80)]
    load_calls = []
    crawl_configs = []
    start_snapshots = []

    monkeypatch.setattr(
        pipeline_service,
        "acquire_crawler_lock",
        lambda: reservation,
    )

    def load_config():
        load_calls.append(True)
        return configs[0]

    def crawl(run_id, runtime_config):
        crawl_configs.append(runtime_config)
        # 模擬 run 中途 DB 設定已改變；本次 snapshot 不應改變。
        configs[0] = runtime_config.copy()
        configs[0]["max_detail_fetches"] = 200
        return [], [], {
            "failed_count": 0,
        }

    monkeypatch.setattr(
        pipeline_service,
        "load_runtime_config",
        load_config,
    )
    monkeypatch.setattr(
        pipeline_service,
        "start_crawler_run",
        lambda **kwargs: start_snapshots.append(
            kwargs["config_snapshot"]
        ),
    )
    monkeypatch.setattr(
        pipeline_service,
        "crawl_jobs",
        crawl,
    )
    monkeypatch.setattr(
        pipeline_service,
        "save_raw_jobs",
        lambda *args, **kwargs: {},
    )
    monkeypatch.setattr(
        pipeline_service,
        "save_jobs",
        lambda jobs: {},
    )
    monkeypatch.setattr(
        pipeline_service,
        "finish_crawler_run",
        lambda **kwargs: None,
    )

    first = pipeline_service.run_pipeline()

    assert first["status"] == "SUCCESS"
    assert len(load_calls) == 1
    assert crawl_configs[0][
        "max_detail_fetches"
    ] == 80
    assert start_snapshots[0][
        "max_detail_fetches"
    ] == 80


def test_next_run_uses_new_runtime_config(
    monkeypatch,
):
    configs = iter(
        [runtime_config(80), runtime_config(120)]
    )
    used_limits = []

    monkeypatch.setattr(
        pipeline_service,
        "acquire_crawler_lock",
        lambda: FakeReservation(),
    )
    monkeypatch.setattr(
        pipeline_service,
        "load_runtime_config",
        lambda: next(configs),
    )
    monkeypatch.setattr(
        pipeline_service,
        "start_crawler_run",
        lambda **kwargs: None,
    )

    def crawl(run_id, runtime_config):
        used_limits.append(
            runtime_config[
                "max_detail_fetches"
            ]
        )
        return [], [], {"failed_count": 0}

    monkeypatch.setattr(
        pipeline_service,
        "crawl_jobs",
        crawl,
    )
    monkeypatch.setattr(
        pipeline_service,
        "save_raw_jobs",
        lambda *args, **kwargs: {},
    )
    monkeypatch.setattr(
        pipeline_service,
        "save_jobs",
        lambda jobs: {},
    )
    monkeypatch.setattr(
        pipeline_service,
        "finish_crawler_run",
        lambda **kwargs: None,
    )

    pipeline_service.run_pipeline()
    pipeline_service.run_pipeline()

    assert used_limits == [80, 120]
