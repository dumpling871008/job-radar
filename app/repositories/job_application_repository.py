from sqlalchemy import select

from app.models.job_application import (
    JobApplication,
)


class JobApplicationRepository:

    def __init__(self, session):
        self.session = session


    def get_by_job_id(self, job_id):
        statement = (
            select(JobApplication)
            .where(
                JobApplication.job_id
                == job_id
            )
        )

        return self.session.scalar(
            statement
        )


    def create_or_get(self, job_id):
        application = (
            self.get_by_job_id(
                job_id
            )
        )

        if application is not None:
            return application

        application = JobApplication(
            job_id=job_id,
            status="UNREAD",
        )

        self.session.add(application)
        self.session.flush()

        return application


    def update_status(
        self,
        job_id,
        status,
    ):
        application = (
            self.create_or_get(
                job_id
            )
        )

        application.status = status

        return application


    def update_note(
        self,
        job_id,
        note,
    ):
        application = (
            self.create_or_get(
                job_id
            )
        )

        application.note = note

        return application
