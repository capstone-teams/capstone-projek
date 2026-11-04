"""drop rps source_markdown

BE-13 mengoreksi BE-05.2: DL-008 menetapkan hasil Docling disimpan sebagai JSON
(``rps.source_document``), sedangkan YAML baru dibentuk oleh BE-08.1 saat
dibutuhkan sebagai input LLM (DL-006). Kolom ``source_markdown`` tidak lagi
dibaca maupun ditulis oleh aplikasi, sehingga dihapus.

Dokumen lama yang hanya memiliki Markdown tidak kehilangan berkas aslinya:
``file_path`` tetap dipertahankan, dan baris tersebut akan dikonversi ulang
secara otomatis ketika ``POST /api/v1/rps/{id}/process`` dipanggil — idempotency
mensyaratkan ``source_document`` terisi. Tidak ada data yang disalin dari
Markdown ke JSON.

Revision ID: e1a7c4b9d2f6
Revises: c8f4a1d27e93
Create Date: 2026-10-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1a7c4b9d2f6'
down_revision: Union[str, Sequence[str], None] = 'c8f4a1d27e93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('rps', 'source_markdown')


def downgrade() -> None:
    """Downgrade schema.

    Kolom dikembalikan sebagai NULL-able: hasil Markdown tidak lagi diproduksi,
    sehingga tidak ada nilai yang dapat diisi ulang. Baris lama yang sempat
    diproses ulang akan tetap kosong pada kolom ini.
    """
    op.add_column(
        'rps',
        sa.Column('source_markdown', sa.Text(), nullable=True),
    )
