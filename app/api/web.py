import math
from datetime import datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sqlalchemy import func, or_, select

from app.db.database import SessionLocal
from app.models.job import Job


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


@app.get("/")
def home(
    request: Request,

    view: Literal["all", "today"] = Query(
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
):

    q = q.strip()
    location = location.strip()


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


        # =========================
        # 3. 計算符合條件的總筆數
        # =========================

        count_statement = select(
            func.count(Job.id)
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

        statement = select(Job)


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

    all_view_url = (
        home_url.include_query_params(
            view="all",
            q=q,
            location=location,
            page=1,
        )
    )

    today_view_url = (
        home_url.include_query_params(
            view="today",
            q=q,
            location=location,
            page=1,
        )
    )

    clear_url = (
        home_url.include_query_params(
            view=view,
            page=1,
        )
    )

    previous_url = None
    next_url = None


    if page > 1:

        previous_url = (
            home_url.include_query_params(
                view=view,
                q=q,
                location=location,
                page=page - 1,
            )
        )


    if page < total_pages:

        next_url = (
            home_url.include_query_params(
                view=view,
                q=q,
                location=location,
                page=page + 1,
            )
        )


    return templates.TemplateResponse(
        request=request,
        name="jobs.html",
        context={
            "jobs": jobs,
            "view": view,
            "page": page,
            "total_pages": total_pages,
            "total_jobs": total_jobs,

            "q": q,
            "location": location,
            "locations": locations,

            "all_view_url": all_view_url,
            "today_view_url": today_view_url,
            "clear_url": clear_url,
            "previous_url": previous_url,
            "next_url": next_url,
        },
    )
