from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    Integer,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CrawlerSetting(Base):
    __tablename__ = "crawler_settings"
    __table_args__ = (
        CheckConstraint(
            "id = 1",
            name="ck_crawler_settings_singleton",
        ),
        CheckConstraint(
            "max_detail_fetches BETWEEN 1 AND 500",
            name="ck_crawler_settings_max_detail",
        ),
        CheckConstraint(
            "max_search_pages_per_keyword BETWEEN 1 AND 20",
            name="ck_crawler_settings_max_pages",
        ),
        CheckConstraint(
            "detail_refresh_hours BETWEEN 1 AND 720",
            name="ck_crawler_settings_refresh_hours",
        ),
        CheckConstraint(
            "request_interval_seconds >= 1",
            name="ck_crawler_settings_request_interval",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        default=1,
    )
    max_detail_fetches: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    max_search_pages_per_keyword: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    detail_refresh_hours: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    request_interval_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
