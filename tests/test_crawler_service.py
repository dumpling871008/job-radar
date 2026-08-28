from datetime import (
    datetime,
    timedelta,
    timezone,
)
from types import SimpleNamespace

import app.services.crawler_service as crawler_service
from app.crawler.client import (
    DetailAccessForbiddenError,
)


def test_one_job_failure_should_not_stop_other_jobs(
    monkeypatch,
):
    """
    第一筆 Detail API 失敗，
    第二筆成功。

    預期：
    - crawler 不會整批中斷
    - success_count = 1
    - failed_count = 1
    - clean_jobs 有 1 筆
    - failure 有被記錄
    """

    # =========================
    # 測試時只搜尋一個 keyword
    # 而且只需要 2 筆
    # =========================

    monkeypatch.setattr(
        crawler_service,
        "SEARCH_QUOTAS",
        {
            "資料工程師": 2,
        },
    )

    monkeypatch.setattr(
        crawler_service,
        "MAX_DETAIL_FETCHES",
        2,
    )

    monkeypatch.setattr(
        crawler_service,
        "MAX_SEARCH_PAGES_PER_KEYWORD",
        1,
    )

    monkeypatch.setattr(
        crawler_service,
        "REQUEST_INTERVAL_SECONDS",
        0,
    )

    monkeypatch.setattr(
        crawler_service,
        "find_existing_jobs",
        lambda source_job_ids: {},
    )


    # =========================
    # 模擬 Search API
    # =========================

    fake_search_jobs = [
        {
            "jobNo": "111",
            "jobName": "失敗的資料工程師",
            "custName": "A 公司",
            "jobAddrNoDesc": "台北市",
            "description": "摘要 A",
            "link": {
                "job": "https://www.104.com.tw/job/aaa"
            },
        },
        {
            "jobNo": "222",
            "jobName": "成功的資料工程師",
            "custName": "B 公司",
            "jobAddrNoDesc": "新北市",
            "description": "摘要 B",
            "link": {
                "job": "https://www.104.com.tw/job/bbb"
            },
        },
    ]


    def fake_fetch_search_page(
        keyword,
        page,
    ):
        return fake_search_jobs


    monkeypatch.setattr(
        crawler_service,
        "fetch_search_page",
        fake_fetch_search_page,
    )


    # =========================
    # 模擬 Detail API
    # =========================

    def fake_fetch_job_detail(
        job_url,
    ):
        # 第一筆故意失敗
        if "aaa" in job_url:
            raise RuntimeError(
                "測試用 Detail API 錯誤"
            )

        # 第二筆成功
        return (
            {
                "header": {
                    "appearDate": "2026/08/28",
                },
                "jobDetail": {
                    "jobDescription": "完整 JD",
                },
                "condition": {
                    "workExp": "1年以上",
                    "edu": "大學以上",
                },
            },
            1,
        )


    monkeypatch.setattr(
        crawler_service,
        "fetch_job_detail",
        fake_fetch_job_detail,
    )


    # =========================
    # 不真的寫 crawler_failures DB
    # 只記錄有沒有被呼叫
    # =========================

    recorded_failures = []


    def fake_save_crawler_failure(
        **kwargs,
    ):
        recorded_failures.append(
            kwargs
        )


    monkeypatch.setattr(
        crawler_service,
        "save_crawler_failure",
        fake_save_crawler_failure,
    )


    # =========================
    # 執行 crawler
    # =========================

    clean_jobs, raw_jobs, stats = (
        crawler_service.crawl_jobs(
            run_id="test-run-001"
        )
    )


    # =========================
    # 驗證結果
    # =========================

    assert stats["success_count"] == 1
    assert stats["failed_count"] == 1

    assert len(clean_jobs) == 1
    assert len(raw_jobs) == 1

    assert clean_jobs[0]["job_no"] == "222"

    assert stats["failed_jobs"] == [
        "111"
    ]

    # failure 應該有被記錄
    assert len(recorded_failures) == 1

    assert (
        recorded_failures[0][
            "source_job_id"
        ]
        == "111"
    )

    assert (
        recorded_failures[0]["stage"]
        == "DETAIL"
    )


def search_job(job_no):
    return {
        "jobNo": str(job_no),
        "jobName": f"職缺 {job_no}",
        "custName": "測試公司",
        "jobAddrNoDesc": "台北市",
        "description": "摘要",
        "link": {
            "job": (
                "https://www.104.com.tw/job/"
                f"{job_no}"
            )
        },
    }


def test_new_job_is_detail_candidate():
    candidates, stats = (
        crawler_service.select_detail_candidates(
            [search_job("new")],
            {},
        )
    )

    assert [
        job["jobNo"]
        for job in candidates
    ] == ["new"]
    assert stats["new_candidate_count"] == 1


def test_recently_checked_job_is_skipped():
    now = datetime.now(timezone.utc)
    existing = SimpleNamespace(
        last_detail_checked_at=(
            now - timedelta(hours=1)
        )
    )

    candidates, stats = (
        crawler_service.select_detail_candidates(
            [search_job("fresh")],
            {"fresh": existing},
            now=now,
        )
    )

    assert candidates == []
    assert stats["fresh_skipped_count"] == 1


def test_stale_job_is_refresh_candidate():
    now = datetime.now(timezone.utc)
    existing = SimpleNamespace(
        last_detail_checked_at=(
            now
            - timedelta(
                hours=(
                    crawler_service
                    .DETAIL_REFRESH_HOURS
                    + 1
                )
            )
        )
    )

    candidates, stats = (
        crawler_service.select_detail_candidates(
            [search_job("stale")],
            {"stale": existing},
            now=now,
        )
    )

    assert len(candidates) == 1
    assert (
        stats["refresh_candidate_count"]
        == 1
    )


def test_null_detail_checked_at_is_refresh_candidate():
    existing = SimpleNamespace(
        last_detail_checked_at=None
    )

    candidates, stats = (
        crawler_service.select_detail_candidates(
            [search_job("null")],
            {"null": existing},
        )
    )

    assert len(candidates) == 1
    assert (
        stats["refresh_candidate_count"]
        == 1
    )


def configure_search_test(
    monkeypatch,
    *,
    quotas,
    max_details=120,
):
    monkeypatch.setattr(
        crawler_service,
        "SEARCH_QUOTAS",
        quotas,
    )
    monkeypatch.setattr(
        crawler_service,
        "MAX_DETAIL_FETCHES",
        max_details,
    )
    monkeypatch.setattr(
        crawler_service,
        "MAX_SEARCH_PAGES_PER_KEYWORD",
        1,
    )
    monkeypatch.setattr(
        crawler_service,
        "REQUEST_INTERVAL_SECONDS",
        0,
    )


def test_duplicate_across_keywords_fetches_detail_once(
    monkeypatch,
):
    configure_search_test(
        monkeypatch,
        quotas={"Python": 5, "Backend": 5},
    )
    detail_calls = []

    monkeypatch.setattr(
        crawler_service,
        "fetch_search_page",
        lambda keyword, page: [
            search_job("same-job")
        ],
    )
    monkeypatch.setattr(
        crawler_service,
        "find_existing_jobs",
        lambda source_job_ids: {},
    )
    monkeypatch.setattr(
        crawler_service,
        "fetch_job_detail",
        lambda job_url: (
            detail_calls.append(job_url)
            or ({"jobDetail": {}}, 1)
        ),
    )
    monkeypatch.setattr(
        crawler_service,
        "transform_job",
        lambda job_data, detail_data: {
            "description": "JD",
        },
    )

    _, _, stats = crawler_service.crawl_jobs(
        "dedup-run"
    )

    assert len(detail_calls) == 1
    assert stats["search_unique_count"] == 1
    assert stats["selected_count"] == 1


def test_candidate_budget_does_not_exceed_limit(
    monkeypatch,
):
    configure_search_test(
        monkeypatch,
        quotas={"Python": 200},
        max_details=120,
    )
    search_results = [
        search_job(index)
        for index in range(200)
    ]

    monkeypatch.setattr(
        crawler_service,
        "fetch_search_page",
        lambda keyword, page: search_results,
    )
    monkeypatch.setattr(
        crawler_service,
        "find_existing_jobs",
        lambda source_job_ids: {},
    )

    candidates, stats = (
        crawler_service.collect_detail_candidates(
            "budget-run"
        )
    )

    assert len(candidates) == 120
    assert stats["new_candidate_count"] == 120


def test_candidate_lookup_is_batched_per_search_page(
    monkeypatch,
):
    configure_search_test(
        monkeypatch,
        quotas={"Python": 10},
    )
    lookup_calls = []
    jobs = [
        search_job("one"),
        search_job("two"),
        search_job("three"),
    ]

    monkeypatch.setattr(
        crawler_service,
        "fetch_search_page",
        lambda keyword, page: jobs,
    )

    def fake_lookup(source_job_ids):
        lookup_calls.append(source_job_ids)
        return {}

    monkeypatch.setattr(
        crawler_service,
        "find_existing_jobs",
        fake_lookup,
    )

    crawler_service.collect_detail_candidates(
        "batch-run"
    )

    assert lookup_calls == [
        ["one", "two", "three"]
    ]


def test_detail_failure_does_not_update_checked_time(
    monkeypatch,
):
    configure_search_test(
        monkeypatch,
        quotas={"Python": 1},
    )
    checked_at = (
        datetime.now(timezone.utc)
        - timedelta(hours=72)
    )
    existing = SimpleNamespace(
        last_detail_checked_at=checked_at
    )

    monkeypatch.setattr(
        crawler_service,
        "fetch_search_page",
        lambda keyword, page: [
            search_job("failed")
        ],
    )
    monkeypatch.setattr(
        crawler_service,
        "find_existing_jobs",
        lambda source_job_ids: {
            "failed": existing
        },
    )
    monkeypatch.setattr(
        crawler_service,
        "fetch_job_detail",
        lambda job_url: (_ for _ in ()).throw(
            RuntimeError("detail failed")
        ),
    )
    monkeypatch.setattr(
        crawler_service,
        "save_crawler_failure",
        lambda **kwargs: None,
    )

    clean_jobs, raw_jobs, _ = (
        crawler_service.crawl_jobs(
            "failure-run"
        )
    )

    assert clean_jobs == []
    assert raw_jobs == []
    assert (
        existing.last_detail_checked_at
        == checked_at
    )


def test_403_stops_remaining_detail_requests(
    monkeypatch,
):
    configure_search_test(
        monkeypatch,
        quotas={"Python": 2},
        max_details=2,
    )
    detail_calls = []
    failures = []

    monkeypatch.setattr(
        crawler_service,
        "fetch_search_page",
        lambda keyword, page: [
            search_job("forbidden"),
            search_job("not-attempted"),
        ],
    )
    monkeypatch.setattr(
        crawler_service,
        "find_existing_jobs",
        lambda source_job_ids: {},
    )

    def forbidden_detail(job_url):
        detail_calls.append(job_url)
        raise DetailAccessForbiddenError(
            "Detail API 回傳 403",
            attempt_count=1,
            http_status=403,
        )

    monkeypatch.setattr(
        crawler_service,
        "fetch_job_detail",
        forbidden_detail,
    )
    monkeypatch.setattr(
        crawler_service,
        "save_crawler_failure",
        lambda **kwargs: failures.append(
            kwargs
        ),
    )

    _, _, stats = crawler_service.crawl_jobs(
        "forbidden-run"
    )

    assert len(detail_calls) == 1
    assert stats["stopped_by_forbidden"] is True
    assert failures[0]["http_status"] == 403
