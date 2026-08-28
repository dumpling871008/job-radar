import hashlib
import json


def generate_content_hash(job):
    """
    根據重要職缺內容產生 SHA-256 hash。
    如果 JD 或重要欄位改變，hash 就會改變。
    """

    hash_data = {
        "job_name": job.get("job_name", ""),
        "company_name": job.get("company_name", ""),
        "location": job.get("location", ""),
        "description": job.get("description", ""),
        "experience": job.get("experience", ""),
        "education": job.get("education", ""),
    }

    content = json.dumps(
        hash_data,
        ensure_ascii=False,
        sort_keys=True,
    )

    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()


def transform_job(
    job_data,
    detail_data,
):
    job_detail = detail_data.get(
        "jobDetail",
        {},
    )

    condition = detail_data.get(
        "condition",
        {},
    )

    header = detail_data.get(
        "header",
        {},
    )

    job_url = (
        job_data
        .get("link", {})
        .get("job", "")
    )

    job = {
        "job_name": job_data.get(
            "jobName",
            "",
        ),

        "company_name": job_data.get(
            "custName",
            "",
        ),

        "location": job_data.get(
            "jobAddrNoDesc",
            "",
        ),

        "job_no": str(
            job_data.get(
                "jobNo",
                "",
            )
        ),

        "url": job_url,

        "description_summary": job_data.get(
            "description",
            "",
        ),

        "description": job_detail.get(
            "jobDescription",
            "",
        ),

        "experience": condition.get(
            "workExp",
            "",
        ),

        "education": condition.get(
            "edu",
            "",
        ),

        "appear_date": header.get(
            "appearDate",
            "",
        ),
    }

    # 最後再算 hash
    job["content_hash"] = (
        generate_content_hash(job)
    )

    return job