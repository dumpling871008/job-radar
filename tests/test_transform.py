from app.crawler.transform import generate_content_hash, transform_job


def test_same_job_should_have_same_hash():

    job1 = {
        "job_name": "資料工程師",
        "company_name": "ABC 公司",
        "location": "台北市",
        "description": "使用 Python 建立 ETL Pipeline",
        "experience": "1年以上",
        "education": "大學以上",
    }

    job2 = {
        "job_name": "資料工程師",
        "company_name": "ABC 公司",
        "location": "台北市",
        "description": "使用 Python 建立 ETL Pipeline",
        "experience": "1年以上",
        "education": "大學以上",
    }

    hash1 = generate_content_hash(job1)
    hash2 = generate_content_hash(job2)

    assert hash1 == hash2


def test_changed_jd_should_have_different_hash():

    old_job = {
        "job_name": "資料工程師",
        "company_name": "ABC 公司",
        "location": "台北市",
        "description": "需要 Python",
        "experience": "1年以上",
        "education": "大學以上",
    }

    new_job = {
        "job_name": "資料工程師",
        "company_name": "ABC 公司",
        "location": "台北市",
        "description": "需要 Python、Airflow、PostgreSQL",
        "experience": "1年以上",
        "education": "大學以上",
    }

    old_hash = generate_content_hash(old_job)
    new_hash = generate_content_hash(new_job)

    assert old_hash != new_hash


def test_changed_salary_should_have_different_hash():
    base_job = {
        "job_name": "後端工程師",
        "company_name": "ABC 公司",
        "location": "台北市",
        "description": "需要 Python",
        "experience": "1年以上",
        "education": "大學以上",
        "salary_text": "月薪45,000元以上",
    }
    changed_salary = {
        **base_job,
        "salary_text": "月薪55,000元以上",
    }

    assert generate_content_hash(
        base_job
    ) != generate_content_hash(
        changed_salary
    )

def test_transform_job():

    search_data = {
        "jobName": "資料工程師",
        "custName": "ABC 公司",
        "jobAddrNoDesc": "台北市信義區",
        "jobNo": "12345678",
        "description": "這是搜尋摘要",
        "link": {
            "job": "https://www.104.com.tw/job/abc123"
        },
    }

    detail_data = {
        "header": {
            "appearDate": "2026/08/28",
        },

        "jobDetail": {
            "jobDescription": (
                "負責 Python、FastAPI 與 PostgreSQL 開發"
            ),
            "salary": "月薪45,000~60,000元",
        },

        "condition": {
            "workExp": "1年以上",
            "edu": "大學以上",
        },
    }

    job = transform_job(
        search_data,
        detail_data,
    )

    assert job["job_name"] == "資料工程師"

    assert job["company_name"] == "ABC 公司"

    assert job["location"] == "台北市信義區"

    assert job["job_no"] == "12345678"

    assert (
        job["url"]
        == "https://www.104.com.tw/job/abc123"
    )

    assert (
        job["description_summary"]
        == "這是搜尋摘要"
    )

    assert (
        job["description"]
        == "負責 Python、FastAPI 與 PostgreSQL 開發"
    )

    assert job["experience"] == "1年以上"

    assert job["education"] == "大學以上"

    assert job["appear_date"] == "2026/08/28"

    assert job["job_category"] == "AI_DATA"

    assert job["salary_text"] == (
        "月薪45,000~60,000元"
    )

    assert job["tech_stack"] == [
        "Python",
        "FastAPI",
        "PostgreSQL",
    ]
    assert len(job["content_hash"]) == 64
