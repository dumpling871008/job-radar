"""add job_category to jobs

Revision ID: a6b2e9c4d7f1
Revises: f4c8a1d6e2b9
Create Date: 2026-08-28 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a6b2e9c4d7f1"
down_revision: Union[
    str,
    Sequence[str],
    None,
] = "f4c8a1d6e2b9"
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
            "job_category",
            sa.String(length=30),
            server_default="UNKNOWN",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_jobs_job_category",
        "jobs",
        "job_category IN ("
        "'SOFTWARE', 'AI_DATA', 'DEVOPS_CLOUD', "
        "'OTHER_ENGINEERING', 'NON_TECH', 'UNKNOWN'"
        ")",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_jobs_job_category",
        "jobs",
        type_="check",
    )
    op.drop_column(
        "jobs",
        "job_category",
    )
