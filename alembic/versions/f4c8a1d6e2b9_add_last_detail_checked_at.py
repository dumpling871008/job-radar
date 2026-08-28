"""add last_detail_checked_at to jobs

Revision ID: f4c8a1d6e2b9
Revises: d3f6a9c2e8b1
Create Date: 2026-08-28 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4c8a1d6e2b9"
down_revision: Union[
    str,
    Sequence[str],
    None,
] = "d3f6a9c2e8b1"
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
            "last_detail_checked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "jobs",
        "last_detail_checked_at",
    )
