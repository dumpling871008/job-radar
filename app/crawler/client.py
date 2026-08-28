import requests
import time

from app.config import (
    SEARCH_API_URL,
    DETAIL_API_URL,
    PAGE_SIZE,
    REQUEST_TIMEOUT,
    USER_AGENT,
)


def fetch_search_page(keyword, page):
    """
    抓取 104 某個關鍵字的某一頁搜尋結果。
    """

    params = {
        "jobsource": "index_s",
        "keyword": keyword,
        "mode": "s",
        "order": 15,
        "page": page,
        "pagesize": PAGE_SIZE,
    }

    headers = {
        "User-Agent": USER_AGENT,
        "Referer": "https://www.104.com.tw/jobs/search/?jobsource=index_s&keyword=%E8%B3%87%E6%96%99%E5%B7%A5%E7%A8%8B%E5%B8%AB&mode=s&page=1",
    }

    response = requests.get(
        SEARCH_API_URL,
        params=params,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    content_type = response.headers.get(
        "Content-Type",
        "",
    )

    if "application/json" not in content_type:
        raise RuntimeError(
            "Search API 回傳的不是 JSON"
        )

    payload = response.json()

    jobs = payload.get("data", [])

    return jobs


def fetch_job_detail(
    job_url,
    max_attempts=3,
):
    job_id = (
        job_url
        .split("/job/")[-1]
        .split("?")[0]
    )

    detail_url = (
        f"{DETAIL_API_URL}/{job_id}"
    )

    headers = {
        "User-Agent": USER_AGENT,
        "Referer": job_url,
    }

    last_error = None

    for attempt in range(
        1,
        max_attempts + 1,
    ):

        try:

            response = requests.get(
                detail_url,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )

            content_type = (
                response.headers.get(
                    "Content-Type",
                    "",
                )
            )

            # 403 不一直重試
            if response.status_code == 403:
                raise RuntimeError(
                    "Detail API 回傳 403"
                )

            # 429 或 5xx 可以稍後再試
            if (
                response.status_code == 429
                or response.status_code >= 500
            ):

                raise RuntimeError(
                    f"Detail API HTTP "
                    f"{response.status_code}"
                )

            if response.status_code != 200:
                raise RuntimeError(
                    f"Detail API HTTP "
                    f"{response.status_code}"
                )

            if (
                "application/json"
                not in content_type
            ):
                raise RuntimeError(
                    "Detail API 回傳的不是 JSON"
                )

            payload = response.json()

            return (
                payload.get(
                    "data",
                    {},
                ),
                attempt,
            )

        except (
            requests.RequestException,
            RuntimeError,
        ) as error:

            last_error = error

            # 403 不繼續 retry
            if (
                "403"
                in str(error)
            ):
                break

            if attempt < max_attempts:

                wait_seconds = (
                    2 ** (attempt - 1)
                )

                print(
                    f"第 {attempt} 次失敗，"
                    f"{wait_seconds} 秒後重試..."
                )

                time.sleep(
                    wait_seconds
                )

    raise RuntimeError(
        f"Detail API 最終失敗："
        f"{last_error}"
    )
