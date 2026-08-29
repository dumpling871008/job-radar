import pytest

from app.crawler.experience_normalizer import (
    normalize_experience,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        ("不拘", "NO_REQUIREMENT"),
        ("無經驗可", "NO_EXPERIENCE"),
        ("1年以下", "UNDER_ONE"),
        ("1年以上", "ONE_TO_THREE"),
        ("2年以上", "ONE_TO_THREE"),
        ("3年以上", "THREE_TO_FIVE"),
        ("5年以上", "FIVE_PLUS"),
        ("10年以上", "FIVE_PLUS"),
        ("面議", "UNKNOWN"),
    ),
)
def test_normalize_experience(value, expected):
    assert normalize_experience(value) == expected
