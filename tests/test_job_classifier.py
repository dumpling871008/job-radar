import pytest

from app.crawler.job_classifier import (
    classify_job,
)


@pytest.mark.parametrize(
    "title",
    (
        "AI 影音暨數位媒體設計專員",
        "風控管理師",
        "數位服務營運 PM",
        "工務／工地現場監工",
    ),
)
def test_non_tech_titles_are_excluded_first(
    title,
):
    assert classify_job(title) == "NON_TECH"


@pytest.mark.parametrize(
    "title",
    (
        "製程工程師",
        "精密鑄造研發工程師",
    ),
)
def test_other_engineering_titles(title):
    assert classify_job(title) == (
        "OTHER_ENGINEERING"
    )


@pytest.mark.parametrize(
    ("title", "expected"),
    (
        ("Python 工程師", "SOFTWARE"),
        ("後端工程師", "SOFTWARE"),
        ("Full Stack Engineer", "SOFTWARE"),
        ("AI Engineer", "AI_DATA"),
        ("資料工程師", "AI_DATA"),
        ("DevOps Engineer", "DEVOPS_CLOUD"),
    ),
)
def test_relevant_technical_titles(
    title,
    expected,
):
    assert classify_job(title) == expected


def test_ai_design_role_is_not_misclassified():
    assert classify_job(
        "AI 影音暨數位媒體設計專員",
        "使用生成式 AI 製作影音與社群素材",
    ) == "NON_TECH"


def test_generic_engineer_is_not_automatically_software():
    assert classify_job(
        "品質工程師",
        "負責工廠品質管理",
    ) == "UNKNOWN"


def test_system_engineer_requires_it_description():
    assert classify_job(
        "系統工程師",
        "維護 Linux 伺服器與資訊系統",
    ) == "SOFTWARE"
    assert classify_job(
        "系統工程師",
        "維護工廠生產系統設備",
    ) == "UNKNOWN"
