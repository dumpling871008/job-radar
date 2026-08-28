from contextlib import contextmanager

from sqlalchemy import text

from app.db.database import engine


# 固定使用同一組 lock key
# 只要所有 crawler 都使用這組 key，
# PostgreSQL 就能判斷是否已經有 crawler 在執行。
LOCK_KEY_1 = 104
LOCK_KEY_2 = 1


class CrawlerLockReservation:

    def __init__(self, connection):
        self.connection = connection
        self.acquired = True


    def release(self):
        if not self.acquired:
            return

        try:
            self.connection.execute(
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
        except Exception as error:
            # 關閉 connection 也會由 PostgreSQL
            # 自動釋放 session-level advisory lock。
            print(
                "Crawler advisory lock "
                f"解鎖失敗：{error}"
            )
        finally:
            self.acquired = False

            try:
                self.connection.close()
            except Exception as error:
                print(
                    "Crawler lock connection "
                    f"關閉失敗：{error}"
                )


def acquire_crawler_lock():
    """Try to reserve the crawler lock without blocking."""
    connection = engine.connect()

    try:
        acquired = connection.execute(
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
        ).scalar()
    except Exception:
        connection.close()
        raise

    if not acquired:
        connection.close()
        return None

    return CrawlerLockReservation(
        connection
    )


@contextmanager
def crawler_lock():
    # Advisory Lock 是 connection-scoped，reservation
    # 會讓同一條 connection 活到 pipeline 結束。
    reservation = acquire_crawler_lock()

    if reservation is None:
        yield False
        return

    try:
        yield True
    finally:
        reservation.release()
