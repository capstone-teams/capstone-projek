"""add rps schema_version

Menambahkan kolom ``rps.schema_version`` — versi RPS Structured Data Schema yang
berlaku untuk sebuah dokumen.

Kolom ini adalah bagian dari kunci idempotency BE-05: dokumen dengan
``file_hash`` **dan** ``schema_version`` yang sama tidak diproses ulang, sehingga
kolomnya ``NOT NULL`` (versi kosong akan membuat kunci tersebut ambigu).

``server_default='1.0'`` dipakai untuk mengisi baris yang sudah ada pada database
development. Nilai itu sama dengan ``DEFAULT_SCHEMA_VERSION`` pada
``src/models/rps.py`` dan ``RPS_SCHEMA_VERSION`` pada
``src/schemas/rps_structured.py``; server default tetap dipertahankan sesudahnya
sebagai backstop bagi penulisan yang tidak melalui domain, dan agar model ORM
serta skema database tetap konsisten.

Revision ID: b3c9e14a7f52
Revises: a7d3f1b92c40
Create Date: 2026-10-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3c9e14a7f52'
down_revision: Union[str, Sequence[str], None] = 'a7d3f1b92c40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Panjang kolom mengikuti ``src.models.rps.SCHEMA_VERSION_LENGTH``.
SCHEMA_VERSION_LENGTH = 50
DEFAULT_SCHEMA_VERSION = "1.0"


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'rps',
        sa.Column(
            'schema_version',
            sa.String(length=SCHEMA_VERSION_LENGTH),
            nullable=False,
            server_default=DEFAULT_SCHEMA_VERSION,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('rps', 'schema_version')
