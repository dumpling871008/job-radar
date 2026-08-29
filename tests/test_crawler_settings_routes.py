from uuid import uuid4

from sqlalchemy import delete, select

from app.db.database import SessionLocal
from app.models.crawler_keyword import (
    CrawlerKeyword,
)
from app.models.crawler_setting import (
    CrawlerSetting,
)
from tests.test_dashboard import request_app


def test_crawler_settings_page_returns_200():
    status, html, _ = request_app(
        "/settings/crawler"
    )

    assert status == 200
    assert "Crawler Parameters" in html
    assert "Search Keywords" in html
    assert "Crawler Settings" in html


def test_settings_post_updates_and_invalid_value_does_not_persist():
    with SessionLocal() as session:
        settings = session.get(
            CrawlerSetting,
            1,
        )
        original = {
            "max_detail_fetches": (
                settings.max_detail_fetches
            ),
            "max_search_pages_per_keyword": (
                settings
                .max_search_pages_per_keyword
            ),
            "detail_refresh_hours": (
                settings.detail_refresh_hours
            ),
            "request_interval_seconds": (
                settings
                .request_interval_seconds
            ),
        }

    try:
        status, _, _ = request_app(
            "/settings/crawler",
            method="POST",
            data={
                "max_detail_fetches": "87",
                "max_search_pages_per_keyword": "7",
                "detail_refresh_hours": "72",
                "request_interval_seconds": "2.5",
            },
        )
        assert status == 303

        with SessionLocal() as session:
            settings = session.get(
                CrawlerSetting,
                1,
            )
            assert settings.max_detail_fetches == 87

        invalid_status, _, _ = request_app(
            "/settings/crawler",
            method="POST",
            data={
                "max_detail_fetches": "90",
                "max_search_pages_per_keyword": "21",
                "detail_refresh_hours": "72",
                "request_interval_seconds": "0.5",
            },
        )
        assert invalid_status == 422

        with SessionLocal() as session:
            settings = session.get(
                CrawlerSetting,
                1,
            )
            assert settings.max_detail_fetches == 87
            assert (
                settings
                .max_search_pages_per_keyword
                == 7
            )
    finally:
        with SessionLocal() as session:
            settings = session.get(
                CrawlerSetting,
                1,
            )
            for field, value in original.items():
                setattr(settings, field, value)
            session.commit()


def test_keyword_add_and_disable_routes():
    keyword = f"Route 測試 {uuid4().hex}"
    keyword_id = None

    try:
        status, _, _ = request_app(
            "/settings/crawler/keywords",
            method="POST",
            data={
                "keyword": keyword,
                "enabled": "true",
                "target_count": "26",
                "sort_order": "99",
            },
        )
        assert status == 303

        with SessionLocal() as session:
            model = session.scalar(
                select(CrawlerKeyword).where(
                    CrawlerKeyword.keyword
                    == keyword
                )
            )
            assert model is not None
            assert model.target_count == 26
            keyword_id = model.id

        disable_status, _, _ = request_app(
            f"/settings/crawler/keywords/{keyword_id}",
            method="POST",
            data={
                "keyword": keyword,
                "target_count": "26",
                "sort_order": "99",
            },
        )
        assert disable_status == 303

        with SessionLocal() as session:
            model = session.get(
                CrawlerKeyword,
                keyword_id,
            )
            assert model.enabled is False
    finally:
        with SessionLocal() as session:
            session.execute(
                delete(CrawlerKeyword).where(
                    CrawlerKeyword.keyword
                    == keyword
                )
            )
            session.commit()
