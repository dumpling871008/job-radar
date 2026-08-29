"""add crawler runtime settings

Revision ID: e2a7c5d9b4f1
Revises: c8e4a1f7b2d6
Create Date: 2026-08-29 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e2a7c5d9b4f1"
down_revision: Union[str, Sequence[str], None] = (
    "c8e4a1f7b2d6"
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    settings_table = op.create_table(
        "crawler_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "max_detail_fetches",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "max_search_pages_per_keyword",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "detail_refresh_hours",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "request_interval_seconds",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "id = 1",
            name="ck_crawler_settings_singleton",
        ),
        sa.CheckConstraint(
            "max_detail_fetches BETWEEN 1 AND 500",
            name="ck_crawler_settings_max_detail",
        ),
        sa.CheckConstraint(
            "max_search_pages_per_keyword BETWEEN 1 AND 20",
            name="ck_crawler_settings_max_pages",
        ),
        sa.CheckConstraint(
            "detail_refresh_hours BETWEEN 1 AND 720",
            name="ck_crawler_settings_refresh_hours",
        ),
        sa.CheckConstraint(
            "request_interval_seconds >= 1",
            name="ck_crawler_settings_request_interval",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    keyword_table = op.create_table(
        "crawler_keywords",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "keyword",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "target_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "target_count BETWEEN 1 AND 500",
            name="ck_crawler_keywords_target_count",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "keyword",
            name="uq_crawler_keywords_keyword",
        ),
    )
    op.add_column(
        "crawler_runs",
        sa.Column(
            "config_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    op.bulk_insert(
        settings_table,
        [
            {
                "id": 1,
                "max_detail_fetches": 120,
                "max_search_pages_per_keyword": 8,
                "detail_refresh_hours": 48,
                "request_interval_seconds": 2.0,
            }
        ],
    )
    op.bulk_insert(
        keyword_table,
        [
            {"keyword": "AI 應用工程師", "enabled": False, "target_count": 1, "sort_order": 10},
            {"keyword": "AI 工程師", "enabled": False, "target_count": 1, "sort_order": 20},
            {"keyword": "生成式 AI 工程師", "enabled": False, "target_count": 1, "sort_order": 30},
            {"keyword": "Python 工程師", "enabled": False, "target_count": 1, "sort_order": 40},
            {"keyword": "資料工程師", "enabled": True, "target_count": 120, "sort_order": 50},
            {"keyword": "後端工程師", "enabled": False, "target_count": 1, "sort_order": 60},
            {"keyword": "軟體工程師", "enabled": False, "target_count": 1, "sort_order": 70},
        ],
    )


def downgrade() -> None:
    op.drop_column(
        "crawler_runs",
        "config_snapshot",
    )
    op.drop_table("crawler_keywords")
    op.drop_table("crawler_settings")
