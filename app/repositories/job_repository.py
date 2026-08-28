from datetime import datetime, timezone

from sqlalchemy import select

from app.models.job import Job


class JobRepository:

    def __init__(self, session):
        self.session = session


    def find_by_source_job_id(
        self,
        source_job_id,
    ):
        statement = (
            select(Job)
            .where(
                Job.source_job_id
                == source_job_id
            )
        )

        return self.session.scalar(
            statement
        )


    def upsert(self, job_data):
        """
        新職缺 → INSERT
        舊職缺內容改變 → UPDATE
        舊職缺沒有改變 → 只更新 last_seen_at

        回傳：
        new
        updated
        unchanged
        """

        source_job_id = str(
            job_data["job_no"]
        )

        existing_job = (
            self.find_by_source_job_id(
                source_job_id
            )
        )

        now = datetime.now(
            timezone.utc
        )


        # =====================
        # 新職缺
        # =====================

        if existing_job is None:

            new_job = Job(
                source="104",

                source_job_id=(
                    source_job_id
                ),

                title=job_data.get(
                    "job_name",
                    "",
                ),

                company_name=job_data.get(
                    "company_name",
                    "",
                ),

                location=job_data.get(
                    "location",
                    "",
                ),

                description_summary=(
                    job_data.get(
                        "description_summary",
                        "",
                    )
                ),

                description=job_data.get(
                    "description",
                    "",
                ),

                url=job_data.get(
                    "url",
                    "",
                ),

                experience=job_data.get(
                    "experience",
                    "",
                ),

                education=job_data.get(
                    "education",
                    "",
                ),

                content_hash=job_data.get(
                    "content_hash",
                    "",
                ),

                first_seen_at=now,
                last_seen_at=now,
            )

            self.session.add(
                new_job
            )

            return "new"


        # =====================
        # 已存在職缺
        # =====================

        content_changed = (
            existing_job.content_hash
            != job_data.get(
                "content_hash",
                "",
            )
        )

        # 不管有沒有改變
        # 都代表今天再次看到它
        existing_job.last_seen_at = now


        # =====================
        # JD 有變
        # =====================

        if content_changed:

            existing_job.title = (
                job_data.get(
                    "job_name",
                    "",
                )
            )

            existing_job.company_name = (
                job_data.get(
                    "company_name",
                    "",
                )
            )

            existing_job.location = (
                job_data.get(
                    "location",
                    "",
                )
            )

            existing_job.description_summary = (
                job_data.get(
                    "description_summary",
                    "",
                )
            )

            existing_job.description = (
                job_data.get(
                    "description",
                    "",
                )
            )

            existing_job.url = (
                job_data.get(
                    "url",
                    "",
                )
            )

            existing_job.experience = (
                job_data.get(
                    "experience",
                    "",
                )
            )

            existing_job.education = (
                job_data.get(
                    "education",
                    "",
                )
            )

            existing_job.content_hash = (
                job_data.get(
                    "content_hash",
                    "",
                )
            )

            return "updated"


        return "unchanged"