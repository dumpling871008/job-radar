def extract_salary_text(detail_data):
    """只接受 104 Detail API 明確提供的薪資顯示文字。"""

    value = (
        (detail_data or {})
        .get("jobDetail", {})
        .get("salary")
    )

    if not isinstance(value, str):
        return None

    value = value.strip()
    return value or None
