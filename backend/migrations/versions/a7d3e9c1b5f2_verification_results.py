"""tabel verification_results untuk Moodle verification (BE-21.2)

Hasil verifikasi disimpan per eksekusi: status (enum ``verification_status``
yang sudah ada sejak skema awal), daftar perbedaan yang tersisa, perbedaan yang
sudah diperbaiki, jumlah perbaikan, dan waktu verifikasi. Tabel ``verifications``
dari skema awal tidak diubah.

Revision ID: a7d3e9c1b5f2
Revises: c4f8b2a7e913
Create Date: 2026-11-10 21:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a7d3e9c1b5f2"
down_revision: Union[str, Sequence[str], None] = "c4f8b2a7e913"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    verification_status = postgresql.ENUM(
        "PASS",
        "PARTIAL",
        "FAIL",
        "UNKNOWN",
        name="verification_status",
        create_type=False,
    )
    verification_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "verification_results",
        sa.Column("workflow_id", sa.String(length=22), nullable=False),
        sa.Column("execution_id", sa.String(length=22), nullable=False),
        sa.Column("status", verification_status, nullable=False),
        sa.Column(
            "discrepancies",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "repaired",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("repair_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("repair_rounds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
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
            "repair_count >= 0", name="ck_verification_results_repair_count"
        ),
        sa.CheckConstraint(
            "repair_rounds >= 0", name="ck_verification_results_repair_rounds"
        ),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"]),
        sa.ForeignKeyConstraint(["execution_id"], ["moodle_executions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_verification_results_workflow_id", "verification_results", ["workflow_id"]
    )
    op.create_index(
        "ix_verification_results_execution_id", "verification_results", ["execution_id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_verification_results_execution_id", table_name="verification_results"
    )
    op.drop_index(
        "ix_verification_results_workflow_id", table_name="verification_results"
    )
    op.drop_table("verification_results")
    # Enum ``verification_status`` tetap dipakai tabel ``verifications``.