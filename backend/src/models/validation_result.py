"""Entity ValidationResult — hasil validasi satu konten (BE-19.1).

``target_type``/``target_id`` adalah referensi polimorfik (course plan, content,
activity, eksekusi Moodle), sehingga tidak memakai satu foreign key. Untuk
konten hasil generation, ``target_type`` bernilai ``CONTENT`` (tabel
``contents``) atau ``ACTIVITY`` (tabel ``activities``).

``agent_run_id`` boleh kosong: generation dan validasi konten (BE-19.3) berjalan
sebagai tahap workflow tanpa selalu membuat ``AgentRun``. ``retry_count``
mencatat berapa kali Retry/Fix dijalankan sebelum hasil ini (BE-20.3), dan
``validated_at`` adalah waktu validasi dilakukan.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel


class ValidationTargetType(str, enum.Enum):
    COURSE_PLAN = "COURSE_PLAN"
    CONTENT = "CONTENT"
    ACTIVITY = "ACTIVITY"
    MOODLE_EXECUTION = "MOODLE_EXECUTION"


class ValidationStatus(str, enum.Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class ValidationResult(BaseModel):
    __tablename__ = "validation_results"

    agent_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_runs.id"),
        nullable=True,
        index=True,
    )

    # Polymorphic reference (Course Plan / Content / Activity / Moodle
    # Execution), so intentionally not a single-table foreign key.
    target_type: Mapped[ValidationTargetType] = mapped_column(
        Enum(ValidationTargetType, name="validation_target_type"),
        nullable=False,
    )

    target_id: Mapped[str] = mapped_column(
        nullable=False,
        index=True,
    )

    status: Mapped[ValidationStatus] = mapped_column(
        Enum(ValidationStatus, name="validation_status"),
        nullable=False,
    )

    checks: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    score: Mapped[float | None] = mapped_column(
        Numeric,
        nullable=True,
    )

    errors: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    warnings: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
