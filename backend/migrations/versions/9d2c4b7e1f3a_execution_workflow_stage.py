"""execution workflow stage: moodle execution per run + execution operations

Revision ID: 9d2c4b7e1f3a
Revises: f3a1c9d2b7e4
Create Date: 2026-11-08 09:00:00.000000

Tabel ``moodle_executions`` sebelumnya mencatat satu panggilan Moodle
(``operation``/``target_type``/``target_id``) dan belum pernah ditulis oleh
service mana pun. Tahap eksekusi BE-17.1 membutuhkannya sebagai **satu run
eksekusi** (workflow, course plan, target Moodle, cakupan, ringkasan read-back),
sedangkan operasi individual dipindahkan ke ``execution_operations``.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9d2c4b7e1f3a"
down_revision: Union[str, Sequence[str], None] = "f3a1c9d2b7e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Kolom per-panggilan lama tidak dipakai lagi; baris historis tidak ada.
    op.drop_index(
        "ix_moodle_executions_moodle_object_id", table_name="moodle_executions"
    )
    op.drop_index("ix_moodle_executions_course_id", table_name="moodle_executions")
    op.drop_constraint(
        "moodle_executions_agent_run_id_fkey",
        "moodle_executions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "moodle_executions_course_id_fkey",
        "moodle_executions",
        type_="foreignkey",
    )
    for column in (
        "agent_run_id",
        "operation",
        "target_type",
        "target_id",
        "moodle_object_id",
        "request_reference",
        "error_code",
        "retry_count",
        "course_id",
    ):
        op.drop_column("moodle_executions", column)

    execution_scope = postgresql.ENUM(
        "STRUCTURE", "FULL", name="execution_scope", create_type=False
    )
    execution_scope.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "moodle_executions",
        sa.Column("workflow_id", sa.String(length=22), nullable=False),
    )
    op.add_column(
        "moodle_executions",
        sa.Column("course_plan_id", sa.String(length=22), nullable=False),
    )
    op.add_column(
        "moodle_executions",
        sa.Column("moodle_course_id", sa.Integer(), nullable=False),
    )
    op.add_column(
        "moodle_executions",
        sa.Column("scope", execution_scope, nullable=False),
    )
    op.add_column(
        "moodle_executions",
        sa.Column("readback", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_foreign_key(
        "moodle_executions_workflow_id_fkey",
        "moodle_executions",
        "workflows",
        ["workflow_id"],
        ["id"],
    )
    op.create_foreign_key(
        "moodle_executions_course_plan_id_fkey",
        "moodle_executions",
        "course_plans",
        ["course_plan_id"],
        ["id"],
    )
    op.create_index(
        "ix_moodle_executions_workflow_id", "moodle_executions", ["workflow_id"]
    )
    op.create_index(
        "ix_moodle_executions_course_plan_id",
        "moodle_executions",
        ["course_plan_id"],
    )

    operation_type = postgresql.ENUM(
        "SECTION",
        "LEARNING_MATERIAL",
        "LEARNING_RESOURCE",
        "ASSIGNMENT",
        "QUIZ",
        name="execution_operation_type",
        create_type=False,
    )
    operation_status = postgresql.ENUM(
        "PENDING",
        "RUNNING",
        "SUCCESS",
        "FAILED",
        "SKIPPED",
        name="execution_operation_status",
        create_type=False,
    )
    operation_type.create(op.get_bind(), checkfirst=True)
    operation_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "execution_operations",
        sa.Column("execution_id", sa.String(length=22), nullable=False),
        sa.Column("course_plan_week_id", sa.String(length=22), nullable=True),
        sa.Column("content_id", sa.String(length=22), nullable=True),
        sa.Column("operation_type", operation_type, nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("moodle_object_id", sa.String(length=255), nullable=True),
        sa.Column("status", operation_status, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "retry_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("id", sa.String(length=22), nullable=False),
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
        sa.CheckConstraint(
            "retry_count >= 0", name="ck_execution_operations_retry_count"
        ),
        sa.ForeignKeyConstraint(["execution_id"], ["moodle_executions.id"]),
        sa.ForeignKeyConstraint(["course_plan_week_id"], ["course_plan_weeks.id"]),
        sa.ForeignKeyConstraint(["content_id"], ["contents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "execution_id",
            "idempotency_key",
            name="uq_execution_operations_execution_key",
        ),
    )
    op.create_index(
        "ix_execution_operations_execution_id",
        "execution_operations",
        ["execution_id"],
    )
    op.create_index(
        "ix_execution_operations_course_plan_week_id",
        "execution_operations",
        ["course_plan_week_id"],
    )
    op.create_index(
        "ix_execution_operations_status", "execution_operations", ["status"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_execution_operations_status", table_name="execution_operations")
    op.drop_index(
        "ix_execution_operations_course_plan_week_id",
        table_name="execution_operations",
    )
    op.drop_index(
        "ix_execution_operations_execution_id", table_name="execution_operations"
    )
    op.drop_table("execution_operations")
    op.execute("DROP TYPE IF EXISTS execution_operation_status")
    op.execute("DROP TYPE IF EXISTS execution_operation_type")

    op.drop_index(
        "ix_moodle_executions_course_plan_id", table_name="moodle_executions"
    )
    op.drop_index("ix_moodle_executions_workflow_id", table_name="moodle_executions")
    op.drop_constraint(
        "moodle_executions_course_plan_id_fkey",
        "moodle_executions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "moodle_executions_workflow_id_fkey",
        "moodle_executions",
        type_="foreignkey",
    )
    for column in ("readback", "scope", "moodle_course_id", "course_plan_id", "workflow_id"):
        op.drop_column("moodle_executions", column)
    op.execute("DROP TYPE IF EXISTS execution_scope")

    # Kolom lama dibuka kembali sebagai nullable: data historis tidak ada.
    op.add_column(
        "moodle_executions", sa.Column("course_id", sa.String(length=22), nullable=True)
    )
    op.add_column(
        "moodle_executions",
        sa.Column("agent_run_id", sa.String(length=22), nullable=True),
    )
    op.add_column(
        "moodle_executions", sa.Column("operation", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "moodle_executions",
        sa.Column("target_type", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "moodle_executions", sa.Column("target_id", sa.String(length=22), nullable=True)
    )
    op.add_column(
        "moodle_executions",
        sa.Column("moodle_object_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "moodle_executions",
        sa.Column("request_reference", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "moodle_executions", sa.Column("error_code", sa.String(length=100), nullable=True)
    )
    op.add_column(
        "moodle_executions",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_foreign_key(
        "moodle_executions_agent_run_id_fkey",
        "moodle_executions",
        "agent_runs",
        ["agent_run_id"],
        ["id"],
    )
    op.create_foreign_key(
        "moodle_executions_course_id_fkey",
        "moodle_executions",
        "course",
        ["course_id"],
        ["id"],
    )
    op.create_index(
        "ix_moodle_executions_course_id", "moodle_executions", ["course_id"]
    )
    op.create_index(
        "ix_moodle_executions_moodle_object_id",
        "moodle_executions",
        ["moodle_object_id"],
    )
