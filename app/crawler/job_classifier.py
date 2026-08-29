import re


JOB_CATEGORIES = (
    "SOFTWARE",
    "AI_DATA",
    "DEVOPS_CLOUD",
    "OTHER_ENGINEERING",
    "NON_TECH",
    "UNKNOWN",
)


NON_TECH_TITLE_PATTERNS = (
    r"影音.*設計",
    r"數位媒體.*設計",
    r"行銷",
    r"業務",
    r"行政",
    r"風控",
    r"財務",
    r"會計",
    r"營運\s*p\.?m\.?(?:\b|$)",
    r"產品行銷",
    r"工地.*監工",
    r"現場.*監工",
    r"人員調派",
)

OTHER_ENGINEERING_TITLE_PATTERNS = (
    r"製程工程師",
    r"機械工程師",
    r"設備工程師",
    r"電機工程師",
    r"材料工程師",
    r"土木工程師",
    r"工務工程師",
    r"鑄造",
    r"製造工程",
)

AI_DATA_TITLE_PATTERNS = (
    r"\bai\s*(?:應用)?工程師\b",
    r"\bai\s+engineer\b",
    r"\bmachine\s+learning\s+engineer\b",
    r"\bml\s+engineer\b",
    r"資料工程師",
    r"\bdata\s+engineer\b",
    r"\bdata\s+scientist\b",
    r"資料科學",
    r"\bllm\b",
    r"生成式\s*ai",
    r"\bmlops\b",
)

DEVOPS_TITLE_PATTERNS = (
    r"\bdevops\b",
    r"\bsre\b",
    r"\bcloud\s+engineer\b",
    r"雲端工程師",
    r"\bplatform\s+engineer\b",
    r"\binfrastructure\s+engineer\b",
    r"\bkubernetes\b",
)

SOFTWARE_TITLE_PATTERNS = (
    r"python\s*工程師",
    r"後端工程師",
    r"\bbackend\s+(?:engineer|developer)\b",
    r"前端工程師",
    r"\bfrontend\s+(?:engineer|developer)\b",
    r"\bfull[ -]?stack\s+(?:engineer|developer)\b",
    r"全端工程師",
    r"\bsoftware\s+engineer\b",
    r"軟體工程師",
    r"\bweb\s+(?:engineer|developer)\b",
)

TECHNICAL_TITLE_PATTERN = re.compile(
    r"工程師|engineer|developer|開發",
    re.IGNORECASE,
)

SYSTEM_TITLE_PATTERN = re.compile(
    r"系統工程師",
    re.IGNORECASE,
)

SYSTEM_DESCRIPTION_PATTERNS = (
    r"資訊系統",
    r"軟體",
    r"程式",
    r"\bapi\b",
    r"資料庫",
    r"\bdatabase\b",
    r"伺服器",
    r"\bserver\b",
    r"\blinux\b",
    r"雲端",
    r"\bcloud\b",
)

DESCRIPTION_CATEGORY_PATTERNS = {
    "AI_DATA": (
        r"machine learning",
        r"機器學習",
        r"資料工程",
        r"data pipeline",
        r"data science",
        r"\bllm\b",
        r"生成式\s*ai",
        r"\bmlops\b",
    ),
    "DEVOPS_CLOUD": (
        r"\bdevops\b",
        r"\bsre\b",
        r"\bkubernetes\b",
        r"雲端基礎設施",
        r"cloud infrastructure",
    ),
    "SOFTWARE": (
        r"後端開發",
        r"前端開發",
        r"軟體開發",
        r"web development",
        r"\bapi\b",
    ),
}


def _matches(text, patterns):
    return any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in patterns
    )


def classify_job(title, description=""):
    """以可讀、保守的規則分類 clean job，不修改原始資料。"""

    normalized_title = " ".join(
        (title or "").split()
    )
    normalized_description = " ".join(
        (description or "").split()
    )

    # 排除規則必須優先，避免 AI／工程師等寬鬆字樣誤判。
    if _matches(
        normalized_title,
        NON_TECH_TITLE_PATTERNS,
    ):
        return "NON_TECH"

    if _matches(
        normalized_title,
        OTHER_ENGINEERING_TITLE_PATTERNS,
    ):
        return "OTHER_ENGINEERING"

    if _matches(
        normalized_title,
        AI_DATA_TITLE_PATTERNS,
    ):
        return "AI_DATA"

    if _matches(
        normalized_title,
        DEVOPS_TITLE_PATTERNS,
    ):
        return "DEVOPS_CLOUD"

    if _matches(
        normalized_title,
        SOFTWARE_TITLE_PATTERNS,
    ):
        return "SOFTWARE"

    if SYSTEM_TITLE_PATTERN.search(
        normalized_title
    ) and _matches(
        normalized_description,
        SYSTEM_DESCRIPTION_PATTERNS,
    ):
        return "SOFTWARE"

    # Description 只協助明確帶技術職稱的工作，不因單一 AI／Python
    # 等字樣把設計、行銷或營運職缺判成技術職。
    if TECHNICAL_TITLE_PATTERN.search(
        normalized_title
    ):
        for category, patterns in (
            DESCRIPTION_CATEGORY_PATTERNS.items()
        ):
            if _matches(
                normalized_description,
                patterns,
            ):
                return category

    return "UNKNOWN"
