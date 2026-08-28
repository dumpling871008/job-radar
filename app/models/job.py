from datetime import datetime

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Job(Base):

    __tablename__ = "jobs"

    # 資料庫自己的流水號
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # 資料來源，例如 104
    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="104",
    )

    # 104 的 jobNo
    source_job_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
    )

    # 職缺名稱
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # 公司名稱
    company_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # 地區
    location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Search API 的 JD 摘要
    description_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Detail API 的完整 JD
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # 原始職缺網址
    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # 經驗要求
    experience: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # 學歷要求
    education: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # 用來判斷 JD 有沒有變化
    content_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    # 第一次看到這個職缺
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # 最近一次看到這個職缺
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # DB 資料最後更新時間
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )