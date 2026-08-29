from datetime import datetime, timezone

from app.api.presentation import (
    format_datetime_taipei,
    normalize_preview,
)


def test_datetime_is_displayed_in_taipei_without_microseconds():
    value = datetime(
        2026,
        8,
        28,
        8,
        59,
        1,
        273339,
        tzinfo=timezone.utc,
    )

    assert format_datetime_taipei(
        value
    ) == "2026/08/28 16:59"


def test_preview_collapses_whitespace():
    assert normalize_preview(
        "工作內容：\n\n 1. Python\t開發  2. API"
    ) == "工作內容： 1. Python 開發 2. API"


def test_long_preview_adds_ellipsis():
    assert normalize_preview(
        "abcdef",
        max_length=5,
    ) == "abcde…"


def test_short_preview_does_not_add_ellipsis():
    assert normalize_preview(
        "短文字",
        max_length=5,
    ) == "短文字"
