"""create workflow and workflow event (BE-11.1)

Fondasi workflow Agentic AI (issue BE-11.1, proposal §3.5.6 dan §3.6.7–§3.6.8):

- ``workflows`` — satu rangkaian pekerjaan agent untuk sebuah RPS, dengan status
  state machine, course target Moodle, model LLM, kemajuan tahap, serta waktu
  mulai/selesai;
- ``workflow_events`` — riwayat kejadian workflow (perubahan tahap, aktivitas
  agent, operasi Moodle, retry, kegagalan) yang dibaca endpoint monitoring dan
  dikirim ke WebSocket (BE-11.3).

``rps.workflow_id`` sudah ada sejak BE-08.2 tanpa foreign key: baris RPS dapat
dibuat/diperbarui sebelum workflow-nya, dan reanalyze memakai kembali workflow
yang sama. Menambahkan FK di sini akan membuat urutan penulisan itu rapuh tanpa
menambah invariant yang benar-benar dijaga (orkestrator selalu menulis id yang
valid). Karena itu relasinya tetap dicatat sebagai kolom biasa.

Revision ID: e1444178fa3c
Revises: 7c2f9a41e6b3
Create Date: 2026-11-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e1444178fa3c'
down_revision: Union[str, Sequence[str], None] = '7c2f9a41e6b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Panjang kolom identifier mengikuti ``src.models.base.ID_LENGTH`` (ShortUUID).
ID_LENGTH = 22


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "workflows",
        sa.Column("owner_id", sa.String(length=ID_LENGTH), nullable=False),
        sa.Column("rps_id", sa.String(length=ID_LENGTH), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "QUEUED",
                "PROCESSING_RPS",
                "ANALYZING_RPS",
                "PLANNING_COURSE",
                "GENERATING_CONTENT",
                "VALIDATING",
                "WAITING_FOR_REVIEW",
                "EXECUTING_TO_MOODLE",
                "VERIFYING",
                "RETRYING",
                "COMPLETED",
                "FAILED",
                name="workflow_status",
            ),
            server_default="QUEUED",
            nullable=False,
        ),
        sa.Column("moodle_course_id", sa.Integer(), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("progress_completed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("progress_total", sa.Integer(), server_default="0", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=ID_LENGTH), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("length(id) = 22", name="ck_id_length"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["rps_id"], ["rps.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workflows_owner_id"), "workflows", ["owner_id"], unique=False)
    op.create_index(op.f("ix_workflows_rps_id"), "workflows", ["rps_id"], unique=False)
    op.create_index(op.f("ix_workflows_status"), "workflows", ["status"], unique=False)

    op.create_table(
        "workflow_events",
        sa.Column("workflow_id", sa.String(length=ID_LENGTH), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum(
                "PERUBAHAN_TAHAP",
                "AKTIVITAS_AGENT",
                "OPERASI_MOODLE",
                "RETRY_FIX",
                "ERROR_FAILURE",
                name="workflow_event_type",
            ),
            nullable=False,
        ),
        sa.Column("event", sa.String(length=100), nullable=False),
        sa.Column("stage", sa.String(length=100), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("id", sa.String(length=ID_LENGTH), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("length(id) = 22", name="ck_id_length"),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_workflow_events_workflow_id"),
        "workflow_events",
        ["workflow_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_workflow_events_workflow_id"), table_name="workflow_events"
    )
    op.drop_table("workflow_events")
    op.drop_index(op.f("ix_workflows_status"), table_name="workflows")
    op.drop_index(op.f("ix_workflows_rps_id"), table_name="workflows")
    op.drop_index(op.f("ix_workflows_owner_id"), table_name="workflows")
    op.drop_table("workflows")

    # ``drop_table`` tidak menghapus tipe enum yang dibuat bersamanya.
    op.execute("DROP TYPE IF EXISTS workflow_event_type")
    op.execute("DROP TYPE IF EXISTS workflow_status")
