import math
from datetime import datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import (
    FastAPI,
    Form,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sqlalchemy import func, or_, select
from sqlalchemy.orm import contains_eager

from app.db.database import SessionLocal
from app.models.job import Job
from app.models.job_application import (
    JobApplication,
)
from app.repositories.crawler_failure_repository import (
    CrawlerFailureRepository,
)
from app.repositories.crawler_run_repository import (
    CrawlerRunRepository,
)
from app.services.job_application_service import (
    JOB_APPLICATION_STATUSES,
    JobApplicationService,
)


app = FastAPI(
    title="Job Radar"
)


# =========================
# Static
# =========================

app.mount(
    "/static",
    StaticFiles(
        directory="app/static"
    ),
    name="static",
)


# =========================
# Templates
# =========================

templates = Jinja2Templates(
    directory="app/templates"
)


PAGE_SIZE = 20
TAIPEI_TIMEZONE = ZoneInfo("Asia/Taipei")
JOB_APPLICATION_STATUS_LABELS = {
    "all": "全部",
    "UNREAD": "未處理",
    "SAVED": "收藏",
    "APPLIED": "已投遞",
    "INTERVIEW": "面試",
    "REJECTED": "不考慮",
    "CLOSED": "已結束",
}


def taipei_today_range():
    today = datetime.now(
        TAIPEI_TIMEZONE
    ).date()

    start = datetime.combine(
        today,
        time.min,
        tzinfo=TAIPEI_TIMEZONE,
    )

    return start, start + timedelta(days=1)


def monitoring_pagination(
    request,
    route_name,
    requested_page,
    total_items,
):
    total_pages = max(
        math.ceil(
            total_items / PAGE_SIZE
        ),
        1,
    )

    page = min(
        requested_page,
        total_pages,
    )

    route_url = request.url_for(
        route_name
    )

    previous_url = None
    next_url = None

    if page > 1:
        previous_url = (
            route_url.include_query_params(
                page=page - 1
            )
        )

    if page < total_pages:
        next_url = (
            route_url.include_query_params(
                page=page + 1
            )
        )

    return {
        "page": page,
        "total_pages": total_pages,
        "offset": (
            (page - 1)
            * PAGE_SIZE
        ),
        "previous_url": previous_url,
        "next_url": next_url,
    }


def dashboard_url(
    base_url,
    *,
    view,
    q,
    location,
    sort,
    application_status,
    page,
):
    parameters = {
        "view": view,
        "q": q,
        "location": location,
        "page": page,
    }

    if sort:
        parameters["sort"] = sort

    if application_status != "all":
        parameters["status"] = (
            application_status
        )

    return base_url.include_query_params(
        **parameters
    )


@app.get("/")
def home(
    request: Request,

    view: Literal[
        "all",
        "today",
        "updated",
    ] = Query(
        default="all",
    ),

    page: int = Query(
        default=1,
        ge=1,
    ),

    q: str = Query(
        default="",
    ),

    location: str = Query(
        default="",
    ),

    sort: str = Query(
        default="",
    ),

    application_status: Literal[
        "all",
        "UNREAD",
        "SAVED",
        "APPLIED",
        "INTERVIEW",
        "REJECTED",
        "CLOSED",
    ] = Query(
        default="all",
        alias="status",
    ),
):

    q = q.strip()
    location = location.strip()
    sort = sort.strip()


    with SessionLocal() as session:

        # =========================
        # 1. 取得目前資料庫有哪些城市
        # =========================

        city_expr = func.substr(
            Job.location,
            1,
            3,
        )

        city_statement = (
            select(city_expr)
            .where(
                Job.location.is_not(None),
                Job.location != "",
            )
            .distinct()
            .order_by(city_expr)
        )
        locations = session.scalars(
            city_statement
        ).all()


        # =========================
        # 2. 建立搜尋條件
        # =========================

        filters = []


        # 今日新增：以台北時區的日期邊界判斷
        if view == "today":

            today_start, tomorrow_start = (
                taipei_today_range()
            )

            filters.extend(
                [
                    Job.first_seen_at
                    >= today_start,

                    Job.first_seen_at
                    < tomorrow_start,
                ]
            )

        # 今日 JD 更新：只看重要內容變更時間
        elif view == "updated":

            today_start, tomorrow_start = (
                taipei_today_range()
            )

            filters.extend(
                [
                    Job.content_updated_at
                    >= today_start,

                    Job.content_updated_at
                    < tomorrow_start,
                ]
            )


        # 關鍵字搜尋
        if q:

            keyword = f"%{q}%"

            filters.append(
                or_(
                    Job.title.ilike(
                        keyword
                    ),

                    Job.company_name.ilike(
                        keyword
                    ),

                    Job.description.ilike(
                        keyword
                    ),
                )
            )


        # 地區搜尋
        if location:

            filters.append(
                Job.location.ilike(
                    f"{location}%"
                )
            )


        # 沒有 application record 的職缺
        # 也視為尚未處理。
        if application_status == "UNREAD":

            filters.append(
                or_(
                    JobApplication.id.is_(
                        None
                    ),
                    JobApplication.status
                    == "UNREAD",
                )
            )

        elif application_status != "all":

            filters.append(
                JobApplication.status
                == application_status
            )


        # =========================
        # 3. 計算符合條件的總筆數
        # =========================

        count_statement = (
            select(func.count(Job.id))
            .outerjoin(
                JobApplication,
                JobApplication.job_id
                == Job.id,
            )
        )


        if filters:

            count_statement = (
                count_statement.where(
                    *filters
                )
            )


        total_jobs = session.scalar(
            count_statement
        ) or 0


        # =========================
        # 4. 計算總頁數
        # =========================

        total_pages = math.ceil(
            total_jobs / PAGE_SIZE
        )

        total_pages = max(
            total_pages,
            1,
        )


        if page > total_pages:

            page = total_pages


        # =========================
        # 5. Offset
        # =========================

        offset = (
            (page - 1)
            * PAGE_SIZE
        )


        # =========================
        # 6. 查詢職缺
        # =========================

        statement = (
            select(Job)
            .outerjoin(
                JobApplication,
                JobApplication.job_id
                == Job.id,
            )
            .options(
                contains_eager(
                    Job.application
                )
            )
        )


        if filters:

            statement = (
                statement.where(
                    *filters
                )
            )


        statement = (
            statement
            .order_by(
                Job.first_seen_at.desc()
            )
            .offset(offset)
            .limit(PAGE_SIZE)
        )


        jobs = session.scalars(
            statement
        ).all()


    # =========================
    # 7. Dashboard URL
    # =========================

    home_url = request.url_for(
        "home"
    )

    all_view_url = dashboard_url(
        home_url,
        view="all",
        q=q,
        location=location,
        sort=sort,
        application_status=(
            application_status
        ),
        page=1,
    )

    today_view_url = dashboard_url(
        home_url,
        view="today",
        q=q,
        location=location,
        sort=sort,
        application_status=(
            application_status
        ),
        page=1,
    )

    updated_view_url = dashboard_url(
        home_url,
        view="updated",
        q=q,
        location=location,
        sort=sort,
        application_status=(
            application_status
        ),
        page=1,
    )

    clear_url = dashboard_url(
        home_url,
        view=view,
        q="",
        location="",
        sort=sort,
        application_status=(
            application_status
        ),
        page=1,
    )

    status_filter_urls = {
        status: dashboard_url(
            home_url,
            view=view,
            q=q,
            location=location,
            sort=sort,
            application_status=status,
            page=1,
        )
        for status in (
            "all",
            *JOB_APPLICATION_STATUSES,
        )
    }

    previous_url = None
    next_url = None


    if page > 1:

        previous_url = dashboard_url(
            home_url,
            view=view,
            q=q,
            location=location,
            sort=sort,
            application_status=(
                application_status
            ),
            page=page - 1,
        )


    if page < total_pages:

        next_url = dashboard_url(
            home_url,
            view=view,
            q=q,
            location=location,
            sort=sort,
            application_status=(
                application_status
            ),
            page=page + 1,
        )


    return templates.TemplateResponse(
        request=request,
        name="jobs.html",
        context={
            "active_page": "jobs",
            "jobs": jobs,
            "view": view,
            "page": page,
            "total_pages": total_pages,
            "total_jobs": total_jobs,

            "q": q,
            "location": location,
            "locations": locations,
            "sort": sort,
            "application_status": (
                application_status
            ),
            "application_statuses": (
                JOB_APPLICATION_STATUSES
            ),
            "application_status_labels": (
                JOB_APPLICATION_STATUS_LABELS
            ),
            "status_filter_urls": (
                status_filter_urls
            ),

            "all_view_url": all_view_url,
            "today_view_url": today_view_url,
            "updated_view_url": updated_view_url,
            "clear_url": clear_url,
            "previous_url": previous_url,
            "next_url": next_url,
        },
    )


def job_dashboard_redirect(
    request,
    *,
    view,
    q,
    location,
    sort,
    application_status,
    page,
):
    return RedirectResponse(
        url=str(
            dashboard_url(
                request.url_for("home"),
                view=view,
                q=q,
                location=location,
                sort=sort,
                application_status=(
                    application_status
                ),
                page=page,
            )
        ),
        status_code=303,
    )


@app.post("/jobs/{job_id}/status")
def update_job_status(
    job_id: int,
    request: Request,
    status: str = Form(...),
    view: str = Form("all"),
    q: str = Form(""),
    location: str = Form(""),
    sort: str = Form(""),
    page: int = Form(1),
    filter_status: str = Form("all"),
):
    with SessionLocal() as session:
        service = JobApplicationService(
            session
        )

        try:
            service.update_status(
                job_id,
                status,
            )
            session.commit()
        except ValueError as error:
            session.rollback()
            raise HTTPException(
                status_code=422,
                detail=str(error),
            ) from error
        except LookupError as error:
            session.rollback()
            raise HTTPException(
                status_code=404,
                detail=str(error),
            ) from error

    return job_dashboard_redirect(
        request,
        view=view,
        q=q,
        location=location,
        sort=sort,
        application_status=(
            filter_status
        ),
        page=max(page, 1),
    )


@app.post("/jobs/{job_id}/note")
def update_job_note(
    job_id: int,
    request: Request,
    note: str = Form(""),
    view: str = Form("all"),
    q: str = Form(""),
    location: str = Form(""),
    sort: str = Form(""),
    page: int = Form(1),
    filter_status: str = Form("all"),
):
    with SessionLocal() as session:
        service = JobApplicationService(
            session
        )

        try:
            service.update_note(
                job_id,
                note,
            )
            session.commit()
        except LookupError as error:
            session.rollback()
            raise HTTPException(
                status_code=404,
                detail=str(error),
            ) from error

    return job_dashboard_redirect(
        request,
        view=view,
        q=q,
        location=location,
        sort=sort,
        application_status=(
            filter_status
        ),
        page=max(page, 1),
    )


@app.get("/runs")
def runs(
    request: Request,
    page: int = Query(
        default=1,
        ge=1,
    ),
):
    with SessionLocal() as session:
        repository = (
            CrawlerRunRepository(
                session
            )
        )

        total_runs = (
            repository.count_runs()
        )

        pagination = (
            monitoring_pagination(
                request=request,
                route_name="runs",
                requested_page=page,
                total_items=total_runs,
            )
        )

        crawler_runs = (
            repository.list_runs(
                offset=(
                    pagination["offset"]
                ),
                limit=PAGE_SIZE,
            )
        )

    return templates.TemplateResponse(
        request=request,
        name="runs.html",
        context={
            "active_page": "runs",
            "crawler_runs": crawler_runs,
            "total_runs": total_runs,
            **pagination,
        },
    )


@app.get("/failures")
def failures(
    request: Request,
    page: int = Query(
        default=1,
        ge=1,
    ),
):
    with SessionLocal() as session:
        repository = (
            CrawlerFailureRepository(
                session
            )
        )

        total_failures = (
            repository.count_failures()
        )

        pagination = (
            monitoring_pagination(
                request=request,
                route_name="failures",
                requested_page=page,
                total_items=total_failures,
            )
        )

        crawler_failures = (
            repository.list_failures(
                offset=(
                    pagination["offset"]
                ),
                limit=PAGE_SIZE,
            )
        )

    return templates.TemplateResponse(
        request=request,
        name="failures.html",
        context={
            "active_page": "failures",
            "crawler_failures": (
                crawler_failures
            ),
            "total_failures": (
                total_failures
            ),
            **pagination,
        },
    )
