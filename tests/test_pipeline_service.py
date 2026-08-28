from app.services import pipeline_service
import main as main_module


class FakeReservation:

    def __init__(self):
        self.released = False


    def release(self):
        self.released = True


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
        lambda run_id: (
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
        "start_crawler_run",
        lambda **kwargs: None,
    )

    def failed_crawl(run_id):
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
        "start_crawler_run",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        pipeline_service,
        "crawl_jobs",
        lambda run_id: (_ for _ in ()).throw(
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
