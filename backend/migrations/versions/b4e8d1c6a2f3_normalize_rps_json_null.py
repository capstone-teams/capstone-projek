"""normalisasi nilai kosong RPS menjadi SQL NULL

``source_document`` dan ``structured_data`` menyimpan Python ``None`` sebagai
JSON ``null`` karena tipe JSONB bawaan SQLAlchemy memakai
``none_as_null=False``. Di SQL, JSON ``null`` tetap "NOT NULL", sehingga
``source_document IS NOT NULL`` tidak dapat dipakai sebagai indikator keberadaan
dokumen sumber — query daftar/detail jadi harus membaca JSONB besar itu.

Migrasi ini menormalkan baris lama ke SQL NULL. Mulai sekarang model memakai
``JSONB(none_as_null=True)`` sehingga penulisan berikutnya juga menyimpan SQL
NULL. Aplikasi membaca kedua bentuk sebagai ``None``; tidak ada perubahan
kontrak data.

Revision ID: b4e8d1c6a2f3
Revises: c1a4f7e2b9d3
Create Date: 2026-11-09 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4e8d1c6a2f3"
down_revision: Union[str, Sequence[str], None] = "c1a4f7e2b9d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLUMNS = ("source_document", "structured_data")


def upgrade() -> None:
    """Upgrade schema."""
    for column in _COLUMNS:
        op.execute(
            f"UPDATE rps SET {column} = NULL WHERE {column} = 'null'::jsonb"
        )


def downgrade() -> None:
    """Downgrade schema.

    JSON ``null`` dan SQL NULL sama-sama dibaca sebagai ``None`` oleh aplikasi,
    sehingga tidak perlu mengubah data kembali.
    """
