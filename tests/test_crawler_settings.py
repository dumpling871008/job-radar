from uuid import uuid4

import pytest

from app.config import (
    DETAIL_REFRESH_HOURS,
    MAX_DETAIL_FETCHES,
    MAX_SEARCH_PAGES_PER_KEYWORD,
    REQUEST_INTERVAL_SECONDS,
)
from app.db.database import SessionLocal
from app.models.crawler_setting import (
    CrawlerSetting,
)
from app.services.crawler_settings_service import (
    CrawlerSettingsService,
)
from app.repositories.crawler_run_repository import (
    CrawlerRunRepository,
)


@pytest.fixture
def settings_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_missing_singleton_uses_config_defaults(
    settings_session,
):
    existing = settings_session.get(
        CrawlerSetting,
        1,
    )
    settings_session.delete(existing)
    settings_session.flush()

    settings = CrawlerSettingsService(
        settings_session
    ).get_settings()

    assert settings.max_detail_fetches == (
        MAX_DETAIL_FETCHES
    )
    assert (
        settings.max_search_pages_per_keyword
        == MAX_SEARCH_PAGES_PER_KEYWORD
    )
    assert settings.detail_refresh_hours == (
        DETAIL_REFRESH_HOURS
    )
    assert settings.request_interval_seconds == (
        REQUEST_INTERVAL_SECONDS
    )


def test_update_settings_is_saved_in_session(
    settings_session,
):
    service = CrawlerSettingsService(
        settings_session
    )
    settings = service.update_settings(
        max_detail_fetches=88,
        max_search_pages_per_keyword=6,
        detail_refresh_hours=72,
        request_interval_seconds=2.5,
    )
    settings_session.flush()

    assert settings.max_detail_fetches == 88
    assert (
        service.get_settings()
        .max_detail_fetches
        == 88
    )


def test_add_keyword_and_reject_duplicate(
    settings_session,
):
    service = CrawlerSettingsService(
        settings_session
    )
    keyword = f"測試 {uuid4().hex}"

    created = service.add_keyword(
        keyword=f"  {keyword}  ",
        enabled=True,
        target_count=25,
        sort_order=90,
    )
    settings_session.flush()

    assert created.keyword == keyword
    assert created.target_count == 25

    with pytest.raises(
        ValueError,
        match="已存在",
    ):
        service.add_keyword(
            keyword=keyword.lower(),
            enabled=True,
            target_count=10,
        )


def test_disabled_keyword_is_not_in_runtime_config(
    settings_session,
):
    service = CrawlerSettingsService(
        settings_session
    )
    disabled = f"停用 {uuid4().hex}"
    enabled = f"啟用 {uuid4().hex}"
    service.add_keyword(
        keyword=disabled,
        enabled=False,
        target_count=20,
    )
    service.add_keyword(
        keyword=enabled,
        enabled=True,
        target_count=30,
    )
    settings_session.flush()

    runtime_keywords = {
        item["keyword"]
        for item in service.get_runtime_config()[
            "keywords"
        ]
    }

    assert enabled in runtime_keywords
    assert disabled not in runtime_keywords


def test_invalid_pages_and_interval_are_rejected(
    settings_session,
):
    service = CrawlerSettingsService(
        settings_session
    )

    with pytest.raises(ValueError):
        service.update_settings(
            max_detail_fetches=100,
            max_search_pages_per_keyword=21,
            detail_refresh_hours=48,
            request_interval_seconds=2,
        )

    with pytest.raises(ValueError):
        service.update_settings(
            max_detail_fetches=100,
            max_search_pages_per_keyword=8,
            detail_refresh_hours=48,
            request_interval_seconds=0.9,
        )


def test_crawler_run_persists_config_snapshot(
    settings_session,
):
    run_id = f"snapshot-{uuid4().hex}"
    snapshot = {
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
    }
    repository = CrawlerRunRepository(
        settings_session
    )
    repository.create(
        run_id=run_id,
        config_snapshot=snapshot,
    )
    settings_session.flush()

    assert repository.get(
        run_id
    ).config_snapshot == snapshot
