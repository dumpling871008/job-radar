from app.config import (
    SEARCH_QUOTAS,
    MAX_JOBS,
    START_PAGE,
    END_PAGE,
)

from app.crawler.client import (
    fetch_search_page,
    fetch_job_detail,
)

from app.crawler.transform import (
    transform_job,
)

from app.services.crawler_failure_service import (
    save_crawler_failure,
)


def crawl_jobs(run_id):

    # =========================
    # 1. 多關鍵字搜尋
    # =========================

    selected_jobs = []

    # 用來全域去重
    seen_job_no = set()

    # 記錄 Search API 總共回傳多少資料
    search_count = 0

    # 記錄每個關鍵字最後取幾筆
    keyword_counts = {}

    for keyword, quota in SEARCH_QUOTAS.items():

        print("=" * 50)
        print(
            f"開始搜尋：{keyword}"
            f"（目標 {quota} 筆）"
        )

        keyword_added = 0

        for page in range(
            START_PAGE,
            END_PAGE + 1,
        ):

            # 這個 keyword 已經滿額
            if keyword_added >= quota:
                break

            # 全部已經 50 筆
            if len(selected_jobs) >= MAX_JOBS:
                break

            print(
                f"正在抓「{keyword}」"
                f"第 {page} 頁..."
            )

            jobs = fetch_search_page(
                keyword=keyword,
                page=page,
            )

            search_count += len(jobs)

            print(
                f"第 {page} 頁取得 "
                f"{len(jobs)} 筆搜尋結果"
            )

            # 如果這一頁完全沒資料
            # 就不用繼續翻頁
            if not jobs:
                break

            for job_data in jobs:

                job_no = str(
                    job_data.get(
                        "jobNo",
                        "",
                    )
                )

                # 沒有 jobNo 就不要
                if not job_no:
                    continue

                # 已經抓過就跳過
                if job_no in seen_job_no:
                    continue

                # 加入全域去重紀錄
                seen_job_no.add(job_no)

                selected_jobs.append(
                    job_data
                )

                keyword_added += 1

                # 此 keyword 已經滿額
                if keyword_added >= quota:
                    break

                # 全部已達 50
                if len(selected_jobs) >= MAX_JOBS:
                    break

        keyword_counts[keyword] = (
            keyword_added
        )

        print(
            f"「{keyword}」"
            f"實際加入 {keyword_added} 筆"
        )

        print(
            f"目前累積 "
            f"{len(selected_jobs)} 筆"
        )

        if len(selected_jobs) >= MAX_JOBS:
            break


    print("=" * 50)

    print(
        f"最終選出 "
        f"{len(selected_jobs)} 筆不重複職缺"
    )


    # =========================
    # 2. 抓完整 JD
    # =========================

    clean_jobs = []
    raw_jobs = []

    success_count = 0
    failed_count = 0

    failed_jobs = []

    total = len(selected_jobs)

    for index, job_data in enumerate(
        selected_jobs,
        start=1,
    ):

        job_name = job_data.get(
            "jobName",
            "",
        )

        job_url = (
            job_data
            .get("link", {})
            .get("job", "")
        )

        job_no = str(
            job_data.get(
                "jobNo",
                "",
            )
        )

        print(
            f"[{index}/{total}] "
            f"正在抓完整 JD："
            f"{job_name}"
        )

        if not job_url:

            failed_count += 1

            failed_jobs.append(
                job_no
            )

            continue

        try:

            detail_data, attempt_count = (
                fetch_job_detail(
                    job_url
                )
            )
            raw_job = {
                "source_job_id": job_no,
                "source_url": job_url,

                "raw_data": {
                    "search": job_data,
                    "detail": detail_data,
                },
            }

            raw_jobs.append(raw_job)
            job = transform_job(
                job_data,
                detail_data,
            )

            if job["description"]:

                success_count += 1

            else:

                failed_count += 1

                failed_jobs.append(
                    job_no
                )

            clean_jobs.append(job)

        except Exception as error:

            failed_count += 1

            failed_jobs.append(
                job_no
            )

            save_crawler_failure(
                run_id=run_id,
                stage="DETAIL",
                source_job_id=job_no,
                attempt_count=3,
                error_type=type(error).__name__,
                error_message=str(error),
            )

            print(
                f"取得失敗：{job_no}"
            )

            print(
                f"原因：{error}"
            )


    # =========================
    # 3. 統計
    # =========================

    stats = {
        "search_count": search_count,

        "selected_count": len(
            selected_jobs
        ),

        "success_count": success_count,

        "failed_count": failed_count,

        "failed_jobs": failed_jobs,

        "keyword_counts": (
            keyword_counts
        ),
    }

    return clean_jobs, raw_jobs, stats