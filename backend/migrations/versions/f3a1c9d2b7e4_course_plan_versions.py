"""course plan versions and weekly plan (BE-14.1)

Tabel ``course_plans`` dan ``course_plan_weeks`` sudah dibuat pada migrasi init
(BE-02) dengan bentuk placeholder berbasis course yang belum pernah ditulis
service apa pun. Migrasi ini menyesuaikannya dengan issue BE-14.1: rencana
dimiliki sebuah workflow, disimpan berversi, dan tiap minggu memuat struktur
Course Plan Week (content-schema §9) beserta penanda UTS/UAS dan referensi baris
RPS.

Catatan bentuk:

- ``course_id`` dan ``rps_analysis_id`` dilonggarkan menjadi nullable. Alur
  BE-14 membuat rencana dari workflow, sebelum course Moodle ada, dan hasil
  analisis RPS saat ini disimpan pada ``rps.structured_data`` (bukan baris
  ``rps_analyses``), sehingga kolom itu tidak selalu terisi.
- ``workflow_id`` dan ``rps_id`` juga nullable demi baris lama; service BE-14
  selalu mengisinya.
- partial unique index ``uq_course_plans_workflow_approved`` menjaga invariant
  "hanya satu versi APPROVED per workflow" di level database.

Revision ID: f3a1c9d2b7e4
Revises: 3482768899c4
Create Date: 2026-11-04 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f3a1c9d2b7e4"
down_revision: Union[str, Sequence[str], None] = "3482768899c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ID_LENGTH = 22


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "course_plans", "course_id", existing_type=sa.String(length=ID_LENGTH), nullable=True
    )
    op.alter_column(
        "course_plans",
        "rps_analysis_id",
        existing_type=sa.String(length=ID_LENGTH),
        nullable=True,
    )

    op.add_column(
        "course_plans",
        sa.Column("workflow_id", sa.String(length=ID_LENGTH), nullable=True),
    )
    op.add_column(
        "course_plans", sa.Column("rps_id", sa.String(length=ID_LENGTH), nullable=True)
    )
    op.add_column(
        "course_plans",
        sa.Column("weeks_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "course_plans",
        sa.Column(
            "activity_configuration",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "course_plans",
        sa.Column(
            "validation_result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column("course_plans", sa.Column("revision_notes", sa.Text(), nullable=True))
    op.add_column(
        "course_plans", sa.Column("regeneration_instruction", sa.Text(), nullable=True)
    )
    op.add_column(
        "course_plans", sa.Column("prompt_version", sa.String(length=50), nullable=True)
    )
    op.add_column(
        "course_plans", sa.Column("model_name", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "course_plans",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_foreign_key(
        "fk_course_plans_workflow_id",
        "course_plans",
        "workflows",
        ["workflow_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_course_plans_rps_id",
        "course_plans",
        "rps",
        ["rps_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_course_plans_workflow_id"), "course_plans", ["workflow_id"], unique=False
    )
    op.create_index(
        op.f("ix_course_plans_rps_id"), "course_plans", ["rps_id"], unique=False
    )
    op.create_unique_constraint(
        "uq_course_plans_workflow_version",
        "course_plans",
        ["workflow_id", "version"],
    )
    op.create_index(
        "uq_course_plans_workflow_approved",
        "course_plans",
        ["workflow_id"],
        unique=True,
        postgresql_where=sa.text("status = 'APPROVED'"),
    )
    op.create_check_constraint(
        "ck_course_plans_weeks_count", "course_plans", "weeks_count >= 0"
    )

    op.add_column(
        "course_plan_weeks",
        sa.Column("objectives", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "course_plan_weeks",
        sa.Column(
            "planned_activities", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )
    op.add_column(
        "course_plan_weeks",
        sa.Column(
            "week_type", sa.String(length=10), server_default="regular", nullable=False
        ),
    )
    op.add_column(
        "course_plan_weeks", sa.Column("rps_week", sa.Integer(), nullable=True)
    )
    op.create_check_constraint(
        "ck_course_plan_weeks_week_number", "course_plan_weeks", "week_number >= 1"
    )
    op.create_check_constraint(
        "ck_course_plan_weeks_week_type",
        "course_plan_weeks",
        "week_type IN ('regular', 'kuis', 'uts', 'uas')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_course_plan_weeks_week_type", "course_plan_weeks", type_="check")
    op.drop_constraint(
        "ck_course_plan_weeks_week_number", "course_plan_weeks", type_="check"
    )
    op.drop_column("course_plan_weeks", "rps_week")
    op.drop_column("course_plan_weeks", "week_type")
    op.drop_column("course_plan_weeks", "planned_activities")
    op.drop_column("course_plan_weeks", "objectives")

    op.drop_constraint("ck_course_plans_weeks_count", "course_plans", type_="check")
    op.drop_index("uq_course_plans_workflow_approved", table_name="course_plans")
    op.drop_constraint(
        "uq_course_plans_workflow_version", "course_plans", type_="unique"
    )
    op.drop_index(op.f("ix_course_plans_rps_id"), table_name="course_plans")
    op.drop_index(op.f("ix_course_plans_workflow_id"), table_name="course_plans")
    op.drop_constraint("fk_course_plans_rps_id", "course_plans", type_="foreignkey")
    op.drop_constraint("fk_course_plans_workflow_id", "course_plans", type_="foreignkey")
    op.drop_column("course_plans", "approved_at")
    op.drop_column("course_plans", "model_name")
    op.drop_column("course_plans", "prompt_version")
    op.drop_column("course_plans", "regeneration_instruction")
    op.drop_column("course_plans", "revision_notes")
    op.drop_column("course_plans", "validation_result")
    op.drop_column("course_plans", "activity_configuration")
    op.drop_column("course_plans", "weeks_count")
    op.drop_column("course_plans", "rps_id")
    op.drop_column("course_plans", "workflow_id")

    op.alter_column(
        "course_plans",
        "rps_analysis_id",
        existing_type=sa.String(length=ID_LENGTH),
        nullable=False,
    )
    op.alter_column(
        "course_plans", "course_id", existing_type=sa.String(length=ID_LENGTH), nullable=False
    )
