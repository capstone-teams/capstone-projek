"""Konfigurasi aktivitas dan additional prompt dosen (BE-10.1).

Satu baris per dosen (``user_id`` UNIQUE) — nilai ini adalah default yang dipakai
agent saat menyusun course plan dan konten (PRD FR-011, FR-025, FR-026).

Default kolom: learning material aktif, tiga jenis aktivitas lain nonaktif.
Agent tidak boleh membuat assignment/quiz hanya karena tipenya tersedia; ia harus
mengikuti baris ini (PRD FR-026).
"""

from sqlalchemy import Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel


class ActivityConfiguration(BaseModel):
    __tablename__ = "activity_configurations"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        unique=True,
    )

    learning_material: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    learning_resource: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    assignment: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    quiz: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    #: Instruksi tambahan dosen untuk agent (opsional). Batas panjangnya
    #: dikonfigurasi melalui environment, bukan di-hardcode; lihat
    #: ``Settings.instructor_additional_prompt_max_length``.
    additional_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
