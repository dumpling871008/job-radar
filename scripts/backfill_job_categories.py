from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.database import SessionLocal
from app.services.job_category_service import (
    backfill_job_categories,
)


def main():
    with SessionLocal() as session:
        result = backfill_job_categories(
            session
        )
        session.commit()

    print(
        "job category backfill completed: "
        f"scanned={result['scanned']}, "
        f"updated={result['updated']}, "
        f"categories={result['categories']}"
    )


if __name__ == "__main__":
    main()
