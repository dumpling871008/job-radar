from contextlib import contextmanager

from sqlalchemy import text

from app.db.database import engine


# 固定使用同一組 lock key
# 只要所有 crawler 都使用這組 key，
# PostgreSQL 就能判斷是否已經有 crawler 在執行。
LOCK_KEY_1 = 104
LOCK_KEY_2 = 1


@contextmanager
def crawler_lock():

    # Advisory Lock 是 connection-scoped
    # 所以整個 crawler 執行期間，
    # 這個 connection 都不能關掉。
    with engine.connect() as connection:

        result = connection.execute(
            text(
                """
                SELECT pg_try_advisory_lock(
                    :key1,
                    :key2
                );
                """
            ),
            {
                "key1": LOCK_KEY_1,
                "key2": LOCK_KEY_2,
            },
        )

        acquired = result.scalar()

        if not acquired:
            yield False
            return

        try:
            yield True

        finally:
            connection.execute(
                text(
                    """
                    SELECT pg_advisory_unlock(
                        :key1,
                        :key2
                    );
                    """
                ),
                {
                    "key1": LOCK_KEY_1,
                    "key2": LOCK_KEY_2,
                },
            )