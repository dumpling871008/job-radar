import re
from datetime import timezone
from zoneinfo import ZoneInfo


TAIPEI_TIMEZONE = ZoneInfo(
    "Asia/Taipei"
)
MAX_PREVIEW_LENGTH = 220


def format_datetime_taipei(value):
    if value is None:
        return ""

    if value.tzinfo is None:
        value = value.replace(
            tzinfo=timezone.utc
        )

    return value.astimezone(
        TAIPEI_TIMEZONE
    ).strftime("%Y/%m/%d %H:%M")


def normalize_preview(
    text,
    max_length=MAX_PREVIEW_LENGTH,
):
    normalized = re.sub(
        r"\s+",
        " ",
        text or "",
    ).strip()

    if len(normalized) <= max_length:
        return normalized

    return (
        normalized[:max_length].rstrip()
        + "…"
    )
