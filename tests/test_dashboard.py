import asyncio
from datetime import datetime, time, timedelta
from urllib.parse import (
    parse_qs,
    urlencode,
    urlsplit,
)
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
                job_category="SOFTWARE",
                tech_stack=["Python"],
                salary_text=(
                    "月薪45,000~60,000元"
                    if index == 0
                    else None
                ),
                experience="1年以上",
                url=(
                    "https://www.104.com.tw/job/"
                    f"dashboard-{index}"
                ),
                first_seen_at=(
                    today_start
                    + timedelta(hours=1)
                ),
                content_updated_at=(
                    today_start
                    + timedelta(hours=2)
                    if index < 3
                    else None
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
            job_category="SOFTWARE",
            tech_stack=["Python"],
            experience="1年以上",
            url=(
                "https://www.104.com.tw/job/"
                "dashboard-old"
            ),
            first_seen_at=(
                today_start
                - timedelta(seconds=1)
            ),
            content_updated_at=(
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


def request_app(
    path,
    *,
    method="GET",
    data=None,
):
    parsed_url = urlsplit(path)
    messages = []
    request_sent = False
    body = urlencode(
        data or {}
    ).encode()
    headers = []

    if data is not None:
        headers.append(
            (
                b"content-type",
                b"application/x-www-form-urlencoded",
            )
        )

    scope = {
        "type": "http",
        "asgi": {
            "version": "3.0",
            "spec_version": "2.3",
        },
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": parsed_url.path,
        "raw_path": parsed_url.path.encode(),
        "query_string": parsed_url.query.encode(),
        "root_path": "",
        "headers": headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    async def receive():
        nonlocal request_sent

        if not request_sent:
            request_sent = True
            return {
                "type": "http.request",
                "body": body,
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

    response_headers = {
        key.decode().lower(): value.decode()
        for key, value in start["headers"]
    }

    return (
        start["status"],
        body.decode(),
        response_headers,
    )


def get_dashboard(path):
    status, body, _ = request_app(path)
    return status, body


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
    navigation = [
        link.get_text(strip=True)
        for link in soup.select(
            ".main-nav-link"
        )
    ]
    assert navigation == [
        "Jobs",
        "Crawler Runs",
        "Failures",
        "Crawler Settings",
    ]
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


def test_updated_view_returns_successfully(
    dashboard_jobs,
):
    status, html = get_dashboard(
        "/?view=updated&q="
        f"{dashboard_jobs['marker']}"
        "&location=%E6%B8%AC%E8%A9%A6%E5%B8%82"
    )
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    assert status == 200
    assert "共 3 筆職缺" in (
        soup.select_one(
            ".subtitle"
        ).get_text(" ", strip=True)
    )
    assert (
        soup.select_one(
            '.view-tab.active[data-view="updated"]'
        )
        is not None
    )


def test_updated_view_excludes_null_content_updated_at(
    dashboard_jobs,
):
    marker = dashboard_jobs["marker"]
    status, html = get_dashboard(
        f"/?view=updated&q={marker}&location="
        "%E6%B8%AC%E8%A9%A6%E5%B8%82"
    )

    assert status == 200
    assert f"{marker} 測試職缺 0" in html
    assert f"{marker} 測試職缺 3" not in html
    assert f"{marker} 昨日測試職缺" not in html


def test_q_location_and_view_can_coexist(
    dashboard_jobs,
):
    marker = dashboard_jobs["marker"]

    status, html = get_dashboard(
        f"/?view=updated&q={marker}&location="
        "%E6%B8%AC%E8%A9%A6%E5%B8%82&page=1"
    )
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    assert status == 200
    assert soup.select_one(
        'input[name="view"]'
    )["value"] == "updated"
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
        "category": ["relevant"],
        "page": ["1"],
    }


def test_pagination_keeps_dashboard_filters(
    dashboard_jobs,
):
    marker = dashboard_jobs["marker"]

    status, html = get_dashboard(
        f"/?view=all&q={marker}&location="
        "%E6%B8%AC%E8%A9%A6%E5%B8%82"
        "&status=UNREAD&sort=first_seen"
        "&category=relevant&tech=Python"
        "&experience=ONE_TO_THREE&page=1"
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
        "sort": ["first_seen"],
        "tech": ["Python"],
        "experience": ["ONE_TO_THREE"],
        "status": ["UNREAD"],
        "category": ["relevant"],
        "page": ["2"],
    }


@pytest.fixture
def categorized_dashboard_jobs():
    marker = uuid4().hex
    source_marker = marker[:12]
    now = datetime.now(
        TAIPEI_TIMEZONE
    )
    category_labels = (
        ("SOFTWARE", "軟體職缺"),
        ("AI_DATA", "資料職缺"),
        ("DEVOPS_CLOUD", "雲端職缺"),
        (
            "OTHER_ENGINEERING",
            "傳統工程職缺",
        ),
        ("NON_TECH", "非技術職缺"),
        ("UNKNOWN", "未分類職缺"),
    )
    titles = {
        category: f"{marker} {label}"
        for category, label in category_labels
    }
    tech_stacks = {
        "SOFTWARE": [
            "Python",
            "FastAPI",
            "PostgreSQL",
        ],
        "AI_DATA": [
            "Python",
            "GCP",
            "Docker",
            "Kubernetes",
            "LLM",
            "RAG",
        ],
        "DEVOPS_CLOUD": [
            "GCP",
            "Docker",
        ],
        "OTHER_ENGINEERING": ["Java"],
        "NON_TECH": [],
        "UNKNOWN": [],
    }
    experience_values = {
        "SOFTWARE": "1年以上",
        "AI_DATA": "3年以上",
        "DEVOPS_CLOUD": "5年以上",
        "OTHER_ENGINEERING": "不拘",
        "NON_TECH": None,
        "UNKNOWN": None,
    }
    jobs = [
        Job(
            source="104",
            source_job_id=(
                f"cat-{source_marker}-{category}"
            ),
            title=f"{marker} {label}",
            company_name="分類測試公司",
            location="分類市測試區",
            description="category route test",
            job_category=category,
            tech_stack=tech_stacks[
                category
            ],
            salary_text=(
                "待遇面議"
                if category == "AI_DATA"
                else None
            ),
            experience=experience_values[
                category
            ],
            url=(
                "https://www.104.com.tw/job/"
                f"category-{category}"
            ),
            first_seen_at=now,
            content_updated_at=now,
        )
        for category, label in category_labels
    ]

    with SessionLocal() as session:
        session.add_all(jobs)
        session.commit()

    yield {
        "marker": marker,
        "source_marker": source_marker,
        "titles": titles,
    }

    with SessionLocal() as session:
        session.execute(
            delete(Job).where(
                Job.source_job_id.startswith(
                    f"cat-{source_marker}-"
                )
            )
        )
        session.commit()


def test_relevant_category_excludes_unrelated_jobs(
    categorized_dashboard_jobs,
):
    marker = categorized_dashboard_jobs[
        "marker"
    ]
    titles = categorized_dashboard_jobs[
        "titles"
    ]

    status, html = get_dashboard(
        f"/?category=relevant&q={marker}"
    )

    assert status == 200
    assert titles["SOFTWARE"] in html
    assert titles["AI_DATA"] in html
    assert titles["DEVOPS_CLOUD"] in html
    assert titles["OTHER_ENGINEERING"] not in html
    assert titles["NON_TECH"] not in html
    assert titles["UNKNOWN"] not in html


def test_other_engineering_category_is_available(
    categorized_dashboard_jobs,
):
    marker = categorized_dashboard_jobs[
        "marker"
    ]
    titles = categorized_dashboard_jobs[
        "titles"
    ]

    status, html = get_dashboard(
        "/?category=OTHER_ENGINEERING"
        f"&q={marker}"
    )

    assert status == 200
    assert titles["OTHER_ENGINEERING"] in html
    assert titles["SOFTWARE"] not in html


def test_all_category_includes_every_category(
    categorized_dashboard_jobs,
):
    marker = categorized_dashboard_jobs[
        "marker"
    ]
    titles = categorized_dashboard_jobs[
        "titles"
    ]

    status, html = get_dashboard(
        f"/?category=all&q={marker}"
    )

    assert status == 200
    assert all(
        title in html
        for title in titles.values()
    )


def test_category_coexists_with_dashboard_filters(
    categorized_dashboard_jobs,
):
    marker = categorized_dashboard_jobs[
        "marker"
    ]

    status, html = get_dashboard(
        "/?category=AI_DATA&view=today"
        "&status=UNREAD&location="
        "%E5%88%86%E9%A1%9E%E5%B8%82"
        f"&q={marker}&sort=first_seen&page=1"
    )
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    assert status == 200
    assert (
        categorized_dashboard_jobs[
            "titles"
        ]["AI_DATA"]
        in html
    )
    assert soup.select_one(
        'input[name="category"]'
    )["value"] == "AI_DATA"
    assert soup.select_one(
        '.category-filter__link.active'
    )["data-category"] == "AI_DATA"

    software_query = parse_qs(
        urlsplit(
            soup.select_one(
                '[data-category="SOFTWARE"]'
            )["href"]
        ).query,
        keep_blank_values=True,
    )
    assert software_query == {
        "view": ["today"],
        "q": [marker],
        "location": ["分類市"],
        "sort": ["first_seen"],
        "status": ["UNREAD"],
        "category": ["SOFTWARE"],
        "page": ["1"],
    }


def test_tech_filter_only_shows_matching_jobs(
    categorized_dashboard_jobs,
):
    marker = categorized_dashboard_jobs[
        "marker"
    ]
    titles = categorized_dashboard_jobs[
        "titles"
    ]

    status, html = get_dashboard(
        f"/?category=all&tech=Python&q={marker}"
    )

    assert status == 200
    assert titles["SOFTWARE"] in html
    assert titles["AI_DATA"] in html
    assert titles["DEVOPS_CLOUD"] not in html
    assert titles["OTHER_ENGINEERING"] not in html


def test_tech_and_category_filters_coexist(
    categorized_dashboard_jobs,
):
    marker = categorized_dashboard_jobs[
        "marker"
    ]
    titles = categorized_dashboard_jobs[
        "titles"
    ]

    status, html = get_dashboard(
        "/?category=AI_DATA&tech=Python"
        f"&q={marker}"
    )

    assert status == 200
    assert titles["AI_DATA"] in html
    assert titles["SOFTWARE"] not in html


def test_tech_location_and_q_filters_coexist(
    categorized_dashboard_jobs,
):
    marker = categorized_dashboard_jobs[
        "marker"
    ]

    status, html = get_dashboard(
        "/?category=all&tech=GCP&location="
        "%E5%88%86%E9%A1%9E%E5%B8%82"
        f"&q={marker}"
    )

    assert status == 200
    assert (
        categorized_dashboard_jobs[
            "titles"
        ]["AI_DATA"]
        in html
    )


def test_experience_filter_uses_normalized_bucket(
    categorized_dashboard_jobs,
):
    marker = categorized_dashboard_jobs[
        "marker"
    ]
    titles = categorized_dashboard_jobs[
        "titles"
    ]

    status, html = get_dashboard(
        "/?category=all"
        "&experience=THREE_TO_FIVE"
        f"&q={marker}"
    )

    assert status == 200
    assert titles["AI_DATA"] in html
    assert titles["SOFTWARE"] not in html


def test_salary_text_and_null_are_rendered(
    dashboard_jobs,
):
    marker = dashboard_jobs["marker"]

    salary_status, salary_html = (
        get_dashboard(
            "/?q="
            f"{marker}%20%E6%B8%AC%E8%A9%A6"
            "%E8%81%B7%E7%BC%BA%200"
        )
    )
    null_status, null_html = get_dashboard(
        "/?q="
        f"{marker}%20%E6%B8%AC%E8%A9%A6"
        "%E8%81%B7%E7%BC%BA%201"
    )

    assert salary_status == 200
    assert "薪資：月薪45,000~60,000元" in (
        salary_html
    )
    assert null_status == 200
    assert "薪資：未提供" in null_html
    assert "來源：104" in salary_html


def test_job_card_limits_visible_tech_chips(
    categorized_dashboard_jobs,
):
    marker = categorized_dashboard_jobs[
        "marker"
    ]
    title = categorized_dashboard_jobs[
        "titles"
    ]["AI_DATA"]

    status, html = get_dashboard(
        "/?category=AI_DATA"
        f"&q={marker}"
    )
    soup = BeautifulSoup(
        html,
        "html.parser",
    )
    card = next(
        article
        for article in soup.select(
            "article.job"
        )
        if title in article.get_text(
            " ",
            strip=True,
        )
    )

    assert status == 200
    assert len(
        card.select(
            ".tech-chip:not(.tech-chip--more)"
        )
    ) == 5
    assert card.select_one(
        ".tech-chip--more"
    ).get_text(strip=True) == "+1"
