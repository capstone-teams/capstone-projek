"""Kontrak output Course Plan (BE-14.1, content-schema §8–§9).

Model ini adalah bentuk yang **dihasilkan agent** (BE-15) dan menjadi dasar
penyimpanan versi course plan. Mengikuti Course Plan Schema pada content-schema
§8 — identitas mata kuliah dan daftar minggu — dengan tambahan
``planned_activities`` sesuai issue BE-14.1 dan §9.

Aturan bentuk yang dijaga di sini:

- field di luar kontrak ditolak (``extra="forbid"``), karena output model bahasa
  yang menyimpang harus terlihat sebagai kegagalan validasi, bukan dibuang
  diam-diam;
- nomor minggu positif dan tidak duplikat;
- jenis aktivitas terbatas pada empat jenis Activity Configuration
  (content-schema §10), sehingga rencana tidak dapat meminta aktivitas yang
  tidak dikenal.

``week_type`` dan ``rps_week`` **tidak** diminta dari model: keduanya disalin
dari RPS Analysis saat penyimpanan supaya penanda UTS/UAS dan referensi baris
RPS tidak dapat dikarang agent.
"""

from __future__ import annotations

import enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = [
    "CoursePlanActivityType",
    "CoursePlanCourse",
    "CoursePlanOutput",
    "CoursePlanWeek",
    "WEEK_TYPE_VALUES",
]

#: Jenis minggu yang dikenal, sama dengan jenis minggu RPS (content-schema §6.2).
WEEK_TYPE_VALUES = ("regular", "kuis", "uts", "uas")


class CoursePlanActivityType(str, enum.Enum):
    """Jenis aktivitas yang boleh direncanakan (content-schema §10)."""

    LEARNING_MATERIAL = "learning_material"
    LEARNING_RESOURCE = "learning_resource"
    ASSIGNMENT = "assignment"
    QUIZ = "quiz"


class CoursePlanModel(BaseModel):
    """Base object course plan: kontrak ketat dan teks tanpa spasi tepi."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CoursePlanCourse(CoursePlanModel):
    """Identitas mata kuliah pada rencana (content-schema §8)."""

    title: str = Field(min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=50)
    description: str | None = None


class CoursePlanWeek(CoursePlanModel):
    """Rencana satu minggu (content-schema §9)."""

    week_number: int = Field(ge=1, le=60)
    title: str = Field(min_length=1, max_length=255)
    #: Kode Sub-CPMK yang dicakup minggu ini.
    learning_outcomes: list[str] = Field(default_factory=list)
    #: Tujuan pembelajaran dalam kalimat utuh.
    objectives: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    teaching_methods: list[str] = Field(default_factory=list)
    planned_activities: list[CoursePlanActivityType] = Field(default_factory=list)


class CoursePlanOutput(CoursePlanModel):
    """Course Plan lengkap hasil agent (content-schema §8)."""

    course: CoursePlanCourse
    weeks: list[CoursePlanWeek] = Field(min_length=1)

    @model_validator(mode="after")
    def _reject_duplicate_weeks(self) -> CoursePlanOutput:
        """Nomor minggu duplikat membuat rencana tidak dapat dipetakan ke RPS."""
        seen: set[int] = set()
        duplicates: list[int] = []
        for week in self.weeks:
            if week.week_number in seen:
                duplicates.append(week.week_number)
            seen.add(week.week_number)
        if duplicates:
            raise ValueError(
                f"nomor minggu duplikat: {', '.join(map(str, sorted(duplicates)))}"
            )
        return self
