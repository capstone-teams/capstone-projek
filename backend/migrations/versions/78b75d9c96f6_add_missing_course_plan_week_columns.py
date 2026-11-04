"""add missing course plan week columns

Revision ID: 78b75d9c96f6
Revises: f3a1c9d2b7e4
Create Date: 2026-11-04 18:17:25.686858

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '78b75d9c96f6'
down_revision: Union[str, Sequence[str], None] = 'f3a1c9d2b7e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "course_plan_weeks",
        sa.Column("objectives", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "course_plan_weeks",
        sa.Column("planned_activities", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "course_plan_weeks",
        sa.Column(
            "week_type",
            sa.String(length=10),
            nullable=False,
            server_default="regular",
        ),
    )
    op.add_column(
        "course_plan_weeks",
        sa.Column("rps_week", sa.Integer(), nullable=True),
    )

    op.create_check_constraint(
        "ck_course_plan_weeks_week_type",
        "course_plan_weeks",
        "week_type IN ('regular', 'kuis', 'uts', 'uas')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_course_plan_weeks_week_type",
        "course_plan_weeks",
        type_="check",
    )
    op.drop_column("course_plan_weeks", "rps_week")
    op.drop_column("course_plan_weeks", "week_type")
    op.drop_column("course_plan_weeks", "planned_activities")
    op.drop_column("course_plan_weeks", "objectives")
