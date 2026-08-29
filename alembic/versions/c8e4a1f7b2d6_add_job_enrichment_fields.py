"""add job enrichment fields

Revision ID: c8e4a1f7b2d6
Revises: a6b2e9c4d7f1
Create Date: 2026-08-29 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c8e4a1f7b2d6"
down_revision: Union[
    str,
    Sequence[str],
    None,
] = "a6b2e9c4d7f1"
branch_labels: Union[
    str,
    Sequence[str],
    None,
] = None
depends_on: Union[
    str,
    Sequence[str],
    None,
] = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column(
            "salary_text",
            sa.String(length=255),
            nullable=True,
        ),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "tech_stack",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "jobs",
        "tech_stack",
    )
    op.drop_column(
        "jobs",
        "salary_text",
    )
