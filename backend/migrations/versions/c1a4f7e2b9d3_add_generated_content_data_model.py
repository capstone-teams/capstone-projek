"""generated content data model (BE-19.1)

Menambahkan kolom versi dan identitas konten pada ``contents`` dan
``activities``, serta temuan validasi pada ``validation_results``.

Keputusan model:

- ``LEARNING_MATERIAL``/``RESOURCE`` tetap di ``contents`` dan
  ``ASSIGNMENT``/``QUIZ`` tetap di ``activities``, mengikuti Content Output
  Schema BE-20.1 (``src.schemas.content.REGISTRY``). Tidak ada tabel
  ``generated_content`` baru yang menduplikasi kedua tabel itu.
- ``content_key`` mengikat versi-versi dari konten yang sama; unique
  ``(content_key, version)`` mencegah dua baris dengan versi yang sama.
- ``validation_results.agent_run_id`` menjadi nullable karena generation
  konten berjalan sebagai tahap workflow tanpa selalu membuat ``AgentRun``.
- ``activity_status`` mendapat nilai ``PENDING_REVIEW`` dan ``REJECTED`` agar
  assignment/quiz dapat direview dengan status yang sama seperti content.

Revision ID: c1a4f7e2b9d3
Revises: 9d2c4b7e1f3a
Create Date: 2026-11-08 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1a4f7e2b9d3"
down_revision: Union[str, Sequence[str], None] = "9d2c4b7e1f3a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Panjang kolom identifier mengikuti ``src.models.base.ID_LENGTH``.
ID_LENGTH = 22


def upgrade() -> None:
    """Upgrade schema."""
    # --- contents ---------------------------------------------------------
    for column in (
        sa.Column("workflow_id", sa.String(length=ID_LENGTH), nullable=True),
        sa.Column("course_plan_id", sa.String(length=ID_LENGTH), nullable=True),
        sa.Column("week_number", sa.Integer(), nullable=True),
        sa.Column("content_key", sa.String(length=255), nullable=True),
        sa.Column("revision_notes", sa.Text(), nullable=True),
        sa.Column("prompt_version", sa.String(length=50), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=True),
    ):
        op.add_column("contents", column)

    op.create_foreign_key(
        "contents_workflow_id_fkey",
        "contents",
        "workflows",
        ["workflow_id"],
        ["id"],
    )
    op.create_foreign_key(
        "contents_course_plan_id_fkey",
        "contents",
        "course_plans",
        ["course_plan_id"],
        ["id"],
    )
    op.create_index("ix_contents_workflow_id", "contents", ["workflow_id"])
    op.create_index("ix_contents_course_plan_id", "contents", ["course_plan_id"])
    op.create_index("ix_contents_content_key", "contents", ["content_key"])
    op.create_index(
        "ix_contents_workflow_week", "contents", ["workflow_id", "week_number"]
    )
    op.create_unique_constraint(
        "uq_contents_content_key_version",
        "contents",
        ["content_key", "version"],
    )

    # --- activities -------------------------------------------------------
    # Nilai enum baru belum dipakai pada transaksi migrasi ini.
    op.execute(
        "ALTER TYPE activity_status ADD VALUE IF NOT EXISTS 'PENDING_REVIEW'"
    )
    op.execute("ALTER TYPE activity_status ADD VALUE IF NOT EXISTS 'REJECTED'")

    for column in (
        sa.Column("workflow_id", sa.String(length=ID_LENGTH), nullable=True),
        sa.Column("course_plan_id", sa.String(length=ID_LENGTH), nullable=True),
        sa.Column("week_number", sa.Integer(), nullable=True),
        sa.Column("content_key", sa.String(length=255), nullable=True),
        sa.Column("revision_notes", sa.Text(), nullable=True),
        sa.Column("prompt_version", sa.String(length=50), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column(
            "generated_by_agent_run_id",
            sa.String(length=ID_LENGTH),
            nullable=True,
        ),
    ):
        op.add_column("activities", column)

    op.create_foreign_key(
        "activities_workflow_id_fkey",
        "activities",
        "workflows",
        ["workflow_id"],
        ["id"],
    )
    op.create_foreign_key(
        "activities_course_plan_id_fkey",
        "activities",
        "course_plans",
        ["course_plan_id"],
        ["id"],
    )
    op.create_foreign_key(
        "activities_generated_by_agent_run_id_fkey",
        "activities",
        "agent_runs",
        ["generated_by_agent_run_id"],
        ["id"],
    )
    op.create_index("ix_activities_workflow_id", "activities", ["workflow_id"])
    op.create_index(
        "ix_activities_course_plan_id", "activities", ["course_plan_id"]
    )
    op.create_index("ix_activities_content_key", "activities", ["content_key"])
    op.create_index(
        "ix_activities_workflow_week",
        "activities",
        ["workflow_id", "week_number"],
    )
    op.create_unique_constraint(
        "uq_activities_content_key_version",
        "activities",
        ["content_key", "version"],
    )

    # --- validation_results ----------------------------------------------
    op.alter_column(
        "validation_results",
        "agent_run_id",
        existing_type=sa.String(length=ID_LENGTH),
        nullable=True,
    )
    op.add_column(
        "validation_results",
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "validation_results",
        sa.Column(
            "validated_at", sa.DateTime(timezone=True), nullable=True
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("validation_results", "validated_at")
    op.drop_column("validation_results", "retry_count")
    # Baris tanpa agent run tidak dapat memenuhi kolom lama yang NOT NULL.
    op.execute("DELETE FROM validation_results WHERE agent_run_id IS NULL")
    op.alter_column(
        "validation_results",
        "agent_run_id",
        existing_type=sa.String(length=ID_LENGTH),
        nullable=False,
    )

    op.drop_constraint(
        "uq_activities_content_key_version", "activities", type_="unique"
    )
    op.drop_index("ix_activities_workflow_week", table_name="activities")
    op.drop_index("ix_activities_content_key", table_name="activities")
    op.drop_index("ix_activities_course_plan_id", table_name="activities")
    op.drop_index("ix_activities_workflow_id", table_name="activities")
    op.drop_constraint(
        "activities_generated_by_agent_run_id_fkey",
        "activities",
        type_="foreignkey",
    )
    op.drop_constraint(
        "activities_course_plan_id_fkey", "activities", type_="foreignkey"
    )
    op.drop_constraint(
        "activities_workflow_id_fkey", "activities", type_="foreignkey"
    )
    for column in (
        "generated_by_agent_run_id",
        "model_name",
        "prompt_version",
        "revision_notes",
        "content_key",
        "week_number",
        "course_plan_id",
        "workflow_id",
    ):
        op.drop_column("activities", column)

    # Nilai enum tidak dapat dihapus satu per satu; tipe dibentuk ulang tanpa
    # PENDING_REVIEW/REJECTED. Baris yang terlanjur memakainya dipetakan ke
    # status sebelumnya agar migrasi tidak gagal.
    op.execute(
        "UPDATE activities SET status = 'APPROVED' WHERE status = 'REJECTED'"
    )
    op.execute(
        "UPDATE activities SET status = 'VALIDATED' "
        "WHERE status = 'PENDING_REVIEW'"
    )
    op.execute("ALTER TYPE activity_status RENAME TO activity_status_old")
    op.execute(
        "CREATE TYPE activity_status AS ENUM "
        "('DRAFT', 'VALIDATED', 'APPROVED', 'EXECUTED')"
    )
    op.execute(
        "ALTER TABLE activities ALTER COLUMN status TYPE activity_status "
        "USING status::text::activity_status"
    )
    op.execute("DROP TYPE activity_status_old")

    op.drop_constraint(
        "uq_contents_content_key_version", "contents", type_="unique"
    )
    op.drop_index("ix_contents_workflow_week", table_name="contents")
    op.drop_index("ix_contents_content_key", table_name="contents")
    op.drop_index("ix_contents_course_plan_id", table_name="contents")
    op.drop_index("ix_contents_workflow_id", table_name="contents")
    op.drop_constraint(
        "contents_course_plan_id_fkey", "contents", type_="foreignkey"
    )
    op.drop_constraint(
        "contents_workflow_id_fkey", "contents", type_="foreignkey"
    )
    for column in (
        "model_name",
        "prompt_version",
        "revision_notes",
        "content_key",
        "week_number",
        "course_plan_id",
        "workflow_id",
    ):
        op.drop_column("contents", column)
