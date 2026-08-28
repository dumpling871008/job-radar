from app.services.crawler_lock_service import crawler_lock


def test_crawler_lock_prevents_concurrent_runs():

    # =========================
    # 第一個 crawler 取得 lock
    # =========================

    with crawler_lock() as first_acquired:

        assert first_acquired is True

        # =========================
        # 第一個還沒結束
        # 第二個 crawler 嘗試取得
        # =========================

        with crawler_lock() as second_acquired:

            assert second_acquired is False


    # =========================
    # 第一個 crawler 已經結束
    # lock 應該已經釋放
    # =========================

    with crawler_lock() as third_acquired:

        assert third_acquired is True