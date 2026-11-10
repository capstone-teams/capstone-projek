"""content_id execution_operations menjadi referensi polimorfik

Cakupan ``FULL`` (BE-21.1) mengeksekusi empat jenis konten. Learning material
dan resource disimpan di tabel ``contents``, sedangkan assignment dan quiz di
``activities`` (BE-19.1), sehingga satu foreign key ke ``contents`` tidak bisa
menampung semuanya. ``content_id`` disimpan sebagai referensi polimorfik tanpa
foreign key, sama seperti ``verifications.target_id``.

Downgrade memasang kembali foreign key ke ``contents``; baris yang menunjuk ke
``activities`` dikosongkan lebih dulu supaya pemasangan constraint tidak gagal.

Revision ID: c4f8b2a7e913
Revises: e5b2a8c4d1f7
Create Date: 2026-11-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4f8b2a7e913"
down_revision: Union[str, Sequence[str], None] = "e5b2a8c4d1f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CONSTRAINT = "execution_operations_content_id_fkey"


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(_CONSTRAINT, "execution_operations", type_="foreignkey")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "UPDATE execution_operations SET content_id = NULL "
        "WHERE content_id IS NOT NULL "
        "AND content_id NOT IN (SELECT id FROM contents)"
    )
    op.create_foreign_key(
        _CONSTRAINT,
        "execution_operations",
        "contents",
        ["content_id"],
        ["id"],
    )
