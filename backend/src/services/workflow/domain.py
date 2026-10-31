"""Representasi domain workflow (BE-11.1).

``WorkflowRecord`` dan ``WorkflowEventRecord`` adalah domain model, bukan entity
persistence: keduanya hanya memuat aturan bentuk dan lifecycle workflow, tanpa
mengetahui tabel, session, maupun SQLAlchemy. Entity tabelnya tetap
``src.models.workflow`` dan ``src.models.workflow_event`` yang diakses melalui
:class:`~src.services.workflow.repository.WorkflowRepository`.

Aturan yang dijaga di sini:

- status hanya boleh bertransisi lewat method lifecycle (orkestrator BE-11.2),
  tidak pernah dengan menulis atribut status secara bebas;
- nama event publik selalu berpola ``WORKFLOW_*`` (design-api §17);
- kemajuan tahap tidak pernah negatif dan tidak melebihi jumlah tahap;
- course target Moodle berupa identifier positif atau kosong.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.models.workflow import WorkflowStatus
from src.models.workflow_event import EventType
from src.services.workflow.errors import (
    WorkflowStateError,
    WorkflowValidationError,
)
from src.services.workflow.validation import (
    normalize_event_name,
    normalize_identifier,
    normalize_message,
    normalize_metadata,
    normalize_moodle_course_id,
    normalize_status,
    normalize_timestamp,
)

__all__ = [
    "API_STATUS_BY_STATUS",
    "STAGE_BY_STATUS",
    "WorkflowEventRecord",
    "WorkflowRecord",
    "api_status",
    "stage_name",
]

# Status lifecycle yang dilaporkan API (design-api §16) dipetakan dari state
# machine internal. Selama sebuah tahap berjalan, API melihat ``RUNNING`` dan
# membaca nama tahapnya dari ``stage_name``; status tahap internal tidak bocor
# ke kontrak (design-api §20).
API_STATUS_BY_STATUS: dict[WorkflowStatus, str] = {
    WorkflowStatus.QUEUED: "QUEUED",
    WorkflowStatus.PROCESSING_RPS: "RUNNING",
    WorkflowStatus.ANALYZING_RPS: "RUNNING",
    WorkflowStatus.PLANNING_COURSE: "RUNNING",
    WorkflowStatus.GENERATING_CONTENT: "RUNNING",
    WorkflowStatus.VALIDATING: "RUNNING",
    WorkflowStatus.WAITING_FOR_REVIEW: "RUNNING",
    WorkflowStatus.EXECUTING_TO_MOODLE: "RUNNING",
    WorkflowStatus.VERIFYING: "RUNNING",
    WorkflowStatus.RETRYING: "RUNNING",
    WorkflowStatus.COMPLETED: "COMPLETED",
    WorkflowStatus.FAILED: "FAILED",
}

# Nama tahap pada response monitoring. Status terminal tidak memiliki tahap
# aktif; riwayat tahap terakhir tersedia pada event workflow.
STAGE_BY_STATUS: dict[WorkflowStatus, str] = {
    WorkflowStatus.PROCESSING_RPS: "rps_processing",
    WorkflowStatus.ANALYZING_RPS: "rps_analysis",
    WorkflowStatus.PLANNING_COURSE: "course_planning",
    WorkflowStatus.GENERATING_CONTENT: "content_generation",
    WorkflowStatus.VALIDATING: "validation",
    WorkflowStatus.WAITING_FOR_REVIEW: "instructor_review",
    WorkflowStatus.EXECUTING_TO_MOODLE: "moodle_execution",
    WorkflowStatus.VERIFYING: "verification",
    WorkflowStatus.RETRYING: "retrying",
}

TERMINAL_STATUSES = frozenset({WorkflowStatus.COMPLETED, WorkflowStatus.FAILED})


def api_status(status: WorkflowStatus) -> str:
    """Status lifecycle yang dilaporkan API untuk sebuah status internal."""
    return API_STATUS_BY_STATUS[status]


def stage_name(status: WorkflowStatus) -> str | None:
    """Nama tahap aktif, atau ``None`` bila workflow queued/terminal."""
    return STAGE_BY_STATUS.get(status)


@dataclass(kw_only=True, slots=True)
class WorkflowRecord:
    """Satu workflow beserta state machine-nya.

    ``progress_completed``/``progress_total`` menggambarkan run terakhir. Run
    baru (mis. reanalyze pada workflow yang sama) mengulang hitungannya, karena
    API memonitor kemajuan pekerjaan yang sedang berjalan — bukan akumulasi
    seluruh riwayat workflow.
    """

    owner_id: str
    rps_id: str
    status: WorkflowStatus = WorkflowStatus.QUEUED
    id: str | None = None
    moodle_course_id: int | None = None
    model_name: str | None = None
    progress_completed: int = 0
    progress_total: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        self.owner_id = _require_identifier(self.owner_id, "owner_id")
        self.rps_id = _require_identifier(self.rps_id, "rps_id")
        self.id = normalize_identifier(self.id)
        self.status = normalize_status(self.status)
        self.moodle_course_id = normalize_moodle_course_id(self.moodle_course_id)
        self.model_name = _normalize_model_name(self.model_name)
        self.progress_completed = _normalize_progress(
            self.progress_completed, "progress_completed"
        )
        self.progress_total = _normalize_progress(
            self.progress_total, "progress_total"
        )
        if self.progress_completed > self.progress_total and self.progress_total:
            raise WorkflowValidationError(
                "progress_completed", "tidak boleh melebihi progress_total"
            )
        self.started_at = normalize_timestamp(self.started_at, "started_at")
        self.completed_at = normalize_timestamp(self.completed_at, "completed_at")

    @classmethod
    def create(
        cls,
        *,
        owner_id: str,
        rps_id: str,
        id: str | None = None,
        progress_total: int = 0,
        model_name: str | None = None,
    ) -> WorkflowRecord:
        """Workflow baru yang menunggu dikerjakan orkestrator."""
        return cls(
            id=id,
            owner_id=owner_id,
            rps_id=rps_id,
            status=WorkflowStatus.QUEUED,
            progress_total=progress_total,
            model_name=model_name,
        )

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    @property
    def is_active(self) -> bool:
        """Workflow sedang berjalan (bukan queued/terminal)."""
        return not self.is_terminal and self.status is not WorkflowStatus.QUEUED

    def begin_run(
        self,
        *,
        total: int,
        model_name: str | None = None,
        at: datetime | None = None,
    ) -> None:
        """Mulai satu run: reset kemajuan dan catat model yang dipakai.

        Boleh dipanggil pada workflow yang sudah ``COMPLETED``/``FAILED``:
        reanalyze memakai workflow yang sama dan memulai run baru dari tahap
        analisis (issue BE-11.2).
        """
        self.progress_total = _normalize_progress(total, "progress_total")
        self.progress_completed = 0
        self.model_name = _normalize_model_name(model_name)
        if self.started_at is None:
            # Waktu mulai adalah waktu run pertama; reanalyze tidak mengubahnya.
            self.started_at = normalize_timestamp(at, "started_at") or _utcnow()
        self.completed_at = None

    def enter_stage(self, status: WorkflowStatus) -> None:
        """Masuk ke sebuah tahap kerja.

        Transisi dari status terminal diperbolehkan hanya sebagai bagian dari
        run baru (``begin_run`` sudah dipanggil sebelumnya).
        """
        target = normalize_status(status)
        if target in TERMINAL_STATUSES or target is WorkflowStatus.QUEUED:
            raise WorkflowStateError(
                f"status {target.value} bukan tahap pekerjaan"
            )
        self.status = target
        self.completed_at = None

    def complete_stage(self) -> None:
        """Satu tahap selesai; kemajuan bertambah tanpa melewati total."""
        if not self.is_active:
            raise WorkflowStateError(
                f"workflow {self.id} tidak sedang mengerjakan tahap "
                f"(status: {self.status.value})"
            )
        if self.progress_total:
            self.progress_completed = min(
                self.progress_completed + 1, self.progress_total
            )
        else:
            self.progress_completed += 1

    def mark_retrying(self) -> None:
        """Tahap aktif sedang mencoba ulang setelah kegagalan yang dapat dipulihkan."""
        if not self.is_active:
            raise WorkflowStateError(
                f"workflow {self.id} tidak dapat retry dari status {self.status.value}"
            )
        self.status = WorkflowStatus.RETRYING

    def resume_stage(self, status: WorkflowStatus) -> None:
        """Kembali ke tahap kerja setelah percobaan ulang dimulai."""
        if self.status is not WorkflowStatus.RETRYING:
            return
        self.enter_stage(status)

    def complete_run(self, *, at: datetime | None = None) -> None:
        """Seluruh tahap selesai; workflow mencapai status akhir sukses."""
        self.status = WorkflowStatus.COMPLETED
        self.completed_at = normalize_timestamp(at, "completed_at") or _utcnow()

    def fail_run(self, *, at: datetime | None = None) -> None:
        """Workflow berhenti karena kegagalan yang tidak dapat dipulihkan."""
        self.status = WorkflowStatus.FAILED
        self.completed_at = normalize_timestamp(at, "completed_at") or _utcnow()

    def set_moodle_course_id(self, moodle_course_id: int | None) -> None:
        """Simpan course target Moodle (``None`` mengosongkannya)."""
        self.moodle_course_id = normalize_moodle_course_id(moodle_course_id)

    def __repr__(self) -> str:
        return (
            f"WorkflowRecord(id={self.id!r}, owner_id={self.owner_id!r}, "
            f"rps_id={self.rps_id!r}, status={self.status.value!r}, "
            f"progress={self.progress_completed}/{self.progress_total}, "
            f"moodle_course_id={self.moodle_course_id!r})"
        )


@dataclass(kw_only=True, slots=True)
class WorkflowEventRecord:
    """Satu kejadian workflow yang siap disimpan atau baru dibaca.

    ``metadata`` tidak boleh memuat credential, API key, isi prompt, maupun
    chain-of-thought (design-api §17; data-model §16).
    """

    workflow_id: str
    event_type: EventType
    event: str
    stage: str | None = None
    message: str | None = None
    metadata_: dict | None = field(default=None, repr=False)
    id: str | None = None
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        self.workflow_id = _require_identifier(self.workflow_id, "workflow_id")
        self.event_type = _normalize_event_type(self.event_type)
        self.event = normalize_event_name(self.event)
        self.stage = _normalize_stage(self.stage)
        self.message = normalize_message(self.message)
        self.metadata_ = normalize_metadata(self.metadata_)
        self.id = normalize_identifier(self.id)
        self.created_at = normalize_timestamp(self.created_at, "created_at")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_event_type(value: object) -> EventType:
    if isinstance(value, EventType):
        return value
    if isinstance(value, str):
        try:
            return EventType(value.strip().upper())
        except ValueError as exc:
            raise WorkflowValidationError(
                "event_type", "bukan kategori event yang dikenal"
            ) from exc
    raise WorkflowValidationError("event_type", "wajib berupa EventType")


def _normalize_stage(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise WorkflowValidationError("stage", "harus berupa teks atau None")
    stage = value.strip().lower()
    if not stage:
        return None
    if not re.fullmatch(r"[a-z][a-z0-9_]*", stage):
        raise WorkflowValidationError(
            "stage", "hanya boleh huruf kecil, angka, dan garis bawah"
        )
    if len(stage) > 100:
        raise WorkflowValidationError("stage", "maksimal 100 karakter")
    return stage


def _normalize_model_name(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise WorkflowValidationError("model_name", "harus berupa teks atau None")
    name = value.strip()
    if not name:
        return None
    if len(name) > 255:
        raise WorkflowValidationError("model_name", "maksimal 255 karakter")
    return name


def _normalize_progress(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorkflowValidationError(field_name, "harus berupa bilangan bulat")
    if value < 0:
        raise WorkflowValidationError(field_name, "tidak boleh negatif")
    return value


def _require_identifier(value: object, field_name: str) -> str:
    identifier = normalize_identifier(value)
    if identifier is None:
        raise WorkflowValidationError(field_name, "wajib diisi")
    return identifier
