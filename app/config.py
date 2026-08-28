# =========================
# 104 API 設定
# =========================

SEARCH_API_URL = "https://www.104.com.tw/jobs/search/api/jobs"
DETAIL_API_URL = "https://www.104.com.tw/job/ajax/content"


# =========================
# 搜尋設定
# =========================

SEARCH_QUOTAS = {
    "AI 應用工程師": 0,
    "AI 工程師": 0,
    "生成式 AI 工程師": 0,
    "Python 工程師": 0,
    "資料工程師": 50,
    "後端工程師": 0,
    "軟體工程師": 0,
}

MAX_JOBS = 50

START_PAGE = 1

END_PAGE = 3

PAGE_SIZE = 20


# =========================
# Request 設定
# =========================

REQUEST_TIMEOUT = 30

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/148.0.0.0 Safari/537.36"
)