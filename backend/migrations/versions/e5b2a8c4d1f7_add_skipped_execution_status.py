"""tambah status SKIPPED pada moodle_executions

``ExecutionStatus`` (BE-16.1) membutuhkan status ``SKIPPED`` untuk eksekusi yang
tidak memiliki operasi untuk diterapkan ke Moodle. Enum PostgreSQL
``moodle_execution_status`` belum memuat nilai tersebut.

Downgrade membuat ulang tipe enum tanpa ``SKIPPED`` karena PostgreSQL tidak
mendukung penghapusan nilai enum. Baris berstatus ``SKIPPED`` diubah menjadi
``SUCCESS`` (tidak ada operasi yang gagal) sebelum tipe lama dipasang kembali.

Revision ID: e5b2a8c4d1f7
Revises: b4e8d1c6a2f3
Create Date: 2026-11-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5b2a8c4d1f7"
down_revision: Union[str, Sequence[str], None] = "b4e8d1c6a2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PREVIOUS_VALUES = ("PENDING", "RUNNING", "SUCCESS", "FAILED", "BLOCKED", "RETRYING")


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE moodle_execution_status ADD VALUE IF NOT EXISTS 'SKIPPED'")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("UPDATE moodle_executions SET status = 'SUCCESS' WHERE status = 'SKIPPED'")
    op.execute("ALTER TYPE moodle_execution_status RENAME TO moodle_execution_status_old")
    values = ", ".join(f"'{value}'" for value in _PREVIOUS_VALUES)
    op.execute(f"CREATE TYPE moodle_execution_status AS ENUM ({values})")
    op.execute(
        "ALTER TABLE moodle_executions ALTER COLUMN status TYPE moodle_execution_status "
        "USING status::text::moodle_execution_status"
    )
    op.execute("DROP TYPE moodle_execution_status_old")