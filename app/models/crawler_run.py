from datetime import datetime

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    Text,
    func,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.db.base import Base


class CrawlerRun(Base):

    __tablename__ = "crawler_runs"

    # 每次執行的唯一 ID
    run_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    # MANUAL / SCHEDULED
    trigger_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="MANUAL",
    )

    # RUNNING / SUCCESS / PARTIAL_SUCCESS / FAILED
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Search API 回傳總筆數
    search_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # 去重、quota 後真正選出的數量
    selected_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Detail API
    detail_success_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    detail_failed_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Raw Layer
    raw_inserted_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Clean Layer
    new_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    updated_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    unchanged_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )