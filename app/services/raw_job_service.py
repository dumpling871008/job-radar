import hashlib
import json

from app.db.database import SessionLocal

from app.repositories.raw_job_repository import (
    RawJobRepository,
)


def generate_raw_hash(raw_data):

    raw_text = json.dumps(
        raw_data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        raw_text.encode("utf-8")
    ).hexdigest()


def save_raw_jobs(
    raw_jobs,
    crawler_run_id=None,
):

    inserted_count = 0

    with SessionLocal() as session:

        repository = RawJobRepository(
            session
        )

        try:

            for raw_job in raw_jobs:

                raw_data = raw_job["raw_data"]

                content_hash = (
                    generate_raw_hash(
                        raw_data
                    )
                )

                repository.add_snapshot(
                    source="104",

                    source_job_id=str(
                        raw_job["source_job_id"]
                    ),

                    source_url=(
                        raw_job["source_url"]
                    ),

                    raw_data=raw_data,

                    content_hash=content_hash,

                    crawler_run_id=(
                        crawler_run_id
                    ),
                )

                inserted_count += 1

            session.commit()

        except Exception:

            session.rollback()

            raise

    return {
        "inserted_count": inserted_count,
    }