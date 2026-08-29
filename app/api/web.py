import math
from datetime import datetime, time, timedelta
from typing import Literal

from fastapi import (
    BackgroundTasks,
    FastAPI,
    Form,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sqlalchemy import false, func, or_, select
from sqlalchemy.orm import contains_eager

from app.db.database import SessionLocal
from app.api.presentation import (
    TAIPEI_TIMEZONE,
    format_datetime_taipei,
    normalize_preview,
)
from app.crawler.job_classifier import (
    JOB_CATEGORIES,
)
from app.crawler.experience_normalizer import (
    EXPERIENCE_LEVEL_LABELS,
    normalize_experience,
)
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
from app.services.pipeline_service import (
    reserve_pipeline,
    run_pipeline,
)
from app.services.crawler_settings_service import (
    CrawlerSettingsService,
)


app = FastAPI(
    title="Job Radar"
)


@app.get("/health")
def health():
    return {"status": "ok"}


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
templates.env.filters[
    "datetime_taipei"
] = format_datetime_taipei
templates.env.filters[
    "preview"
] = normalize_preview


PAGE_SIZE = 20
RELEVANT_JOB_CATEGORIES = (
    "SOFTWARE",
    "AI_DATA",
    "DEVOPS_CLOUD",
)
JOB_CATEGORY_LABELS = {
    "relevant": "相關職缺",
    "all": "全部領域",
    "SOFTWARE": "軟體",
    "AI_DATA": "AI / Data",
    "DEVOPS_CLOUD": "DevOps / Cloud",
    "OTHER_ENGINEERING": "其他工程",
    "NON_TECH": "非技術",
    "UNKNOWN": "未分類",
}
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
    category,
    tech,
    experience_level,
    page,
):
    parameters = {
        "view": view,
        "q": q,
        "location": location,
        "category": category,
        "page": page,
    }

    if sort:
        parameters["sort"] = sort

    if tech:
        parameters["tech"] = tech

    if experience_level != "all":
        parameters["experience"] = (
            experience_level
        )

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

    category: Literal[
        "relevant",
        "all",
        "SOFTWARE",
        "AI_DATA",
        "DEVOPS_CLOUD",
        "OTHER_ENGINEERING",
        "NON_TECH",
        "UNKNOWN",
    ] = Query(
        default="relevant",
    ),

    tech: str = Query(
        default="",
    ),

    experience_level: Literal[
        "all",
        "NO_REQUIREMENT",
        "NO_EXPERIENCE",
        "UNDER_ONE",
        "ONE_TO_THREE",
        "THREE_TO_FIVE",
        "FIVE_PLUS",
        "UNKNOWN",
    ] = Query(
        default="all",
        alias="experience",
    ),

    message: Literal[
        "crawler_started",
        "crawler_already_running",
    ] | None = Query(
        default=None,
    ),
):

    q = q.strip()
    location = location.strip()
    sort = sort.strip()
    tech = tech.strip()


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
        locations = sorted(
            {
                city
                for city in session.scalars(
                    city_statement
                ).all()
                if city
            }
        )

        tech_options = sorted(
            {
                item
                for stack in session.scalars(
                    select(Job.tech_stack)
                ).all()
                for item in (stack or [])
                if item
            },
            key=str.casefold,
        )

        experience_values = [
            value
            for value in session.scalars(
                select(Job.experience)
                .where(
                    Job.experience.is_not(
                        None
                    )
                )
                .distinct()
            ).all()
            if value
        ]
        available_experience_levels = {
            normalize_experience(value)
            for value in experience_values
        }
        experience_options = [
            (level, label)
            for level, label in (
                EXPERIENCE_LEVEL_LABELS.items()
            )
            if (
                level == "all"
                or level
                in available_experience_levels
            )
        ]


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


        # 預設只顯示網站定位相關的技術職缺。
        if category == "relevant":
            filters.append(
                Job.job_category.in_(
                    RELEVANT_JOB_CATEGORIES
                )
            )
        elif category != "all":
            filters.append(
                Job.job_category == category
            )


        if tech:
            filters.append(
                Job.tech_stack.contains(
                    [tech]
                )
            )


        if experience_level != "all":
            matching_experience_values = [
                value
                for value in experience_values
                if normalize_experience(value)
                == experience_level
            ]
            filters.append(
                Job.experience.in_(
                    matching_experience_values
                )
                if matching_experience_values
                else false()
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
        category=category,
        tech=tech,
        experience_level=experience_level,
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
        category=category,
        tech=tech,
        experience_level=experience_level,
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
        category=category,
        tech=tech,
        experience_level=experience_level,
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
        category=category,
        tech="",
        experience_level="all",
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
            category=category,
            tech=tech,
            experience_level=experience_level,
            page=1,
        )
        for status in (
            "all",
            *JOB_APPLICATION_STATUSES,
        )
    }

    category_filter_urls = {
        category_value: dashboard_url(
            home_url,
            view=view,
            q=q,
            location=location,
            sort=sort,
            application_status=(
                application_status
            ),
            category=category_value,
            tech=tech,
            experience_level=experience_level,
            page=1,
        )
        for category_value in (
            "relevant",
            "all",
            *JOB_CATEGORIES,
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
            category=category,
            tech=tech,
            experience_level=experience_level,
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
            category=category,
            tech=tech,
            experience_level=experience_level,
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
            "category": category,
            "tech": tech,
            "tech_options": tech_options,
            "experience_level": (
                experience_level
            ),
            "experience_options": (
                experience_options
            ),
            "job_category_labels": (
                JOB_CATEGORY_LABELS
            ),
            "category_filter_urls": (
                category_filter_urls
            ),
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
            "message": message,

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
    category,
    tech,
    experience_level,
    page,
    message=None,
):
    redirect_url = dashboard_url(
        request.url_for("home"),
        view=view,
        q=q,
        location=location,
        sort=sort,
        application_status=(
            application_status
        ),
        category=category,
        tech=tech,
        experience_level=experience_level,
        page=page,
    )

    if message:
        redirect_url = (
            redirect_url.include_query_params(
                message=message
            )
        )

    return RedirectResponse(
        url=str(redirect_url),
        status_code=303,
    )


@app.post("/crawler/run")
def trigger_crawler_run(
    request: Request,
    background_tasks: BackgroundTasks,
    view: str = Form("all"),
    q: str = Form(""),
    location: str = Form(""),
    sort: str = Form(""),
    page: int = Form(1),
    filter_status: str = Form("all"),
    category: str = Form("relevant"),
    tech: str = Form(""),
    experience_level: str = Form(
        "all",
        alias="experience",
    ),
):
    reservation = reserve_pipeline()

    if reservation is None:
        message = (
            "crawler_already_running"
        )
    else:
        try:
            background_tasks.add_task(
                run_pipeline,
                trigger_type="DASHBOARD",
                reservation=reservation,
            )
        except Exception:
            reservation.release()
            raise

        message = "crawler_started"

    return job_dashboard_redirect(
        request,
        view=view,
        q=q,
        location=location,
        sort=sort,
        application_status=(
            filter_status
        ),
        category=category,
        tech=tech,
        experience_level=experience_level,
        page=max(page, 1),
        message=message,
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
    category: str = Form("relevant"),
    tech: str = Form(""),
    experience_level: str = Form(
        "all",
        alias="experience",
    ),
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
        category=category,
        tech=tech,
        experience_level=experience_level,
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
    category: str = Form("relevant"),
    tech: str = Form(""),
    experience_level: str = Form(
        "all",
        alias="experience",
    ),
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
        category=category,
        tech=tech,
        experience_level=experience_level,
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


def _form_enabled(value):
    return (value or "").strip().lower() in {
        "1",
        "true",
        "on",
        "yes",
    }


def _settings_redirect(request, message):
    url = request.url_for(
        "crawler_settings"
    ).include_query_params(
        message=message
    )
    return RedirectResponse(
        url=str(url),
        status_code=303,
    )


@app.get("/settings/crawler")
def crawler_settings(
    request: Request,
    message: str | None = Query(None),
):
    with SessionLocal() as session:
        service = CrawlerSettingsService(
            session
        )
        settings = service.get_settings()
        keywords = service.get_keywords()
        settings_view = {
            "max_detail_fetches": (
                settings.max_detail_fetches
            ),
            "max_search_pages_per_keyword": (
                settings
                .max_search_pages_per_keyword
            ),
            "detail_refresh_hours": (
                settings.detail_refresh_hours
            ),
            "request_interval_seconds": (
                settings
                .request_interval_seconds
            ),
        }
        keyword_views = [
            {
                "id": item.id,
                "keyword": item.keyword,
                "enabled": item.enabled,
                "target_count": (
                    item.target_count
                ),
                "sort_order": item.sort_order,
            }
            for item in keywords
        ]
        session.commit()

    return templates.TemplateResponse(
        request=request,
        name="crawler_settings.html",
        context={
            "active_page": "crawler_settings",
            "settings": settings_view,
            "keywords": keyword_views,
            "message": message,
        },
    )


@app.post("/settings/crawler")
def update_crawler_settings(
    request: Request,
    max_detail_fetches: str = Form(...),
    max_search_pages_per_keyword: str = Form(...),
    detail_refresh_hours: str = Form(...),
    request_interval_seconds: str = Form(...),
):
    with SessionLocal() as session:
        service = CrawlerSettingsService(
            session
        )
        try:
            service.update_settings(
                max_detail_fetches=(
                    max_detail_fetches
                ),
                max_search_pages_per_keyword=(
                    max_search_pages_per_keyword
                ),
                detail_refresh_hours=(
                    detail_refresh_hours
                ),
                request_interval_seconds=(
                    request_interval_seconds
                ),
            )
            session.commit()
        except ValueError as error:
            session.rollback()
            raise HTTPException(
                status_code=422,
                detail=str(error),
            ) from error

    return _settings_redirect(
        request,
        "settings_saved",
    )


@app.post("/settings/crawler/keywords")
def add_crawler_keyword(
    request: Request,
    keyword: str = Form(...),
    target_count: str = Form(...),
    sort_order: str = Form("0"),
    enabled: str | None = Form(None),
):
    with SessionLocal() as session:
        service = CrawlerSettingsService(
            session
        )
        try:
            service.add_keyword(
                keyword=keyword,
                enabled=_form_enabled(
                    enabled
                ),
                target_count=target_count,
                sort_order=sort_order,
            )
            session.commit()
        except ValueError as error:
            session.rollback()
            raise HTTPException(
                status_code=422,
                detail=str(error),
            ) from error

    return _settings_redirect(
        request,
        "keyword_added",
    )


@app.post(
    "/settings/crawler/keywords/{keyword_id}"
)
def update_crawler_keyword(
    keyword_id: int,
    request: Request,
    keyword: str = Form(...),
    target_count: str = Form(...),
    sort_order: str = Form("0"),
    enabled: str | None = Form(None),
):
    with SessionLocal() as session:
        service = CrawlerSettingsService(
            session
        )
        try:
            service.update_keyword(
                keyword_id,
                keyword=keyword,
                enabled=_form_enabled(
                    enabled
                ),
                target_count=target_count,
                sort_order=sort_order,
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

    return _settings_redirect(
        request,
        "keyword_updated",
    )


@app.post(
    "/settings/crawler/keywords/{keyword_id}/delete"
)
def delete_crawler_keyword(
    keyword_id: int,
    request: Request,
):
    with SessionLocal() as session:
        service = CrawlerSettingsService(
            session
        )
        try:
            service.delete_keyword(
                keyword_id
            )
            session.commit()
        except LookupError as error:
            session.rollback()
            raise HTTPException(
                status_code=404,
                detail=str(error),
            ) from error

    return _settings_redirect(
        request,
        "keyword_deleted",
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
