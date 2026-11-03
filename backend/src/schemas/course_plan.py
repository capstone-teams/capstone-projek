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
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = [
    "CoursePlanActivityType",
    "CoursePlanCourse",
    "CoursePlanIdentity",
    "CoursePlanOutput",
    "CoursePlanResponse",
    "CoursePlanValidationIssue",
    "CoursePlanValidationResult",
    "CoursePlanVersionListResponse",
    "CoursePlanVersionSummary",
    "CoursePlanWeek",
    "PlanRejectRequest",
    "PlanWeekResponse",
    "WEEK_TYPE_VALUES",
]

WORKFLOW_ID_EXAMPLE = "q7RtYx2bM8sLdWfZaKp3nQ"
COURSE_PLAN_ID_EXAMPLE = "5AH7inFLxJDRKEa34saR9c"

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


# --- DTO endpoint review (BE-14.2) -----------------------------------------


class CoursePlanIdentity(BaseModel):
    """Identitas mata kuliah yang ditampilkan pada course plan."""

    title: str = ""
    code: str | None = None
    description: str | None = None


class PlanWeekResponse(BaseModel):
    """Satu minggu pada response course plan."""

    week_number: int
    title: str
    learning_outcomes: list[str] = Field(default_factory=list)
    objectives: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    teaching_methods: list[str] = Field(default_factory=list)
    planned_activities: list[str] = Field(default_factory=list)
    week_type: str = "regular"
    rps_week: int | None = None


class CoursePlanValidationIssue(BaseModel):
    """Satu temuan validasi; ``week`` kosong untuk temuan tingkat rencana."""

    code: str
    week: int | None = None
    message: str


class CoursePlanValidationResult(BaseModel):
    """Hasil validasi yang disimpan bersama versi course plan.

    ``passed`` bernilai ``False`` juga ketika versi belum pernah divalidasi,
    sehingga approve tidak dapat melewati validasi yang belum dijalankan.
    """

    passed: bool = False
    issues: list[CoursePlanValidationIssue] = Field(default_factory=list)


class CoursePlanResponse(BaseModel):
    """Satu versi course plan beserta weekly plan-nya (BE-14.2)."""

    id: str
    workflow_id: str | None = None
    version: int
    status: str
    course: CoursePlanIdentity = Field(default_factory=CoursePlanIdentity)
    weeks: list[PlanWeekResponse] = Field(default_factory=list)
    validation: CoursePlanValidationResult = Field(
        default_factory=CoursePlanValidationResult
    )
    revision_notes: str | None = None
    regeneration_instruction: str | None = None
    prompt_version: str | None = None
    model_name: str | None = None
    created_at: datetime | None = None
    approved_at: datetime | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": COURSE_PLAN_ID_EXAMPLE,
                "workflow_id": WORKFLOW_ID_EXAMPLE,
                "version": 1,
                "status": "DRAFT",
                "course": {"title": "Basis Data", "code": "IF2230"},
                "weeks": [
                    {
                        "week_number": 1,
                        "title": "Pengenalan Basis Data",
                        "learning_outcomes": ["SUB-1"],
                        "objectives": [
                            "Mahasiswa mampu menjelaskan konsep dasar basis data"
                        ],
                        "topics": ["Pengenalan Basis Data"],
                        "teaching_methods": ["Ceramah", "Praktikum"],
                        "planned_activities": ["learning_material"],
                        "week_type": "regular",
                        "rps_week": 1,
                    }
                ],
                "validation": {"passed": True, "issues": []},
                "revision_notes": None,
                "regeneration_instruction": None,
                "prompt_version": "course_planning/v1",
                "model_name": "gpt-4o-mini",
                "created_at": "2026-11-04T08:00:00Z",
                "approved_at": None,
            }
        }
    )


class CoursePlanVersionSummary(BaseModel):
    """Ringkasan satu versi pada riwayat versi course plan."""

    version: int
    status: str
    validation_passed: bool = False
    revision_notes: str | None = None
    created_at: datetime | None = None
    approved_at: datetime | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "version": 2,
                "status": "DRAFT",
                "validation_passed": True,
                "revision_notes": "Perbaiki pembagian materi minggu 5-8.",
                "created_at": "2026-11-04T08:10:00Z",
                "approved_at": None,
            }
        }
    )


class CoursePlanVersionListResponse(BaseModel):
    """Riwayat versi course plan, terbaru lebih dulu."""

    items: list[CoursePlanVersionSummary] = Field(default_factory=list)


class PlanRejectRequest(BaseModel):
    """Body penolakan course plan; catatan revisi wajib diisi."""

    notes: str = Field(
        min_length=1,
        description="Catatan revisi untuk dosen/agent; tidak boleh kosong.",
        examples=["Minggu 8 seharusnya UTS, pindahkan materi ke minggu 9."],
    )
