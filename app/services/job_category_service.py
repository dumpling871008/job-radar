from collections import Counter

from sqlalchemy import select

from app.crawler.job_classifier import (
    classify_job,
)
from app.models.job import Job


def backfill_job_categories(session):
    """只依既有 clean job 欄位重算分類，由呼叫端決定 commit。"""

    jobs = session.scalars(
        select(Job).order_by(Job.id)
    ).all()
    updated_count = 0
    category_counts = Counter()

    for job in jobs:
        category = classify_job(
            job.title,
            job.description or "",
        )
        category_counts[category] += 1

        if job.job_category != category:
            job.job_category = category
            updated_count += 1

    return {
        "scanned": len(jobs),
        "updated": updated_count,
        "categories": dict(
            sorted(category_counts.items())
        ),
    }
