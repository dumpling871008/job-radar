from datetime import datetime, timezone

from app.models.job import Job
from app.repositories.job_application_repository import (
    JobApplicationRepository,
)


JOB_APPLICATION_STATUSES = (
    "UNREAD",
    "SAVED",
    "APPLIED",
    "INTERVIEW",
    "REJECTED",
    "CLOSED",
)


class JobApplicationService:

    def __init__(self, session):
        self.session = session
        self.repository = (
            JobApplicationRepository(
                session
            )
        )


    def ensure_job_exists(self, job_id):
        if self.session.get(
            Job,
            job_id,
        ) is None:
            raise LookupError(
                f"找不到 job：{job_id}"
            )


    def update_status(
        self,
        job_id,
        status,
    ):
        normalized_status = (
            status.strip().upper()
        )

        if (
            normalized_status
            not in JOB_APPLICATION_STATUSES
        ):
            raise ValueError(
                f"不支援的求職狀態："
                f"{status}"
            )

        self.ensure_job_exists(job_id)

        application = (
            self.repository.update_status(
                job_id,
                normalized_status,
            )
        )

        now = datetime.now(
            timezone.utc
        )

        if (
            normalized_status == "APPLIED"
            and application.applied_at is None
        ):
            application.applied_at = now

        if (
            normalized_status == "INTERVIEW"
            and application.interview_at is None
        ):
            application.interview_at = now

        return application


    def update_note(
        self,
        job_id,
        note,
    ):
        self.ensure_job_exists(job_id)

        return self.repository.update_note(
            job_id,
            note,
        )
