import pytest

from app.crawler.client import fetch_job_detail


class FakeResponse:
    def __init__(
        self,
        status_code,
        content_type="application/json",
        payload=None,
        retry_after=None,
    ):
        self.status_code = status_code

        self.headers = {
            "Content-Type": content_type
        }

        if retry_after is not None:
            self.headers[
                "Retry-After"
            ] = retry_after

        self._payload = payload or {}

    def json(self):
        return self._payload


def test_detail_api_retry_then_success(
    monkeypatch,
):

    # 記錄 requests.get 被呼叫幾次
    call_count = {
        "count": 0
    }

    def fake_get(
        url,
        headers=None,
        timeout=None,
    ):
        call_count["count"] += 1

        # 第一次故意失敗
        if call_count["count"] == 1:

            return FakeResponse(
                status_code=500
            )

        # 第二次成功
        return FakeResponse(
            status_code=200,
            payload={
                "data": {
                    "jobDetail": {
                        "jobDescription":
                        "這是完整 JD"
                    }
                }
            },
        )

    monkeypatch.setattr(
        "app.crawler.client.requests.get",
        fake_get,
    )

    # 不要真的等 1 秒
    monkeypatch.setattr(
        "app.crawler.client.time.sleep",
        lambda seconds: None,
    )

    detail_data, attempt_count = (
        fetch_job_detail(
            "https://www.104.com.tw/job/abc123",
            max_attempts=3,
        )
    )

    assert attempt_count == 2

    assert call_count["count"] == 2

    assert (
        detail_data[
            "jobDetail"
        ][
            "jobDescription"
        ]
        == "這是完整 JD"
    )

def test_detail_api_all_attempts_failed(
    monkeypatch,
):
    call_count = {
        "count": 0
    }

    def fake_get(
        url,
        headers=None,
        timeout=None,
    ):
        call_count["count"] += 1

        # 每一次都回 500
        return FakeResponse(
            status_code=500
        )

    monkeypatch.setattr(
        "app.crawler.client.requests.get",
        fake_get,
    )

    # 測試時不要真的等待
    monkeypatch.setattr(
        "app.crawler.client.time.sleep",
        lambda seconds: None,
    )

    with pytest.raises(
        RuntimeError
    ):
        fetch_job_detail(
            "https://www.104.com.tw/job/abc123",
            max_attempts=3,
        )

    # 應該真的嘗試 3 次
    assert call_count["count"] == 3

def test_detail_api_403_should_not_retry(
    monkeypatch,
):
    call_count = {
        "count": 0
    }

    def fake_get(
        url,
        headers=None,
        timeout=None,
    ):
        call_count["count"] += 1

        return FakeResponse(
            status_code=403
        )

    monkeypatch.setattr(
        "app.crawler.client.requests.get",
        fake_get,
    )

    monkeypatch.setattr(
        "app.crawler.client.time.sleep",
        lambda seconds: None,
    )

    with pytest.raises(
        RuntimeError
    ):
        fetch_job_detail(
            "https://www.104.com.tw/job/abc123",
            max_attempts=3,
        )

    # 403 應該第一次就停止
    assert call_count["count"] == 1


def test_detail_api_429_respects_retry_after(
    monkeypatch,
):
    responses = [
        FakeResponse(
            status_code=429,
            retry_after="7",
        ),
        FakeResponse(
            status_code=200,
            payload={"data": {}},
        ),
    ]
    waits = []

    monkeypatch.setattr(
        "app.crawler.client.requests.get",
        lambda *args, **kwargs: (
            responses.pop(0)
        ),
    )
    monkeypatch.setattr(
        "app.crawler.client.time.sleep",
        waits.append,
    )

    _, attempt_count = fetch_job_detail(
        "https://www.104.com.tw/job/abc123",
        max_attempts=2,
    )

    assert attempt_count == 2
    assert waits == [7.0]
