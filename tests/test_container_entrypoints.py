import pytest

import main as crawler_entrypoint
from app.api import server
from tests.test_dashboard import request_app


def test_health_returns_ok():
    status, body, _ = request_app(
        "/health"
    )

    assert status == 200
    assert body == '{"status":"ok"}'


def test_web_entrypoint_uses_port_environment(
    monkeypatch,
):
    calls = []
    monkeypatch.setenv("PORT", "9090")
    monkeypatch.setattr(
        server.uvicorn,
        "run",
        lambda *args, **kwargs: calls.append(
            (args, kwargs)
        ),
    )

    server.main()

    assert calls == [
        (
            ("app.api.web:app",),
            {
                "host": "0.0.0.0",
                "port": 9090,
            },
        )
    ]


@pytest.mark.parametrize(
    "result, expected_exit_code",
    [
        (
            {
                "started": True,
                "run_id": "success-run",
                "status": "SUCCESS",
            },
            0,
        ),
        (
            {
                "started": True,
                "run_id": "partial-run",
                "status": "PARTIAL_SUCCESS",
            },
            0,
        ),
        (
            {
                "started": True,
                "run_id": "failed-run",
                "status": "FAILED",
                "error_message": "failure",
            },
            1,
        ),
    ],
)
def test_crawler_entrypoint_uses_shared_pipeline_and_exit_semantics(
    monkeypatch,
    result,
    expected_exit_code,
):
    calls = []

    def fake_run_pipeline(trigger_type):
        calls.append(trigger_type)
        return result

    monkeypatch.setattr(
        crawler_entrypoint,
        "run_pipeline",
        fake_run_pipeline,
    )

    assert (
        crawler_entrypoint.main()
        == expected_exit_code
    )
    assert calls == ["MANUAL"]
