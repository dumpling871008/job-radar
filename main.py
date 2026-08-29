from app.services.pipeline_service import (
    run_pipeline,
)


def main():
    print("=" * 50)
    print("Job Radar")
    print("準備啟動 crawler...")

    result = run_pipeline(
        trigger_type="MANUAL"
    )

    print("=" * 50)

    if not result["started"]:
        print(
            "目前已經有另一個 crawler "
            "正在執行，本次執行取消。"
        )
        return 0

    print(f"Run ID：{result['run_id']}")
    print(f"Status：{result['status']}")

    if result.get("error_message"):
        print(
            "錯誤："
            f"{result['error_message']}"
        )

    if result["status"] == "FAILED":
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
