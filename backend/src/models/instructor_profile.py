"""Preferensi penyampaian dosen (BE-10.1).

Satu baris per dosen (``user_id`` UNIQUE). Kolomnya sengaja kolom relational,
bukan JSONB: nilainya dibaca ulang utuh sebagai konteks agent dan divalidasi per
field (lihat ``src.services.instructor``), sehingga bentuknya harus stabil
(data-model §26).

Field mengikuti kontrak design-api §7 (BE-06.4/BE-10.2): gaya mengajar
(``teaching_style``), keahlian (``expertise`` — satu deskripsi teks, bukan
daftar), preferensi penyampaian (``delivery_preference``), dan bahasa
(``language_preference``).

Setup dosen **tidak** menggantikan informasi akademik RPS (PRD FR-010): nilainya
hanya memengaruhi gaya penyajian hasil generation.
"""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel

# Batas panjang nilai teks. Dipakai juga oleh validasi domain
# (``src.services.instructor.domain``) supaya nilai yang lolos validasi tidak
# ditolak database.
MAX_TEACHING_STYLE_LENGTH = 2000
MAX_EXPERTISE_LENGTH = 2000
MAX_DELIVERY_PREFERENCE_LENGTH = 2000
MAX_LANGUAGE_PREFERENCE_LENGTH = 50


class InstructorProfile(BaseModel):
    __tablename__ = "instructor_profiles"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        unique=True,
    )

    #: Gaya mengajar yang diinginkan dosen (bebas teks).
    teaching_style: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default="",
    )

    #: Keahlian/bidang dosen, mis. ``"Rekayasa Perangkat Lunak"``.
    expertise: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default="",
    )

    #: Preferensi penyampaian (kedalaman penjelasan, contoh, struktur).
    delivery_preference: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default="",
    )

    #: Bahasa pengantar materi, mis. ``"Bahasa Indonesia"``.
    language_preference: Mapped[str] = mapped_column(
        String(MAX_LANGUAGE_PREFERENCE_LENGTH),
        nullable=False,
        default="",
        server_default="",
    )
