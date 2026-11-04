"""add rps source_document and processing duration

Menyempurnakan pipeline konversi BE-05.2 sesuai issue #98:

- ``rps.source_document`` (JSONB) — representasi penuh dokumen hasil konversi
  Docling (DoclingDocument sebagai JSON), mempertahankan teks, heading, tabel,
  dan nomor halaman. Disimpan agar tahap pemetaan field (BE-08) tidak perlu
  menjalankan Docling ulang. Artefak berkas di storage tetap ditulis, karena
  berkas besar lebih murah dilayani dari filesystem.
- ``rps.processing_duration_ms`` — durasi konversi untuk evaluasi performa.
  ``NULL`` berarti dokumen belum pernah selesai diproses.
- ``rps.processing_error_code`` dan ``rps.processing_error`` — kegagalan
  pemrosesan. Karena konversi berjalan di background (design-api §6.3),
  kegagalan tidak dapat muncul pada response request: client membacanya lewat
  polling ketika statusnya ``FAILED``. Kolomnya hanya memuat kode error
  (design-api §18) dan alasan publik yang aman ditampilkan; penyebab teknisnya
  tetap hanya ada di log server-side.

Selain itu, ``server_default`` kolom ``rps.schema_version`` dinaikkan ke ``2.0``
mengikuti ``RPS_SCHEMA_VERSION`` pada ``src/schemas/rps_structured.py``. Baris
yang sudah ada **tidak** ikut berubah: dokumen yang diproses dengan skema 1.0
tetap tercatat 1.0, dan justru itulah yang membuat pemrosesan ulang terdeteksi
perlu ketika skema naik.

Revision ID: c8f4a1d27e93
Revises: b3c9e14a7f52
Create Date: 2026-10-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c8f4a1d27e93'
down_revision: Union[str, Sequence[str], None] = 'b3c9e14a7f52'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Mengikuti ``src.models.rps``; kolom versi skema tidak berubah tipe, hanya
# nilai bawaannya yang naik.
SCHEMA_VERSION_LENGTH = 50
PREVIOUS_SCHEMA_VERSION = "1.0"
DEFAULT_SCHEMA_VERSION = "2.0"


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'rps',
        sa.Column('source_document', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        'rps',
        sa.Column('processing_duration_ms', sa.Integer(), nullable=True),
    )
    op.add_column(
        'rps',
        sa.Column('processing_error_code', sa.String(length=50), nullable=True),
    )
    op.add_column(
        'rps',
        sa.Column('processing_error', sa.Text(), nullable=True),
    )
    op.alter_column(
        'rps',
        'schema_version',
        existing_type=sa.String(length=SCHEMA_VERSION_LENGTH),
        existing_nullable=False,
        server_default=DEFAULT_SCHEMA_VERSION,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'rps',
        'schema_version',
        existing_type=sa.String(length=SCHEMA_VERSION_LENGTH),
        existing_nullable=False,
        server_default=PREVIOUS_SCHEMA_VERSION,
    )
    op.drop_column('rps', 'processing_error')
    op.drop_column('rps', 'processing_error_code')
    op.drop_column('rps', 'processing_duration_ms')
    op.drop_column('rps', 'source_document')
