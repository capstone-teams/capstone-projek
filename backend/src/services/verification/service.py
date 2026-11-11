"""Moodle Verification Service (BE-21.2).

Dipanggil orkestrator setelah eksekusi (tahap ``VERIFYING``, BE-22.1) dan oleh
endpoint verifikasi (BE-22.2). Satu kali verifikasi:

1. memilih eksekusi yang diverifikasi: eksekusi yang diminta, atau eksekusi
   ``FULL`` terakhir yang sudah selesai pada workflow;
2. menyusun kondisi yang diharapkan: section per minggu dari course plan yang
   dieksekusi, dan satu activity untuk setiap operasi konten yang tidak
   ``SKIPPED`` (jenis, minggu, judul konten ``APPROVED``, cmid pada mapping
   BE-04.3);
3. membaca ulang isi course melalui Moodle Integration Layer lalu
   membandingkannya (:func:`~src.services.verification.domain.compare_course`);
4. bila ada perbedaan yang dapat diperbaiki, mapping yang menunjuk objek yang
   sudah tidak ada dibuang lalu operasi terkait dijalankan ulang
   (:meth:`ExecutionService.rerun_operations`), kemudian course dibaca ulang;
   langkah ini diulang paling banyak ``MOODLE_VERIFICATION_MAX_REPAIRS`` kali;
5. hasil akhir disimpan sebagai ``VerificationResult``: status, perbedaan yang
   tersisa, perbedaan yang berhasil diperbaiki, jumlah perbaikan, dan waktu.

Activity yang tidak berasal dari eksekusi (mis. ditambahkan dosen langsung di
Moodle) dilaporkan sebagai ``UNEXPECTED`` dan tidak pernah dihapus. Kegagalan
Moodle saat membaca ulang menghasilkan status ``UNKNOWN`` dengan pesan aman;
credential dan payload mentah tidak pernah disimpan.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.execution_operation import OperationStatus, OperationType
from src.models.moodle_execution import ExecutionScope, ExecutionStatus
from src.models.verification import VerificationStatus
from src.services.course_plan.domain import CoursePlanRecord
from src.services.course_plan.repository import CoursePlanRepository
from src.services.execution.domain import ExecutionRecord
from src.services.execution.errors import (
    EXECUTION_IN_PROGRESS,
    ExecutionNotFoundError,
    ExecutionPreconditionError,
)
from src.services.execution.repository import ExecutionRepository
from src.services.execution.service import (
    MOODLE_FAILURES,
    SECTION_ENTITY_TYPE,
    ExecutionService,
    section_name,
)
from src.services.moodle_assignment_service import ASSIGNMENT_ENTITY_TYPE
from src.services.moodle_error_category import normalize_moodle_error
from src.services.moodle_integration_service import MoodleIntegrationService
from src.services.moodle_mapping_sql import SqlMoodleMappingRepository
from src.services.moodle_page_service import PAGE_ENTITY_TYPE
from src.services.moodle_quiz_service import QUIZ_ENTITY_TYPE
from src.services.moodle_resource_service import RESOURCE_ENTITY_TYPE
from src.services.verification.domain import (
    SECTION_TARGET,
    ActivityExpectation,
    Comparison,
    Discrepancy,
    SectionExpectation,
    VerificationResultRecord,
    compare_course,
    status_for,
)
from src.services.verification.errors import (
    NO_EXECUTION_TO_VERIFY,
    VerificationNotFoundError,
    VerificationPreconditionError,
)
from src.services.verification.repository import VerificationRepository
from src.services.workflow.service import WorkflowService

if TYPE_CHECKING:  # pragma: no cover - hanya untuk type checker
    from src.services.content.repository import ContentRepository

__all__ = ["DEFAULT_MAX_REPAIRS", "VerificationService"]

logger = logging.getLogger(__name__)

#: Batas putaran perbaikan bila ``MOODLE_VERIFICATION_MAX_REPAIRS`` tidak diisi.
DEFAULT_MAX_REPAIRS = 2

#: Jenis operasi konten → tipe entity mapping BE-04.3 yang dipakai operasi BE-12.
MAPPING_ENTITY_BY_OPERATION_TYPE: dict[OperationType, str] = {
    OperationType.LEARNING_MATERIAL: PAGE_ENTITY_TYPE,
    OperationType.LEARNING_RESOURCE: RESOURCE_ENTITY_TYPE,
    OperationType.ASSIGNMENT: ASSIGNMENT_ENTITY_TYPE,
    OperationType.QUIZ: QUIZ_ENTITY_TYPE,
}

#: Eksekusi yang sudah selesai dan dapat diverifikasi.
_FINISHED = (ExecutionStatus.SUCCESS, ExecutionStatus.FAILED)
_ACTIVE = (ExecutionStatus.PENDING, ExecutionStatus.RUNNING)

EmitEvent = Callable[..., Awaitable[None]]


class VerificationService:
    """Read-back, pembandingan, perbaikan terbatas, dan penyimpanan hasil."""

    def __init__(
        self,
        repository: VerificationRepository,
        *,
        executions: ExecutionRepository,
        execution_service: ExecutionService,
        workflow_service: WorkflowService,
        plan_repository: CoursePlanRepository,
        contents: ContentRepository,
        mappings: SqlMoodleMappingRepository,
        moodle: MoodleIntegrationService,
        max_repairs: int = DEFAULT_MAX_REPAIRS,
    ) -> None:
        if max_repairs < 0:
            raise ValueError("max_repairs tidak boleh negatif")
        self._repository = repository
        self._executions = executions
        self._execution_service = execution_service
        self._workflows = workflow_service
        self._plans = plan_repository
        self._contents = contents
        self._mappings = mappings
        self._moodle = moodle
        self._max_repairs = max_repairs

    @classmethod
    def from_session(
        cls,
        session: AsyncSession,
        *,
        moodle: MoodleIntegrationService,
        max_repairs: int | None = None,
    ) -> VerificationService:
        """Bangun service dengan dependency bawaan dan batas perbaikan dari settings."""
        from src.config.settings import settings
        from src.services.content.repository import ContentRepository

        if max_repairs is None:
            max_repairs = settings.moodle_verification_max_repairs
        return cls(
            VerificationRepository(session),
            executions=ExecutionRepository(session),
            execution_service=ExecutionService.from_session(session, moodle=moodle),
            workflow_service=WorkflowService.from_session(session),
            plan_repository=CoursePlanRepository(session),
            contents=ContentRepository(session),
            mappings=SqlMoodleMappingRepository(session),
            moodle=moodle,
            max_repairs=max_repairs,
        )

    # --- Perintah dari orkestrator / route -------------------------------

    async def verify(
        self,
        *,
        workflow_id: str,
        owner_id: str,
        execution_id: str | None = None,
        emit_event: EmitEvent | None = None,
    ) -> VerificationResultRecord:
        """Verifikasi course hasil eksekusi, perbaiki perbedaan, simpan hasilnya.

        Tanpa ``execution_id``, eksekusi ``FULL`` terakhir yang sudah selesai
        yang diverifikasi. Service ini tidak mengubah status workflow; transisi
        ``VERIFYING`` → ``COMPLETED``/``FAILED`` diatur orkestrator berdasarkan
        :attr:`VerificationResultRecord.matches`.

        Verifikasi ditolak ``EXECUTION_IN_PROGRESS`` selama workflow masih
        memiliki eksekusi ``PENDING``/``RUNNING``, karena perbaikan menjalankan
        ulang operasi pada course yang sama.
        """
        workflow = await self._workflows.get_workflow(
            workflow_id=workflow_id, owner_id=owner_id
        )
        await self._reject_running_execution(workflow.id or "")
        execution = await self._resolve_execution(workflow.id or "", execution_id)
        plan = await self._plans.get_by_id(execution.course_plan_id)

        attempted: list[Discrepancy] = []
        repair_count = 0
        rounds = 0
        try:
            comparison = await self._compare(execution, plan)
            while comparison.repairable and rounds < self._max_repairs:
                rounds += 1
                targets = comparison.repairable
                await self._discard_stale_mappings(execution, plan, targets)
                operation_ids = sorted(
                    {item.operation_id for item in targets if item.operation_id}
                )
                await self._execution_service.rerun_operations(
                    execution_id=execution.id or "",
                    operation_ids=operation_ids,
                    emit_event=emit_event,
                )
                repair_count += len(operation_ids)
                attempted.extend(targets)
                execution = await self._executions.get(execution.id or "") or execution
                comparison = await self._compare(execution, plan)
        except MOODLE_FAILURES as exc:
            logger.warning(
                "verifikasi eksekusi %s gagal membaca Moodle: %s", execution.id, exc
            )
            return await self._repository.create(
                VerificationResultRecord(
                    workflow_id=workflow.id or "",
                    execution_id=execution.id or "",
                    status=VerificationStatus.UNKNOWN,
                    verified_at=_utcnow(),
                    repair_count=repair_count,
                    repair_rounds=rounds,
                    error_message=normalize_moodle_error(exc).message,
                )
            )

        record = await self._repository.create(
            VerificationResultRecord(
                workflow_id=workflow.id or "",
                execution_id=execution.id or "",
                status=status_for(comparison.discrepancies),
                verified_at=_utcnow(),
                discrepancies=comparison.discrepancies,
                repaired=_resolved(attempted, comparison.discrepancies),
                repair_count=repair_count,
                repair_rounds=rounds,
                summary=comparison.summary,
            )
        )
        logger.info(
            "verifikasi eksekusi %s workflow %s: %s, %s perbedaan, %s perbaikan",
            execution.id,
            workflow.id,
            record.status.value,
            len(record.discrepancies),
            record.repair_count,
        )
        return record

    async def list_results(
        self, *, workflow_id: str, owner_id: str
    ) -> list[VerificationResultRecord]:
        """Riwayat verifikasi milik workflow dosen yang login, terbaru lebih dulu."""
        workflow = await self._workflows.get_workflow(
            workflow_id=workflow_id, owner_id=owner_id
        )
        return await self._repository.list_for_workflow(workflow.id or "")

    async def get_result(
        self, *, workflow_id: str, owner_id: str, verification_id: str
    ) -> VerificationResultRecord:
        """Satu hasil verifikasi milik workflow dosen yang login."""
        workflow = await self._workflows.get_workflow(
            workflow_id=workflow_id, owner_id=owner_id
        )
        record = await self._repository.get_for_workflow(
            workflow.id or "", verification_id
        )
        if record is None:
            raise VerificationNotFoundError(verification_id)
        return record

    # --- Langkah verifikasi ---------------------------------------------------

    async def _reject_running_execution(self, workflow_id: str) -> None:
        for execution in await self._executions.list_for_workflow(workflow_id):
            if execution.status in _ACTIVE:
                raise ExecutionPreconditionError(
                    EXECUTION_IN_PROGRESS,
                    log_message=(
                        f"verifikasi workflow {workflow_id} ditolak: eksekusi "
                        f"{execution.id} berstatus {execution.status.value}"
                    ),
                )

    async def _resolve_execution(
        self, workflow_id: str, execution_id: str | None
    ) -> ExecutionRecord:
        if execution_id is not None:
            execution = await self._executions.get_for_workflow(
                workflow_id, execution_id
            )
            if execution is None:
                raise ExecutionNotFoundError(execution_id)
            if execution.status not in _FINISHED:
                raise VerificationPreconditionError(
                    NO_EXECUTION_TO_VERIFY,
                    log_message=f"eksekusi {execution_id} berstatus {execution.status.value}",
                )
            return execution
        for execution in await self._executions.list_for_workflow(workflow_id):
            if execution.scope is ExecutionScope.FULL and execution.status in _FINISHED:
                return execution
        raise VerificationPreconditionError(
            NO_EXECUTION_TO_VERIFY,
            log_message=f"workflow {workflow_id} belum memiliki eksekusi FULL yang selesai",
        )

    async def _compare(
        self, execution: ExecutionRecord, plan: CoursePlanRecord | None
    ) -> Comparison:
        sections = await self._expected_sections(execution, plan)
        activities = await self._expected_activities(execution)
        contents = await self._moodle.get_course_contents(execution.moodle_course_id)
        return compare_course(
            contents,
            sections,
            activities,
            report_unexpected=execution.scope is ExecutionScope.FULL,
        )

    async def _expected_sections(
        self, execution: ExecutionRecord, plan: CoursePlanRecord | None
    ) -> list[SectionExpectation]:
        if plan is None:
            return []
        operations = {
            operation.course_plan_week_id: operation
            for operation in execution.operations
            if operation.operation_type is OperationType.SECTION
        }
        expected = []
        for week in plan.weeks:
            operation = operations.get(week.id)
            mapped = (
                await self._mappings.get_moodle_id(SECTION_ENTITY_TYPE, week.id)
                if week.id
                else None
            )
            expected.append(
                SectionExpectation(
                    week_number=week.week_number,
                    name=section_name(week),
                    operation_id=operation.id if operation is not None else None,
                    mapped_section_id=mapped,
                )
            )
        return expected

    async def _expected_activities(
        self, execution: ExecutionRecord
    ) -> list[ActivityExpectation]:
        expected = []
        for operation in execution.operations:
            entity_type = MAPPING_ENTITY_BY_OPERATION_TYPE.get(operation.operation_type)
            if (
                entity_type is None
                or operation.status is OperationStatus.SKIPPED
                or not operation.content_id
                or operation.week_number is None
            ):
                continue
            content = await self._contents.get_by_id(operation.content_id)
            if content is None:
                continue
            key = content.content_key or content.id
            expected.append(
                ActivityExpectation(
                    operation_id=operation.id or "",
                    operation_type=operation.operation_type,
                    week_number=operation.week_number,
                    title=content.title.strip(),
                    mapped_cmid=await self._mappings.get_moodle_id(entity_type, key),
                    recorded_cmid=_as_int(operation.moodle_object_id),
                )
            )
        return expected

    async def _discard_stale_mappings(
        self,
        execution: ExecutionRecord,
        plan: CoursePlanRecord | None,
        discrepancies: tuple[Discrepancy, ...],
    ) -> None:
        """Buang mapping yang menunjuk objek yang tidak ada lagi di course."""
        operations = {operation.id: operation for operation in execution.operations}
        weeks = {week.week_number: week for week in plan.weeks} if plan else {}
        for item in discrepancies:
            if not item.stale_mapping:
                continue
            if item.target == SECTION_TARGET:
                week = weeks.get(item.week_number or -1)
                if week is not None and week.id:
                    await self._mappings.delete(SECTION_ENTITY_TYPE, week.id)
                continue
            operation = operations.get(item.operation_id)
            entity_type = (
                MAPPING_ENTITY_BY_OPERATION_TYPE.get(operation.operation_type)
                if operation
                else None
            )
            if operation is None or entity_type is None or not operation.content_id:
                continue
            content = await self._contents.get_by_id(operation.content_id)
            if content is not None:
                await self._mappings.delete(
                    entity_type, content.content_key or content.id
                )


def _key(item: Discrepancy) -> tuple:
    return (item.type, item.target, item.week_number, item.operation_id)


def _resolved(
    attempted: list[Discrepancy], remaining: tuple[Discrepancy, ...]
) -> tuple[Discrepancy, ...]:
    """Perbedaan yang diperbaiki dan tidak muncul lagi setelah read-back ulang."""
    still_open = {_key(item) for item in remaining}
    resolved: dict[tuple, Discrepancy] = {}
    for item in attempted:
        if _key(item) not in still_open:
            resolved.setdefault(_key(item), item)
    return tuple(resolved.values())


def _as_int(value: str | None) -> int | None:
    try:
        return int(value) if value else None
    except ValueError:
        return None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)