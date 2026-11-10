"""Representasi domain eksekusi Moodle (BE-16.1/BE-17.1).

Dataclass di sini adalah domain model, bukan entity persistence: bentuk yang
dibaca/ditulis service dan route, tanpa SQLAlchemy. Entity tabelnya tetap
``src.models.moodle_execution`` dan ``src.models.execution_operation`` yang
diakses melalui :class:`~src.services.execution.repository.ExecutionRepository`.

Aturan yang dijaga di sini:

- satu eksekusi selalu terikat pada workflow dan satu versi course plan;
- operasi yang sudah berhasil (atau dilewati) tidak dijalankan ulang; hanya
  operasi gagal yang diulang pada eksekusi yang sama;
- ringkasan hasil dihitung dari status operasi, bukan disimpan terpisah.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.models.execution_operation import OperationStatus, OperationType
from src.models.moodle_execution import ExecutionScope, ExecutionStatus

__all__ = [
    "ExecutionOperationRecord",
    "ExecutionRecord",
    "ExecutionSummary",
    "PlannedOperation",
]


@dataclass(frozen=True, kw_only=True)
class PlannedOperation:
    """Operasi yang akan dibuat bersama sebuah eksekusi baru."""

    operation_type: OperationType
    idempotency_key: str
    course_plan_week_id: str | None = None
    content_id: str | None = None
    #: ``SKIPPED`` untuk jenis konten nonaktif / belum disetujui (cakupan FULL).
    status: OperationStatus = OperationStatus.PENDING
    error_message: str | None = None


@dataclass(frozen=True, kw_only=True)
class ExecutionOperationRecord:
    """Satu operasi eksekusi beserta hasilnya."""

    execution_id: str
    operation_type: OperationType
    idempotency_key: str
    status: OperationStatus = OperationStatus.PENDING
    course_plan_week_id: str | None = None
    content_id: str | None = None
    moodle_object_id: str | None = None
    error_message: str | None = None
    retry_count: int = 0
    #: Nomor minggu course plan (di-join saat dibaca) untuk tampilan per minggu.
    week_number: int | None = None
    id: str | None = None


@dataclass(frozen=True, kw_only=True)
class ExecutionSummary:
    """Ringkasan hasil satu eksekusi (jumlah per status operasi)."""

    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0


@dataclass(frozen=True, kw_only=True)
class ExecutionRecord:
    """Satu run eksekusi beserta operasinya."""

    workflow_id: str
    course_plan_id: str
    moodle_course_id: int
    scope: ExecutionScope = ExecutionScope.STRUCTURE
    status: ExecutionStatus = ExecutionStatus.PENDING
    id: str | None = None
    error_message: str | None = None
    readback: dict | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    operations: tuple[ExecutionOperationRecord, ...] = field(default_factory=tuple)

    @property
    def summary(self) -> ExecutionSummary:
        """Jumlah berhasil, gagal, dan dilewati pada operasi eksekusi ini."""
        counts = {status: 0 for status in OperationStatus}
        for operation in self.operations:
            counts[operation.status] += 1
        return ExecutionSummary(
            total=len(self.operations),
            success=counts[OperationStatus.SUCCESS],
            failed=counts[OperationStatus.FAILED],
            skipped=counts[OperationStatus.SKIPPED],
        )

    @property
    def failed_operations(self) -> tuple[ExecutionOperationRecord, ...]:
        return tuple(
            operation
            for operation in self.operations
            if operation.status is OperationStatus.FAILED
        )
