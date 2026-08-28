import requests
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from app.config import (
    SEARCH_API_URL,
    DETAIL_API_URL,
    PAGE_SIZE,
    REQUEST_TIMEOUT,
    USER_AGENT,
)


class DetailFetchError(RuntimeError):

    def __init__(
        self,
        message,
        *,
        attempt_count,
        http_status=None,
        retry_after=None,
    ):
        super().__init__(message)
        self.attempt_count = attempt_count
        self.http_status = http_status
        self.retry_after = retry_after


class DetailAccessForbiddenError(
    DetailFetchError
):
    pass


def parse_retry_after(value):
    if not value:
        return None

    try:
        return max(float(value), 0)
    except (TypeError, ValueError):
        pass

    try:
        retry_at = parsedate_to_datetime(
            value
        )

        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(
                tzinfo=timezone.utc
            )

        return max(
            (
                retry_at
                - datetime.now(timezone.utc)
            ).total_seconds(),
            0,
        )
    except (TypeError, ValueError):
        return None


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
    last_http_status = None
    attempts_made = 0

    for attempt in range(
        1,
        max_attempts + 1,
    ):

        attempts_made = attempt

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
                raise DetailAccessForbiddenError(
                    "Detail API 回傳 403",
                    attempt_count=attempt,
                    http_status=403,
                )

            # 429 優先尊重 Retry-After。
            if response.status_code == 429:
                raise DetailFetchError(
                    "Detail API HTTP 429",
                    attempt_count=attempt,
                    http_status=429,
                    retry_after=parse_retry_after(
                        response.headers.get(
                            "Retry-After"
                        )
                    ),
                )

            # 5xx 稍後使用 exponential backoff。
            if response.status_code >= 500:

                raise DetailFetchError(
                    f"Detail API HTTP "
                    f"{response.status_code}",
                    attempt_count=attempt,
                    http_status=(
                        response.status_code
                    ),
                )

            if response.status_code != 200:
                raise DetailFetchError(
                    f"Detail API HTTP "
                    f"{response.status_code}",
                    attempt_count=attempt,
                    http_status=(
                        response.status_code
                    ),
                )

            if (
                "application/json"
                not in content_type
            ):
                raise DetailFetchError(
                    "Detail API 回傳的不是 JSON",
                    attempt_count=attempt,
                    http_status=(
                        response.status_code
                    ),
                )

            payload = response.json()

            return (
                payload.get(
                    "data",
                    {},
                ),
                attempt,
            )

        except DetailAccessForbiddenError:
            raise

        except (
            requests.RequestException,
            DetailFetchError,
        ) as error:

            last_error = error
            last_http_status = getattr(
                error,
                "http_status",
                None,
            )

            if attempt < max_attempts:

                wait_seconds = getattr(
                    error,
                    "retry_after",
                    None,
                )

                if wait_seconds is None:
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

    raise DetailFetchError(
        f"Detail API 最終失敗："
        f"{last_error}",
        attempt_count=attempts_made,
        http_status=last_http_status,
    )
