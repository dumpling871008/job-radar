import time
from datetime import (
    datetime,
    timedelta,
    timezone,
)

from app.crawler.client import (
    DetailAccessForbiddenError,
    fetch_job_detail,
    fetch_search_page,
)
from app.crawler.transform import (
    transform_job,
)
from app.db.database import SessionLocal
from app.repositories.job_repository import (
    JobRepository,
)
from app.services.crawler_failure_service import (
    save_crawler_failure,
)


def find_existing_jobs(source_job_ids):
    """Load one Search batch with a single IN query."""
    with SessionLocal() as session:
        repository = JobRepository(session)
        jobs = (
            repository.find_by_source_job_ids(
                source_job_ids
            )
        )

        return {
            job.source_job_id: job
            for job in jobs
        }


def select_detail_candidates(
    search_jobs,
    existing_jobs,
    *,
    detail_refresh_hours,
    now=None,
    max_candidates=None,
):
    now = now or datetime.now(
        timezone.utc
    )
    stale_before = now - timedelta(
        hours=detail_refresh_hours
    )
    candidates = []
    stats = {
        "new_candidate_count": 0,
        "refresh_candidate_count": 0,
        "fresh_skipped_count": 0,
    }

    for job_data in search_jobs:
        source_job_id = str(
            job_data.get("jobNo", "")
        )
        existing_job = existing_jobs.get(
            source_job_id
        )

        if existing_job is None:
            candidate_type = "NEW"
        elif (
            existing_job.last_detail_checked_at
            is None
            or existing_job.last_detail_checked_at
            < stale_before
        ):
            candidate_type = "STALE"
        else:
            stats[
                "fresh_skipped_count"
            ] += 1
            continue

        if (
            max_candidates is not None
            and len(candidates)
            >= max_candidates
        ):
            continue

        candidates.append(job_data)

        if candidate_type == "NEW":
            stats[
                "new_candidate_count"
            ] += 1
        else:
            stats[
                "refresh_candidate_count"
            ] += 1

    return candidates, stats


def save_search_failure(
    run_id,
    error,
):
    response = getattr(
        error,
        "response",
        None,
    )

    save_crawler_failure(
        run_id=run_id,
        stage="SEARCH",
        attempt_count=1,
        http_status=getattr(
            response,
            "status_code",
            None,
        ),
        error_type=type(error).__name__,
        error_message=str(error),
    )


def collect_detail_candidates(
    run_id,
    runtime_config,
):
    keywords = runtime_config["keywords"]
    max_detail_fetches = runtime_config[
        "max_detail_fetches"
    ]
    max_search_pages = runtime_config[
        "max_search_pages_per_keyword"
    ]
    detail_refresh_hours = runtime_config[
        "detail_refresh_hours"
    ]
    candidate_jobs = []
    seen_job_ids = set()
    keyword_counts = {}
    stats = {
        "search_count": 0,
        "search_unique_count": 0,
        "new_candidate_count": 0,
        "refresh_candidate_count": 0,
        "fresh_skipped_count": 0,
    }

    for keyword_config in keywords:
        keyword = keyword_config["keyword"]
        quota = keyword_config[
            "target_count"
        ]
        keyword_candidate_count = 0

        if quota <= 0:
            keyword_counts[keyword] = 0
            continue

        print("=" * 50)
        print(
            f"開始搜尋：{keyword}"
            f"（candidate 上限 {quota} 筆）"
        )

        for page in range(
            1,
            max_search_pages
            + 1,
        ):
            if (
                len(candidate_jobs)
                >= max_detail_fetches
                or keyword_candidate_count
                >= quota
            ):
                break

            print(
                f"正在抓「{keyword}」"
                f"第 {page} 頁..."
            )

            try:
                search_jobs = fetch_search_page(
                    keyword=keyword,
                    page=page,
                )
            except Exception as error:
                save_search_failure(
                    run_id,
                    error,
                )
                raise

            stats["search_count"] += len(
                search_jobs
            )

            if not search_jobs:
                break

            unique_search_jobs = []
            unique_job_ids = []

            for job_data in search_jobs:
                source_job_id = str(
                    job_data.get(
                        "jobNo",
                        "",
                    )
                )

                if (
                    not source_job_id
                    or source_job_id
                    in seen_job_ids
                ):
                    continue

                seen_job_ids.add(
                    source_job_id
                )
                unique_job_ids.append(
                    source_job_id
                )
                unique_search_jobs.append(
                    job_data
                )

            stats[
                "search_unique_count"
            ] += len(unique_search_jobs)

            if not unique_search_jobs:
                continue

            existing_jobs = find_existing_jobs(
                unique_job_ids
            )
            remaining_budget = min(
                max_detail_fetches
                - len(candidate_jobs),
                quota
                - keyword_candidate_count,
            )
            page_candidates, page_stats = (
                select_detail_candidates(
                    unique_search_jobs,
                    existing_jobs,
                    max_candidates=(
                        remaining_budget
                    ),
                    detail_refresh_hours=(
                        detail_refresh_hours
                    ),
                )
            )

            candidate_jobs.extend(
                page_candidates
            )
            keyword_candidate_count += len(
                page_candidates
            )

            for key in (
                "new_candidate_count",
                "refresh_candidate_count",
                "fresh_skipped_count",
            ):
                stats[key] += page_stats[key]

            print(
                f"目前累積 "
                f"{len(candidate_jobs)} 個 "
                "Detail candidates"
            )

        keyword_counts[keyword] = (
            keyword_candidate_count
        )

        if (
            len(candidate_jobs)
            >= max_detail_fetches
        ):
            break

    stats["keyword_counts"] = (
        keyword_counts
    )

    return candidate_jobs, stats


def record_detail_failure(
    *,
    run_id,
    source_job_id,
    error,
):
    save_crawler_failure(
        run_id=run_id,
        stage="DETAIL",
        source_job_id=source_job_id,
        attempt_count=getattr(
            error,
            "attempt_count",
            1,
        ),
        http_status=getattr(
            error,
            "http_status",
            None,
        ),
        error_type=type(error).__name__,
        error_message=str(error),
    )


def crawl_jobs(
    run_id,
    runtime_config,
):
    selected_jobs, selection_stats = (
        collect_detail_candidates(
            run_id,
            runtime_config,
        )
    )
    request_interval_seconds = (
        runtime_config[
            "request_interval_seconds"
        ]
    )

    print("=" * 50)
    print(
        f"最終選出 {len(selected_jobs)} 個 "
        "Detail candidates"
    )

    clean_jobs = []
    raw_jobs = []
    success_count = 0
    failed_count = 0
    failed_jobs = []
    detail_attempted_count = 0
    stopped_by_forbidden = False

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
            job_data.get("jobNo", "")
        )

        if not job_url:
            failed_count += 1
            failed_jobs.append(job_no)
            continue

        if (
            detail_attempted_count > 0
            and request_interval_seconds > 0
        ):
            time.sleep(
                request_interval_seconds
            )

        detail_attempted_count += 1

        print(
            f"[{index}/{len(selected_jobs)}] "
            "正在抓完整 JD："
            f"{job_name}"
        )

        try:
            detail_data, _ = (
                fetch_job_detail(job_url)
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
            clean_jobs.append(job)

            if job["description"]:
                success_count += 1
            else:
                failed_count += 1
                failed_jobs.append(job_no)

        except DetailAccessForbiddenError as error:
            failed_count += 1
            failed_jobs.append(job_no)
            record_detail_failure(
                run_id=run_id,
                source_job_id=job_no,
                error=error,
            )
            stopped_by_forbidden = True

            print(
                "Detail API 回傳 403，"
                "安全停止本次 Detail 抓取。"
            )
            break

        except Exception as error:
            failed_count += 1
            failed_jobs.append(job_no)
            record_detail_failure(
                run_id=run_id,
                source_job_id=job_no,
                error=error,
            )

            print(f"取得失敗：{job_no}")
            print(f"原因：{error}")

    stats = {
        **selection_stats,
        "selected_count": len(
            selected_jobs
        ),
        "detail_attempted_count": (
            detail_attempted_count
        ),
        "success_count": success_count,
        "failed_count": failed_count,
        "failed_jobs": failed_jobs,
        "stopped_by_forbidden": (
            stopped_by_forbidden
        ),
    }

    return clean_jobs, raw_jobs, stats
