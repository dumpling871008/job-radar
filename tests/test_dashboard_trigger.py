from urllib.parse import parse_qs, urlsplit

from app.api import web
from tests.test_dashboard import (
    get_dashboard,
    request_app,
)


class FakeReservation:

    def __init__(self):
        self.released = False


    def release(self):
        self.released = True


def test_crawler_run_post_redirects_and_runs_background(
    monkeypatch,
):
    reservation = FakeReservation()
    calls = []

    monkeypatch.setattr(
        web,
        "reserve_pipeline",
        lambda: reservation,
    )

    def fake_run_pipeline(
        *,
        trigger_type,
        reservation,
    ):
        calls.append(
            {
                "trigger_type": trigger_type,
                "reservation": reservation,
            }
        )
        reservation.release()

    monkeypatch.setattr(
        web,
        "run_pipeline",
        fake_run_pipeline,
    )

    status, _, headers = request_app(
        "/crawler/run",
        method="POST",
        data={
            "view": "updated",
            "q": "Python",
            "location": "台北市",
            "sort": "first_seen",
            "page": "2",
            "filter_status": "SAVED",
            "category": "AI_DATA",
            "tech": "Python",
            "experience": "THREE_TO_FIVE",
        },
    )
    query = parse_qs(
        urlsplit(
            headers["location"]
        ).query
    )

    assert status == 303
    assert calls == [
        {
            "trigger_type": "DASHBOARD",
            "reservation": reservation,
        }
    ]
    assert reservation.released is True
    assert query == {
        "view": ["updated"],
        "q": ["Python"],
        "location": ["台北市"],
        "sort": ["first_seen"],
        "status": ["SAVED"],
        "category": ["AI_DATA"],
        "tech": ["Python"],
        "experience": ["THREE_TO_FIVE"],
        "page": ["2"],
        "message": ["crawler_started"],
    }


def test_crawler_run_post_does_not_queue_when_locked(
    monkeypatch,
):
    calls = []

    monkeypatch.setattr(
        web,
        "reserve_pipeline",
        lambda: None,
    )
    monkeypatch.setattr(
        web,
        "run_pipeline",
        lambda **kwargs: calls.append(
            kwargs
        ),
    )

    status, _, headers = request_app(
        "/crawler/run",
        method="POST",
        data={},
    )
    query = parse_qs(
        urlsplit(
            headers["location"]
        ).query
    )

    assert status == 303
    assert calls == []
    assert query["message"] == [
        "crawler_already_running"
    ]
    assert query["category"] == [
        "relevant"
    ]


def test_dashboard_renders_trigger_and_feedback(
    monkeypatch,
):
    class EmptyJobResult:

        def all(self):
            return []

    monkeypatch.setattr(
        web,
        "SessionLocal",
        lambda: _FakeDashboardSession(
            EmptyJobResult()
        ),
    )

    status, html = get_dashboard(
        "/?message=crawler_started"
    )

    assert status == 200
    assert "立即更新職缺" in html
    assert "查看執行紀錄" in html
    assert "已開始更新職缺。" in html


class _FakeDashboardSession:

    def __init__(self, result):
        self.result = result
        self.scalar_calls = 0


    def __enter__(self):
        return self


    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        return False


    def scalars(self, statement):
        return self.result


    def scalar(self, statement):
        self.scalar_calls += 1
        return 0
