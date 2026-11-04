"""create instructor setup

Menyiapkan penyimpanan setup dosen (BE-10.1): Instructor Profile dan Activity
Configuration (termasuk Additional Prompt).

``instructor_profiles`` sudah dibuat pada migrasi init (BE-02) dengan kolom JSONB
placeholder yang belum pernah dipakai service apa pun. Tabel tersebut kosong,
sehingga kolom placeholder-nya diganti dengan kolom relational yang benar-benar
dipakai domain — nilainya divalidasi per field, jadi bentuknya tidak boleh
bebas (data-model §26).

``activity_configurations`` menyimpan preferensi aktivitas dan additional prompt
per dosen (0..1). Default database mengikuti issue BE-10.1: learning material
aktif, jenis aktivitas lain nonaktif.

Revision ID: d4e7b1a9c632
Revises: e1a7c4b9d2f6
Create Date: 2026-10-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd4e7b1a9c632'
down_revision: Union[str, Sequence[str], None] = 'e1a7c4b9d2f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Kolom placeholder BE-02 yang tidak pernah dipakai; digantikan kolom di bawah.
PLACEHOLDER_COLUMNS = (
    "teaching_style",
    "language",
    "content_preferences",
    "activity_preferences",
    "additional_preferences",
)


def upgrade() -> None:
    """Upgrade schema."""
    for column in PLACEHOLDER_COLUMNS:
        op.drop_column("instructor_profiles", column)

    op.add_column(
        "instructor_profiles",
        sa.Column("teaching_style", sa.Text(), server_default="", nullable=False),
    )
    op.add_column(
        "instructor_profiles",
        sa.Column("expertise", sa.Text(), server_default="", nullable=False),
    )
    op.add_column(
        "instructor_profiles",
        sa.Column("delivery_preference", sa.Text(), server_default="", nullable=False),
    )
    op.add_column(
        "instructor_profiles",
        sa.Column(
            "language_preference", sa.String(length=50), server_default="", nullable=False
        ),
    )

    op.create_table(
        "activity_configurations",
        sa.Column("user_id", sa.String(length=22), nullable=False),
        sa.Column("learning_material", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("learning_resource", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("assignment", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("quiz", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("additional_prompt", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("activity_configurations")

    op.drop_column("instructor_profiles", "language_preference")
    op.drop_column("instructor_profiles", "delivery_preference")
    op.drop_column("instructor_profiles", "expertise")
    op.drop_column("instructor_profiles", "teaching_style")

    op.add_column(
        "instructor_profiles",
        sa.Column(
            "teaching_style",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "instructor_profiles",
        sa.Column("language", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "instructor_profiles",
        sa.Column(
            "content_preferences",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "instructor_profiles",
        sa.Column(
            "activity_preferences",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "instructor_profiles",
        sa.Column(
            "additional_preferences",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
