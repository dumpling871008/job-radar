from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.db.base import Base


class RawJob(Base):

    __tablename__ = "raw_jobs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # 之後建立 crawler_runs 時可以串起來
    crawler_run_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="104",
    )

    # 104 jobNo
    # 注意：Raw Layer 不可以 unique
    source_job_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    source_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # 保存 API 原始 JSON
    raw_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    # 原始資料 hash
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    crawled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )