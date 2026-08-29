from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.dialects.postgresql import (
    JSONB,
)

from app.db.base import Base


if TYPE_CHECKING:
    from app.models.job_application import (
        JobApplication,
    )


class Job(Base):

    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            "job_category IN ("
            "'SOFTWARE', 'AI_DATA', "
            "'DEVOPS_CLOUD', "
            "'OTHER_ENGINEERING', "
            "'NON_TECH', 'UNKNOWN'"
            ")",
            name="ck_jobs_job_category",
        ),
    )

    application: Mapped[
        "JobApplication | None"
    ] = relationship(
        back_populates="job",
        uselist=False,
    )

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

    # Clean layer 的職缺領域分類
    job_category: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="UNKNOWN",
        server_default="UNKNOWN",
    )

    # Detail API 提供的原始薪資顯示文字
    salary_text: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # 由 title / description deterministic 擷取的技術標籤
    tech_stack: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
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

    # 職缺重要內容最近一次真正變更的時間
    content_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # 最近一次成功取得完整 Detail API 的時間
    last_detail_checked_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # DB 資料最後更新時間
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
