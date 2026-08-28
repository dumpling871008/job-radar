from uuid import uuid4

from app.services.crawler_service import (
    crawl_jobs,
)

from app.services.raw_job_service import (
    save_raw_jobs,
)

from app.services.job_service import (
    save_jobs,
)

from app.services.crawler_run_service import (
    start_crawler_run,
    finish_crawler_run,
)

from app.services.crawler_lock_service import (
    crawler_lock,
)


def main():

    print("=" * 50)
    print("Job Radar")
    print("準備啟動 crawler...")


    # =========================
    # 防止 crawler 同時執行
    # =========================

    with crawler_lock() as acquired:

        if not acquired:

            print("=" * 50)
            print(
                "目前已經有另一個 crawler "
                "正在執行。"
            )

            print(
                "本次執行取消。"
            )

            return


        print("Crawler Lock 取得成功")


        # =========================
        # 建立這次 Run ID
        # =========================

        run_id = uuid4().hex

        print(
            f"Run ID：{run_id}"
        )


        # =========================
        # Audit：RUNNING
        # =========================

        start_crawler_run(
            run_id=run_id,
            trigger_type="MANUAL",
        )


        crawler_stats = {}
        raw_stats = {}
        db_stats = {}


        try:

            # =====================
            # Extract + Transform
            # =====================

            jobs, raw_jobs, crawler_stats = (
                crawl_jobs(
                    run_id=run_id
                )
            )


            # =====================
            # Raw Layer
            # =====================

            print("=" * 50)
            print(
                "開始寫入 Raw Layer..."
            )

            raw_stats = save_raw_jobs(
                raw_jobs,
                crawler_run_id=run_id,
            )


            # =====================
            # Clean Layer
            # =====================

            print("=" * 50)
            print(
                "開始寫入 Clean Layer..."
            )

            db_stats = save_jobs(
                jobs
            )


            # =====================
            # 判斷 Pipeline Status
            # =====================

            if (
                crawler_stats.get(
                    "failed_count",
                    0,
                )
                > 0
            ):

                final_status = (
                    "PARTIAL_SUCCESS"
                )

            else:

                final_status = (
                    "SUCCESS"
                )


            # =====================
            # Audit：完成
            # =====================

            finish_crawler_run(
                run_id=run_id,
                status=final_status,
                crawler_stats=crawler_stats,
                raw_stats=raw_stats,
                db_stats=db_stats,
            )


            # =====================
            # Summary
            # =====================

            print("=" * 50)
            print("Crawler 執行完成")

            print(
                f"Run ID：{run_id}"
            )

            print(
                f"Status：{final_status}"
            )

            print(
                f"搜尋結果："
                f"{crawler_stats.get('search_count', 0)}"
            )

            print(
                f"選擇職缺："
                f"{crawler_stats.get('selected_count', 0)}"
            )

            print(
                f"JD 成功："
                f"{crawler_stats.get('success_count', 0)}"
            )

            print(
                f"JD 失敗："
                f"{crawler_stats.get('failed_count', 0)}"
            )

            print(
                f"Raw 新增："
                f"{raw_stats.get('inserted_count', 0)}"
            )

            print(
                f"Clean 新增："
                f"{db_stats.get('new_count', 0)}"
            )

            print(
                f"Clean 更新："
                f"{db_stats.get('updated_count', 0)}"
            )

            print(
                f"Clean 未變更："
                f"{db_stats.get('unchanged_count', 0)}"
            )


        except Exception as error:

            # =====================
            # Audit：FAILED
            # =====================

            finish_crawler_run(
                run_id=run_id,
                status="FAILED",
                crawler_stats=crawler_stats,
                raw_stats=raw_stats,
                db_stats=db_stats,
                error_message=str(error),
            )

            print("=" * 50)
            print("Crawler 執行失敗")

            print(
                f"Run ID：{run_id}"
            )

            print(
                f"錯誤：{error}"
            )

            raise


if __name__ == "__main__":
    main()