"""Entity CoursePlanWeek — WeeklyPlan pada issue BE-14.1.

Satu baris adalah rencana satu minggu. Struktur kolom mengikuti Course Plan
Week schema (content-schema §9) ditambah penanda minggu UTS/UAS dan referensi
baris rencana mingguan RPS, sehingga rencana dapat dilacak kembali ke RPS.

``learning_outcomes`` menyimpan **kode** Sub-CPMK yang dipakai minggu tersebut
(issue BE-14.1: "kode Sub-CPMK"); daftar tujuan pembelajarannya ada pada
``objectives``. Kolom ``methods`` adalah metode pembelajaran dan
``planned_activities`` berisi jenis aktivitas yang direncanakan
(``learning_material``/``learning_resource``/``assignment``/``quiz``).
"""

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel

#: Nilai ``week_type`` yang dikenal, sama dengan jenis minggu RPS
#: (``src.schemas.rps_structured.RPSWeekType``) tanpa mengimpor layer schema.
WEEK_TYPES = ("regular", "kuis", "uts", "uas")


class CoursePlanWeek(BaseModel):
    __tablename__ = "course_plan_weeks"
    __table_args__ = (
        UniqueConstraint(
            "course_plan_id", "week_number", name="uq_course_plan_weeks_plan_week"
        ),
        CheckConstraint("week_number >= 1", name="ck_course_plan_weeks_week_number"),
        CheckConstraint(
            "week_type IN ('regular', 'kuis', 'uts', 'uas')",
            name="ck_course_plan_weeks_week_type",
        ),
    )

    course_plan_id: Mapped[str] = mapped_column(
        ForeignKey("course_plans.id"),
        nullable=False,
        index=True,
    )

    week_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Kode Sub-CPMK yang dicakup minggu ini.
    learning_outcomes: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Tujuan pembelajaran (kalimat), terpisah dari kode Sub-CPMK.
    objectives: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    topics: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    methods: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    assessment: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Rencana aktivitas minggu; jenis yang tidak aktif pada Activity
    # Configuration tidak boleh muncul di sini (validasi BE-14.3).
    planned_activities: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # ``regular``/``kuis``/``uts``/``uas`` — minggu UTS/UAS tidak memuat materi
    # baru (content-schema §9; validasi BE-15.1).
    week_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="regular",
        server_default="regular",
    )

    # Baris rencana mingguan RPS yang menjadi acuan minggu ini.
    rps_week: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    metadata_: Mapped[dict | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )
