from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select

from app.db.database import SessionLocal
from app.models.job import Job
from app.models.job_application import (
    JobApplication,
)
from app.repositories.job_application_repository import (
    JobApplicationRepository,
)
from app.services.job_application_service import (
    JobApplicationService,
)
from tests.test_dashboard import request_app


def make_job(marker, suffix="job"):
    return Job(
        source="104",
        source_job_id=(
            f"ja-{marker[:20]}-{suffix}"
        ),
        title=f"{marker} Python 工程師 {suffix}",
        company_name="求職狀態測試公司",
        location="測試市測試區",
        description="Python dashboard test",
        job_category="SOFTWARE",
        url=(
            "https://www.104.com.tw/job/"
            f"application-{suffix}"
        ),
        first_seen_at=datetime.now(
            timezone.utc
        ),
        content_updated_at=datetime.now(
            timezone.utc
        ),
    )


@pytest.fixture
def application_session():
    session = SessionLocal()
    marker = uuid4().hex
    job = make_job(marker)
    session.add(job)
    session.flush()

    try:
        yield session, job
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def dashboard_application_jobs():
    marker = uuid4().hex
    unread_job = make_job(
        marker,
        "unread",
    )
    saved_job = make_job(
        marker,
        "saved",
    )

    with SessionLocal() as session:
        session.add_all(
            [unread_job, saved_job]
        )
        session.flush()
        saved_application = JobApplication(
            job_id=saved_job.id,
            status="SAVED",
        )
        session.add(saved_application)
        session.commit()

        result = {
            "marker": marker,
            "unread_id": unread_job.id,
            "saved_id": saved_job.id,
            "unread_title": unread_job.title,
            "saved_title": saved_job.title,
        }

    yield result

    with SessionLocal() as session:
        job_ids = select(Job.id).where(
            Job.source_job_id.startswith(
                f"ja-{marker[:20]}-"
            )
        )
        session.execute(
            delete(JobApplication).where(
                JobApplication.job_id.in_(
                    job_ids
                )
            )
        )
        session.execute(
            delete(Job).where(
                Job.source_job_id.startswith(
                    f"ja-{marker[:20]}-"
                )
            )
        )
        session.commit()


def test_first_status_update_creates_application(
    application_session,
):
    session, job = application_session
    service = JobApplicationService(session)

    application = service.update_status(
        job.id,
        "SAVED",
    )
    session.flush()

    assert application.status == "SAVED"
    assert (
        JobApplicationRepository(
            session
        ).get_by_job_id(job.id)
        is application
    )


def test_second_update_does_not_create_duplicate(
    application_session,
):
    session, job = application_session
    service = JobApplicationService(session)

    first = service.update_status(
        job.id,
        "SAVED",
    )
    second = service.update_status(
        job.id,
        "APPLIED",
    )
    session.flush()

    count = session.scalar(
        select(
            func.count(JobApplication.id)
        ).where(
            JobApplication.job_id
            == job.id
        )
    )

    assert first.id == second.id
    assert count == 1


def test_applied_sets_applied_at(
    application_session,
):
    session, job = application_session
    application = JobApplicationService(
        session
    ).update_status(
        job.id,
        "APPLIED",
    )

    assert application.applied_at is not None


def test_interview_sets_interview_at(
    application_session,
):
    session, job = application_session
    application = JobApplicationService(
        session
    ).update_status(
        job.id,
        "INTERVIEW",
    )

    assert application.interview_at is not None


def test_note_is_saved(
    application_session,
):
    session, job = application_session
    application = JobApplicationService(
        session
    ).update_note(
        job.id,
        "下週準備技術面試",
    )
    session.flush()

    assert application.note == (
        "下週準備技術面試"
    )


def test_invalid_status_is_rejected(
    application_session,
):
    session, job = application_session

    with pytest.raises(ValueError):
        JobApplicationService(
            session
        ).update_status(
            job.id,
            "UNKNOWN",
        )


def test_status_post_updates_application(
    dashboard_application_jobs,
):
    job_id = dashboard_application_jobs[
        "unread_id"
    ]

    status, _, _ = request_app(
        f"/jobs/{job_id}/status",
        method="POST",
        data={"status": "APPLIED"},
    )

    with SessionLocal() as session:
        application = session.scalar(
            select(JobApplication).where(
                JobApplication.job_id
                == job_id
            )
        )

    assert status == 303
    assert application is not None
    assert application.status == "APPLIED"
    assert application.applied_at is not None


def test_note_post_updates_application(
    dashboard_application_jobs,
):
    job_id = dashboard_application_jobs[
        "unread_id"
    ]

    status, _, _ = request_app(
        f"/jobs/{job_id}/note",
        method="POST",
        data={"note": "已聯絡 HR"},
    )

    with SessionLocal() as session:
        application = session.scalar(
            select(JobApplication).where(
                JobApplication.job_id
                == job_id
            )
        )

    assert status == 303
    assert application is not None
    assert application.note == "已聯絡 HR"


def test_saved_status_filter(
    dashboard_application_jobs,
):
    status, html, _ = request_app(
        "/?status=SAVED&q="
        f"{dashboard_application_jobs['marker']}"
    )

    assert status == 200
    assert (
        dashboard_application_jobs[
            "saved_title"
        ]
        in html
    )
    assert (
        dashboard_application_jobs[
            "unread_title"
        ]
        not in html
    )


def test_unread_filter_includes_job_without_application(
    dashboard_application_jobs,
):
    status, html, _ = request_app(
        "/?status=UNREAD&q="
        f"{dashboard_application_jobs['marker']}"
    )

    assert status == 200
    assert (
        dashboard_application_jobs[
            "unread_title"
        ]
        in html
    )
    assert (
        dashboard_application_jobs[
            "saved_title"
        ]
        not in html
    )


def test_status_filter_coexists_with_other_filters(
    dashboard_application_jobs,
):
    status, html, _ = request_app(
        "/?view=updated&status=SAVED"
        "&location=%E6%B8%AC%E8%A9%A6%E5%B8%82"
        "&q="
        f"{dashboard_application_jobs['marker']}"
        "&sort=first_seen&page=1"
    )

    assert status == 200
    assert (
        dashboard_application_jobs[
            "saved_title"
        ]
        in html
    )
    assert (
        dashboard_application_jobs[
            "unread_title"
        ]
        not in html
    )


def test_status_redirect_preserves_query_parameters(
    dashboard_application_jobs,
):
    job_id = dashboard_application_jobs[
        "unread_id"
    ]
    marker = dashboard_application_jobs[
        "marker"
    ]

    status, _, headers = request_app(
        f"/jobs/{job_id}/status",
        method="POST",
        data={
            "status": "INTERVIEW",
            "view": "updated",
            "q": marker,
            "location": "測試市",
            "sort": "first_seen",
            "page": "2",
            "filter_status": "UNREAD",
            "category": "SOFTWARE",
            "tech": "Python",
            "experience": "ONE_TO_THREE",
        },
    )
    query = parse_qs(
        urlsplit(
            headers["location"]
        ).query
    )

    assert status == 303
    assert query == {
        "view": ["updated"],
        "q": [marker],
        "location": ["測試市"],
        "sort": ["first_seen"],
        "status": ["UNREAD"],
        "category": ["SOFTWARE"],
        "tech": ["Python"],
        "experience": ["ONE_TO_THREE"],
        "page": ["2"],
    }
