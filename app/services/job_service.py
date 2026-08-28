from app.db.database import (
    SessionLocal,
)

from app.repositories.job_repository import (
    JobRepository,
)


def save_jobs(jobs):

    new_count = 0
    updated_count = 0
    unchanged_count = 0

    with SessionLocal() as session:

        repository = JobRepository(
            session
        )

        try:

            for job in jobs:

                result = (
                    repository.upsert(
                        job
                    )
                )

                if result == "new":
                    new_count += 1

                elif result == "updated":
                    updated_count += 1

                elif result == "unchanged":
                    unchanged_count += 1


            # 所有職缺都處理完成
            # 才正式寫入 DB
            session.commit()


        except Exception:

            # 中途出錯
            # 整批取消
            session.rollback()

            raise


    return {
        "new_count": new_count,
        "updated_count": updated_count,
        "unchanged_count": (
            unchanged_count
        ),
    }