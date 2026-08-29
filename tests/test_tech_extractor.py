import pytest

from app.crawler.tech_extractor import (
    extract_tech_stack,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    (
        (
            "Python FastAPI Postgres",
            ["Python", "FastAPI", "PostgreSQL"],
        ),
        (
            "Java developer with Spring Boot",
            ["Java", "Spring Boot"],
        ),
        (
            "React frontend written in TypeScript",
            ["TypeScript", "React"],
        ),
        (
            "Deploy to GCP with Docker and Kubernetes",
            ["Docker", "Kubernetes", "GCP"],
        ),
    ),
)
def test_extracts_supported_tech_stack(
    text,
    expected,
):
    assert extract_tech_stack(
        "工程師",
        text,
    ) == expected


def test_normal_english_go_is_not_go_language():
    assert "Go" not in extract_tech_stack(
        "Operations specialist",
        "We go to the office twice a week.",
    )


@pytest.mark.parametrize(
    "alias",
    ("Postgres", "postgresql"),
)
def test_postgres_alias_is_normalized(alias):
    assert extract_tech_stack(
        "Backend Engineer",
        f"Database: {alias}",
    ) == ["PostgreSQL"]


def test_go_in_tech_list_is_detected():
    assert "Go" in extract_tech_stack(
        "Backend Engineer",
        "Languages: Python / Go / Java",
    )
