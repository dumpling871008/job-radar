from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.database import SessionLocal
from app.services.job_enrichment_service import (
    backfill_job_enrichment,
)


def main():
    with SessionLocal() as session:
        result = backfill_job_enrichment(
            session
        )
        session.commit()

    print(
        "job enrichment backfill completed: "
        f"scanned={result['scanned']}, "
        f"updated={result['updated']}, "
        "salary_updated="
        f"{result['salary_updated']}"
    )


if __name__ == "__main__":
    main()
