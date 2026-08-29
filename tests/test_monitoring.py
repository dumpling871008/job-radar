from datetime import datetime, timezone
from types import SimpleNamespace

from bs4 import BeautifulSoup

from app.api import web
from tests.test_dashboard import get_dashboard


def build_run(
    status,
    *,
    finished=True,
    error_message=None,
    config_snapshot=None,
):
    return SimpleNamespace(
        run_id=f"run-{status.lower()}",
        trigger_type="MANUAL",
        status=status,
        started_at=datetime(
            2026,
            8,
            28,
            1,
            tzinfo=timezone.utc,
        ),
        finished_at=(
            datetime(
                2026,
                8,
                28,
                1,
                5,
                tzinfo=timezone.utc,
            )
            if finished
            else None
        ),
        search_count=40,
        selected_count=20,
        detail_success_count=18,
        detail_failed_count=2,
        raw_inserted_count=18,
        new_count=5,
        updated_count=3,
        unchanged_count=10,
        error_message=error_message,
        config_snapshot=config_snapshot,
    )


def patch_runs(
    monkeypatch,
    runs,
    *,
    total=None,
):
    captured = {}

    monkeypatch.setattr(
        web.CrawlerRunRepository,
        "count_runs",
        lambda repository: (
            len(runs)
            if total is None
            else total
        ),
    )

    def list_runs(
        repository,
        *,
        offset,
        limit,
    ):
        captured.update(
            offset=offset,
            limit=limit,
        )
        return runs

    monkeypatch.setattr(
        web.CrawlerRunRepository,
        "list_runs",
        list_runs,
    )

    return captured


def patch_failures(
    monkeypatch,
    failures,
    *,
    total=None,
):
    captured = {}

    monkeypatch.setattr(
        web.CrawlerFailureRepository,
        "count_failures",
        lambda repository: (
            len(failures)
            if total is None
            else total
        ),
    )

    def list_failures(
        repository,
        *,
        offset,
        limit,
    ):
        captured.update(
            offset=offset,
            limit=limit,
        )
        return failures

    monkeypatch.setattr(
        web.CrawlerFailureRepository,
        "list_failures",
        list_failures,
    )

    return captured


def test_runs_empty_returns_200(
    monkeypatch,
):
    patch_runs(
        monkeypatch,
        [],
    )

    status, html = get_dashboard(
        "/runs"
    )
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    assert status == 200
    assert "目前沒有 crawler run。" in html
    assert (
        soup.select_one(
            ".main-nav-link.active"
        ).get_text(strip=True)
        == "Crawler Runs"
    )


def test_runs_render_statuses(
    monkeypatch,
):
    runs = [
        build_run(
            "SUCCESS",
            config_snapshot={
                "keywords": [
                    {
                        "keyword": "Python 工程師",
                        "target_count": 30,
                    }
                ],
                "max_detail_fetches": 80,
                "max_search_pages_per_keyword": 8,
                "detail_refresh_hours": 48,
                "request_interval_seconds": 2.0,
            },
        ),
        build_run(
            "FAILED",
            error_message="Detail API failed",
        ),
        build_run("PARTIAL_SUCCESS"),
        build_run(
            "RUNNING",
            finished=False,
        ),
    ]
    patch_runs(
        monkeypatch,
        runs,
    )

    status, html = get_dashboard(
        "/runs"
    )

    assert status == 200
    assert "status-badge--success" in html
    assert "status-badge--failed" in html
    assert "status-badge--partial-success" in html
    assert "status-badge--running" in html
    assert "執行中" in html
    assert "Detail API failed" in html
    assert "查看執行設定" in html
    assert "Python 工程師" in html


def test_failures_empty_returns_200(
    monkeypatch,
):
    patch_failures(
        monkeypatch,
        [],
    )

    status, html = get_dashboard(
        "/failures"
    )
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    assert status == 200
    assert "目前沒有 crawler failure。" in html
    assert (
        soup.select_one(
            ".main-nav-link.active"
        ).get_text(strip=True)
        == "Failures"
    )


def test_failure_renders_details(
    monkeypatch,
):
    failure = SimpleNamespace(
        created_at=datetime(
            2026,
            8,
            28,
            2,
            tzinfo=timezone.utc,
        ),
        run_id="run-failure-test",
        source_job_id="job-104-test",
        stage="DETAIL",
        attempt_count=3,
        http_status=500,
        error_type="RuntimeError",
        error_message="Detail API HTTP 500",
    )
    patch_failures(
        monkeypatch,
        [failure],
    )

    status, html = get_dashboard(
        "/failures"
    )

    assert status == 200
    assert "run-failure-test" in html
    assert "job-104-test" in html
    assert "DETAIL" in html
    assert "Detail API HTTP 500" in html


def test_page_two_is_handled(
    monkeypatch,
):
    runs_capture = patch_runs(
        monkeypatch,
        [],
        total=25,
    )
    failures_capture = patch_failures(
        monkeypatch,
        [],
        total=21,
    )

    runs_status, runs_html = (
        get_dashboard(
            "/runs?page=2"
        )
    )
    failures_status, failures_html = (
        get_dashboard(
            "/failures?page=2"
        )
    )

    assert runs_status == 200
    assert failures_status == 200
    assert runs_capture == {
        "offset": 20,
        "limit": 20,
    }
    assert failures_capture == {
        "offset": 20,
        "limit": 20,
    }
    assert "第 2 / 2 頁" in runs_html
    assert "第 2 / 2 頁" in failures_html
