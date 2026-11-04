"""add rps analysis result (BE-08.2)

Menyimpan hasil analisis RPS pada dokumen itu sendiri, sesuai DL-009:

- ``rps.structured_data`` sudah ada dan menjadi bentuk resmi RPS Structured
  Data; migrasi ini menambah ``rps.analyzed_at`` sebagai waktu analisis yang
  menghasilkan data tersebut (design-api §6.4);
- ``rps.workflow_id`` adalah workflow yang menjalankan analisis. BE-08.2
  mengisinya saat analisis dijadwalkan; BE-11.2 memakai kolom yang sama untuk
  workflow orkestrasi pemrosesan + analisis, sehingga endpoint daftar/detail
  membaca satu tempat (design-api §6.5/§6.6);
- nilai ``ANALYZING`` dan ``ANALYZED`` ditambahkan ke native enum ``rps_status``
  (design-api §6.5). Keduanya ditambahkan pada migrasi ini, bukan dengan
  mendefinisikan ulang enum di modul lain.

``ALTER TYPE ... ADD VALUE`` sejak PostgreSQL 12 boleh berjalan di dalam
transaksi migrasi; nilai barunya belum dipakai pada transaksi yang sama.

Revision ID: 7c2f9a41e6b3
Revises: d4e7b1a9c632
Create Date: 2026-10-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c2f9a41e6b3'
down_revision: Union[str, Sequence[str], None] = 'd4e7b1a9c632'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Panjang kolom identifier mengikuti ``src.models.base.ID_LENGTH`` (ShortUUID).
ID_LENGTH = 22


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE rps_status ADD VALUE IF NOT EXISTS 'ANALYZING'")
    op.execute("ALTER TYPE rps_status ADD VALUE IF NOT EXISTS 'ANALYZED'")
    op.add_column(
        'rps',
        sa.Column('analyzed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'rps',
        sa.Column('workflow_id', sa.String(length=ID_LENGTH), nullable=True),
    )
    op.create_index(op.f('ix_rps_workflow_id'), 'rps', ['workflow_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema.

    Nilai enum tidak dapat dihapus satu per satu di PostgreSQL, sehingga tipe
    ``rps_status`` dibentuk ulang tanpa ``ANALYZING``/``ANALYZED``. Baris yang
    terlanjur berstatus analisis dipetakan ke status tahap sebelumnya agar
    migrasi tidak gagal: ``ANALYZING`` → ``PROCESSING``, ``ANALYZED`` →
    ``PROCESSED``.
    """
    op.drop_index(op.f('ix_rps_workflow_id'), table_name='rps')
    op.drop_column('rps', 'workflow_id')
    op.drop_column('rps', 'analyzed_at')

    op.execute("UPDATE rps SET status = 'PROCESSING' WHERE status = 'ANALYZING'")
    op.execute("UPDATE rps SET status = 'PROCESSED' WHERE status = 'ANALYZED'")
    op.execute("ALTER TYPE rps_status RENAME TO rps_status_old")
    op.execute(
        "CREATE TYPE rps_status AS ENUM "
        "('UPLOADED', 'PROCESSING', 'PROCESSED', 'FAILED')"
    )
    op.execute(
        "ALTER TABLE rps ALTER COLUMN status TYPE rps_status "
        "USING status::text::rps_status"
    )
    op.execute("DROP TYPE rps_status_old")
