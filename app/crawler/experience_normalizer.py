import re


EXPERIENCE_LEVEL_LABELS = {
    "all": "全部年資",
    "NO_REQUIREMENT": "經歷不拘",
    "NO_EXPERIENCE": "無經驗",
    "UNDER_ONE": "1 年以下",
    "ONE_TO_THREE": "1–3 年",
    "THREE_TO_FIVE": "3–5 年",
    "FIVE_PLUS": "5 年以上",
    "UNKNOWN": "其他年資",
}


def normalize_experience(value):
    text = "".join(
        (value or "").split()
    )

    if not text:
        return "UNKNOWN"

    if any(
        marker in text
        for marker in (
            "不拘",
            "經歷不限",
            "經驗不限",
        )
    ):
        return "NO_REQUIREMENT"

    if "無經驗" in text:
        return "NO_EXPERIENCE"

    if re.search(
        r"(?:1年以下|未滿1年|1年內)",
        text,
    ):
        return "UNDER_ONE"

    match = re.search(
        r"(\d+)年以上",
        text,
    )
    if not match:
        return "UNKNOWN"

    years = int(match.group(1))

    if years < 1:
        return "UNDER_ONE"
    if years < 3:
        return "ONE_TO_THREE"
    if years < 5:
        return "THREE_TO_FIVE"
    return "FIVE_PLUS"
