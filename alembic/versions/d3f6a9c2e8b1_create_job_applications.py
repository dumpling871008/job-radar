"""create job_applications

Revision ID: d3f6a9c2e8b1
Revises: b7d9e2f4a1c3
Create Date: 2026-08-28 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d3f6a9c2e8b1"
down_revision: Union[
    str,
    Sequence[str],
    None,
] = "b7d9e2f4a1c3"
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
    op.create_table(
        "job_applications",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "job_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="UNREAD",
            nullable=False,
        ),
        sa.Column(
            "note",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "applied_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "interview_at",
            sa.DateTime(timezone=True),
            nullable=True,
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
            "status IN ("
            "'UNREAD', "
            "'SAVED', "
            "'APPLIED', "
            "'INTERVIEW', "
            "'REJECTED', "
            "'CLOSED'"
            ")",
            name=(
                "ck_job_applications_status"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_id",
            name=(
                "uq_job_applications_job_id"
            ),
        ),
    )


def downgrade() -> None:
    op.drop_table(
        "job_applications"
    )
