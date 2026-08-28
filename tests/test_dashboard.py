import asyncio
from datetime import datetime, time, timedelta
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
from bs4 import BeautifulSoup
from sqlalchemy import delete

from app.api.web import (
    TAIPEI_TIMEZONE,
    app,
)
from app.db.database import SessionLocal
from app.models.job import Job


@pytest.fixture(scope="module")
def dashboard_jobs():
    marker = uuid4().hex
    location = "測試市測試區"
    today = datetime.now(
        TAIPEI_TIMEZONE
    ).date()
    today_start = datetime.combine(
        today,
        time.min,
        tzinfo=TAIPEI_TIMEZONE,
    )

    jobs = []

    for index in range(21):
        jobs.append(
            Job(
                source="104",
                source_job_id=(
                    f"dashboard-{marker}-{index}"
                ),
                title=f"{marker} 測試職缺 {index}",
                company_name="Dashboard 測試公司",
                location=location,
                description="Dashboard route test",
                url=(
                    "https://www.104.com.tw/job/"
                    f"dashboard-{index}"
                ),
                first_seen_at=(
                    today_start
                    + timedelta(hours=1)
                ),
            )
        )

    jobs.append(
        Job(
            source="104",
            source_job_id=(
                f"dashboard-{marker}-old"
            ),
            title=f"{marker} 昨日測試職缺",
            company_name="Dashboard 測試公司",
            location=location,
            description="Dashboard route test",
            url=(
                "https://www.104.com.tw/job/"
                "dashboard-old"
            ),
            first_seen_at=(
                today_start
                - timedelta(seconds=1)
            ),
        )
    )

    with SessionLocal() as session:
        session.add_all(jobs)
        session.commit()

    yield {
        "marker": marker,
        "city": "測試市",
    }

    with SessionLocal() as session:
        session.execute(
            delete(Job).where(
                Job.source_job_id.startswith(
                    f"dashboard-{marker}-"
                )
            )
        )
        session.commit()


def get_dashboard(path):
    parsed_url = urlsplit(path)
    messages = []
    request_sent = False

    scope = {
        "type": "http",
        "asgi": {
            "version": "3.0",
            "spec_version": "2.3",
        },
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": parsed_url.path,
        "raw_path": parsed_url.path.encode(),
        "query_string": parsed_url.query.encode(),
        "root_path": "",
        "headers": [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    async def receive():
        nonlocal request_sent

        if not request_sent:
            request_sent = True
            return {
                "type": "http.request",
                "body": b"",
                "more_body": False,
            }

        return {
            "type": "http.disconnect",
        }

    async def send(message):
        messages.append(message)

    asyncio.run(
        app(scope, receive, send)
    )

    start = next(
        message
        for message in messages
        if message["type"]
        == "http.response.start"
    )

    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"]
        == "http.response.body"
    )

    return start["status"], body.decode()


def test_all_view_returns_successfully(
    dashboard_jobs,
):
    status, html = get_dashboard(
        "/?view=all&q="
        f"{dashboard_jobs['marker']}"
        "&location=%E6%B8%AC%E8%A9%A6%E5%B8%82"
    )
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    assert status == 200
    assert "共 22 筆職缺" in (
        soup.select_one(
            ".subtitle"
        ).get_text(" ", strip=True)
    )
    assert (
        soup.select_one(
            '.view-tab.active[data-view="all"]'
        )
        is not None
    )


def test_today_view_returns_successfully(
    dashboard_jobs,
):
    status, html = get_dashboard(
        "/?view=today&q="
        f"{dashboard_jobs['marker']}"
        "&location=%E6%B8%AC%E8%A9%A6%E5%B8%82"
    )
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    assert status == 200
    assert "共 21 筆職缺" in (
        soup.select_one(
            ".subtitle"
        ).get_text(" ", strip=True)
    )
    assert (
        soup.select_one(
            '.view-tab.active[data-view="today"]'
        )
        is not None
    )


def test_q_location_and_view_can_coexist(
    dashboard_jobs,
):
    marker = dashboard_jobs["marker"]

    status, html = get_dashboard(
        f"/?view=today&q={marker}&location="
        "%E6%B8%AC%E8%A9%A6%E5%B8%82&page=1"
    )
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    assert status == 200
    assert soup.select_one(
        'input[name="view"]'
    )["value"] == "today"
    assert soup.select_one(
        'input[name="q"]'
    )["value"] == marker
    assert soup.select_one(
        'select[name="location"] option[selected]'
    )["value"] == "測試市"

    all_tab_query = parse_qs(
        urlsplit(
            soup.select_one(
                '.view-tab[data-view="all"]'
            )["href"]
        ).query,
        keep_blank_values=True,
    )

    assert all_tab_query == {
        "view": ["all"],
        "q": [marker],
        "location": ["測試市"],
        "page": ["1"],
    }


def test_pagination_keeps_dashboard_filters(
    dashboard_jobs,
):
    marker = dashboard_jobs["marker"]

    status, html = get_dashboard(
        f"/?view=all&q={marker}&location="
        "%E6%B8%AC%E8%A9%A6%E5%B8%82&page=1"
    )
    soup = BeautifulSoup(
        html,
        "html.parser",
    )
    next_link = soup.select_one(
        ".pagination a"
    )

    assert status == 200
    assert next_link is not None

    next_query = parse_qs(
        urlsplit(
            next_link["href"]
        ).query,
        keep_blank_values=True,
    )

    assert next_query == {
        "view": ["all"],
        "q": [marker],
        "location": ["測試市"],
        "page": ["2"],
    }
