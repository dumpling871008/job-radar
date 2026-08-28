import app.services.crawler_service as crawler_service


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
        "MAX_JOBS",
        2,
    )

    monkeypatch.setattr(
        crawler_service,
        "START_PAGE",
        1,
    )

    monkeypatch.setattr(
        crawler_service,
        "END_PAGE",
        1,
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