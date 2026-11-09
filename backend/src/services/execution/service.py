"""Eksekusi struktur course plan ke Moodle (BE-16.2, tahap BE-17.1).

Service ini menjawab "operasi apa yang harus dijalankan, dan bagaimana hasilnya
dicatat?" untuk cakupan ``STRUCTURE`` (DL-012). Urutan tahap workflow ada di
:mod:`src.services.workflow.orchestrator`; akses tabel ada di
:class:`~src.services.execution.repository.ExecutionRepository`.

Alur satu run:

1. prasyarat diperiksa (course plan ``APPROVED``, course target tersimpan,
   Moodle terjangkau, tidak ada proses lain pada workflow yang sama);
2. satu :class:`~src.models.execution_operation.ExecutionOperation` ``SECTION``
   per minggu dibuat berstatus ``PENDING``;
3. setiap operasi menjalankan ``save_section`` (nama ``Minggu N - judul``,
   ringkasan berisi tujuan pembelajaran, topik, dan Sub-CPMK; minggu UTS/UAS
   diberi penanda). Section yang sudah tercatat pada tabel mapping BE-04.3
   diperbarui berdasarkan ID-nya; selain itu dicari berdasarkan nomor minggu,
   sehingga eksekusi kedua memperbarui section yang sama alih-alih menambah
   section baru;
4. kegagalan satu operasi tidak menghentikan operasi minggu lain; status
   eksekusi ``FAILED`` bila ada operasi gagal;
5. struktur course dibaca ulang dari Moodle dan ringkasannya disimpan pada
   eksekusi (jumlah, urutan, dan nama section);
6. retry hanya mengulang operasi ``FAILED`` pada eksekusi yang sama.

Seluruh kegagalan Moodle diterjemahkan menjadi pesan publik yang aman; payload
mentah dan credential tidak pernah disimpan pada eksekusi maupun event.
"""

from __future__ import annotations

import html
import logging
import re
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.course_plan import CoursePlanStatus
from src.models.execution_operation import OperationStatus, OperationType
from src.models.moodle_execution import ExecutionScope, ExecutionStatus
from src.services.course_plan.domain import CoursePlanRecord, CoursePlanWeekRecord
from src.services.course_plan.repository import CoursePlanRepository
from src.services.execution.domain import (
    ExecutionOperationRecord,
    ExecutionRecord,
    PlannedOperation,
)
from src.services.execution.errors import (
    EXECUTION_IN_PROGRESS,
    MOODLE_TARGET_NOT_SET,
    MOODLE_UNAVAILABLE,
    PLAN_NOT_APPROVED,
    ExecutionFailedError,
    ExecutionNotFoundError,
    ExecutionPreconditionError,
    ExecutionStateError,
)
from src.services.execution.repository import ExecutionRepository
from src.services.moodle_adapter_exceptions import MoodleIntegrationError
from src.services.moodle_error_category import normalize_moodle_error
from src.services.moodle_exceptions import MoodleError
from src.services.moodle_integration_service import MoodleIntegrationService
from src.services.moodle_mapping import DuplicateMappingError, MoodleMapping
from src.services.moodle_mapping_sql import SqlMoodleMappingRepository
from src.services.workflow.domain import WorkflowRecord
from src.services.workflow.service import WorkflowService

__all__ = ["EVENT_MOODLE_OPERATION", "ExecutionService", "section_name", "section_summary"]

logger = logging.getLogger(__name__)

#: Nama event publik per operasi Moodle (design-api §17: selalu ``WORKFLOW_*``).
EVENT_MOODLE_OPERATION = "WORKFLOW_MOODLE_OPERATION"

#: Tipe entity mapping untuk section minggu (sumber idempotency BE-04.3).
SECTION_ENTITY_TYPE = "course_plan_week"

#: Kegagalan yang berasal dari Moodle (bukan bug aplikasi).
MOODLE_FAILURES = (MoodleError, MoodleIntegrationError)

EmitEvent = Callable[..., Awaitable[None]]


#: Penanda minggu ujian pada nama section (``week_type`` course plan).
EXAM_MARKERS = {"uts": "UTS", "uas": "UAS"}
EXAM_LABELS = {
    "uts": "Ujian Tengah Semester (UTS)",
    "uas": "Ujian Akhir Semester (UAS)",
}

#: Batas panjang nama section Moodle (kolom ``course_sections.name``).
SECTION_NAME_MAX_LENGTH = 255


def section_name(week: CoursePlanWeekRecord) -> str:
    """Nama section Moodle untuk satu minggu, mis. ``Minggu 3 - Relasi Tabel``.

    Minggu UTS/UAS diberi akhiran ``(UTS)``/``(UAS)`` bila judulnya belum
    memuat penanda tersebut. Judul yang terlalu panjang dipotong tanpa
    menghilangkan penanda.
    """
    prefix = f"Minggu {week.week_number} - "
    title = " ".join(week.title.split())
    marker = EXAM_MARKERS.get(week.week_type)
    suffix = ""
    if marker and not re.search(rf"\b{marker}\b", title, flags=re.IGNORECASE):
        suffix = f" ({marker})"
    room = SECTION_NAME_MAX_LENGTH - len(prefix) - len(suffix)
    if len(title) > room:
        title = title[: room - 1].rstrip() + "…"
    return f"{prefix}{title}{suffix}"


def section_summary(week: CoursePlanWeekRecord) -> str:
    """Ringkasan HTML section: penanda ujian, tujuan, topik, dan Sub-CPMK minggu."""
    parts: list[str] = []
    label = EXAM_LABELS.get(week.week_type)
    if label:
        parts.append(f"<p><strong>{label}</strong></p>")
    for heading, items in (
        ("Tujuan Pembelajaran", week.objectives),
        ("Topik", week.topics),
    ):
        cleaned = [item.strip() for item in items if item and item.strip()]
        if cleaned:
            listed = "".join(f"<li>{html.escape(item)}</li>" for item in cleaned)
            parts.append(f"<p><strong>{heading}</strong></p><ul>{listed}</ul>")
    codes = [code.strip() for code in week.learning_outcomes if code and code.strip()]
    if codes:
        parts.append(
            f"<p><strong>Sub-CPMK:</strong> {html.escape(', '.join(codes))}</p>"
        )
    return "".join(parts)


class ExecutionService:
    """Operasi eksekusi Moodle di atas satu ``AsyncSession``."""

    def __init__(
        self,
        repository: ExecutionRepository,
        *,
        workflow_service: WorkflowService,
        plan_repository: CoursePlanRepository,
        moodle: MoodleIntegrationService,
        mappings: SqlMoodleMappingRepository,
    ) -> None:
        self._repository = repository
        self._workflows = workflow_service
        self._plans = plan_repository
        self._moodle = moodle
        self._mappings = mappings

    @classmethod
    def from_session(
        cls, session: AsyncSession, *, moodle: MoodleIntegrationService
    ) -> ExecutionService:
        """Bangun service dengan dependency bawaan."""
        return cls(
            ExecutionRepository(session),
            workflow_service=WorkflowService.from_session(session),
            plan_repository=CoursePlanRepository(session),
            moodle=moodle,
            mappings=SqlMoodleMappingRepository(session),
        )

    # --- Perintah dari route / orkestrator --------------------------------

    async def start_structure(
        self, *, workflow_id: str, owner_id: str
    ) -> ExecutionRecord:
        """Mulai satu eksekusi ``STRUCTURE`` baru berstatus ``PENDING``.

        Prasyarat diperiksa **sebelum** workflow diklaim, sehingga penolakan
        tidak meninggalkan workflow pada status eksekusi. Klaim status bersifat
        atomik: dua permintaan bersamaan hanya menghasilkan satu eksekusi.
        """
        workflow = await self._workflows.get_workflow(
            workflow_id=workflow_id, owner_id=owner_id
        )
        plan = await self._require_prerequisites(workflow)

        claimed = await self._workflows.claim_execution(
            workflow_id=workflow.id or "", owner_id=owner_id
        )
        if claimed is None:
            raise ExecutionPreconditionError(
                EXECUTION_IN_PROGRESS,
                log_message=f"workflow {workflow.id} sedang menjalankan proses lain",
            )

        return await self._repository.create(
            workflow_id=workflow.id or "",
            course_plan_id=plan.id,
            moodle_course_id=workflow.moodle_course_id or 0,
            scope=ExecutionScope.STRUCTURE,
            operations=tuple(_planned_sections(workflow, plan)),
        )

    async def retry_failed(
        self, *, workflow_id: str, owner_id: str, execution_id: str
    ) -> ExecutionRecord:
        """Klaim ulang workflow untuk mengulang operasi gagal pada eksekusi sama."""
        workflow = await self._workflows.get_workflow(
            workflow_id=workflow_id, owner_id=owner_id
        )
        execution = await self._repository.get_for_workflow(
            workflow.id or "", execution_id
        )

        if execution is None:
            raise ExecutionNotFoundError(execution_id)
        if execution.status is not ExecutionStatus.FAILED:
            raise ExecutionStateError(
                f"eksekusi {execution.id} berstatus {execution.status.value}",
                public_message="Hanya eksekusi berstatus FAILED yang dapat diulang.",
            )
        if not execution.failed_operations:
            raise ExecutionStateError(
                f"eksekusi {execution.id} tidak memiliki operasi gagal",
                public_message="Tidak ada operasi gagal yang dapat diulang.",
            )

        claimed = await self._workflows.claim_execution(
            workflow_id=workflow.id or "", owner_id=owner_id
        )
        if claimed is None:
            raise ExecutionPreconditionError(
                EXECUTION_IN_PROGRESS,
                log_message=f"workflow {workflow.id} sedang menjalankan proses lain",
            )

        await self._repository.reset_for_retry(execution.id or "")
        return await self._repository.get(execution.id or "") or execution

    async def list_executions(
        self, *, workflow_id: str, owner_id: str
    ) -> list[ExecutionRecord]:
        """Riwayat eksekusi milik workflow dosen yang login."""
        workflow = await self._workflows.get_workflow(
            workflow_id=workflow_id, owner_id=owner_id
        )
        return await self._repository.list_for_workflow(workflow.id or "")

    async def get_execution(
        self, *, workflow_id: str, owner_id: str, execution_id: str
    ) -> ExecutionRecord:
        """Detail satu eksekusi (beserta operasinya) milik dosen yang login."""
        workflow = await self._workflows.get_workflow(
            workflow_id=workflow_id, owner_id=owner_id
        )
        execution = await self._repository.get_for_workflow(
            workflow.id or "", execution_id
        )
        if execution is None:
            raise ExecutionNotFoundError(execution_id)
        return execution

    # --- Dijalankan di background ---------------------------------------

    async def execute(
        self,
        *,
        execution_id: str,
        owner_id: str,
        emit_event: EmitEvent | None = None,
    ) -> ExecutionRecord:
        """Jalankan operasi yang belum berhasil, lalu simpan hasil read-back.

        Melempar :class:`ExecutionFailedError` setelah hasil disimpan bila ada
        operasi gagal atau read-back tidak sesuai, supaya orkestrator menandai
        workflow ``FAILED``. Exception ini tidak pernah dilempar ke client:
        eksekusi selalu berjalan di background.
        """
        execution = await self._repository.get(execution_id)
        if execution is None:
            raise ExecutionNotFoundError(execution_id)
        workflow = await self._workflows.get_workflow(
            workflow_id=execution.workflow_id, owner_id=owner_id
        )
        plan = await self._plans.get_by_id(execution.course_plan_id)
        if plan is None:
            await self._repository.finish(
                execution_id,
                status=ExecutionStatus.FAILED,
                at=_utcnow(),
                error_message="Course plan untuk eksekusi ini tidak ditemukan.",
            )
            raise ExecutionFailedError("course plan eksekusi tidak ditemukan")

        await self._repository.mark_running(execution_id, at=_utcnow())
        weeks_by_id = {week.id: week for week in plan.weeks}

        for operation in execution.operations:
            if operation.status in (OperationStatus.SUCCESS, OperationStatus.SKIPPED):
                continue
            week = weeks_by_id.get(operation.course_plan_week_id)
            if operation.operation_type is not OperationType.SECTION or week is None:
                # Operasi konten (M04) belum dijalankan pada cakupan STRUCTURE.
                continue
            await self._run_section_operation(
                execution, operation, week, emit_event=emit_event
            )

        updated = await self._repository.get(execution_id)
        failed = updated.summary.failed if updated is not None else 0
        status = ExecutionStatus.FAILED if failed else ExecutionStatus.SUCCESS
        error_message = (
            f"{failed} operasi gagal diterapkan ke Moodle." if failed else None
        )

        readback = await self._read_back(execution, plan)
        if not readback["matches"]:
            status = ExecutionStatus.FAILED
            error_message = error_message or "Hasil read-back tidak sesuai course plan."

        await self._repository.finish(
            execution_id,
            status=status,
            at=_utcnow(),
            readback=readback,
            error_message=error_message,
        )
        final = await self._repository.get(execution_id)
        if status is ExecutionStatus.FAILED:
            raise ExecutionFailedError(error_message or "eksekusi gagal")

        logger.info(
            "eksekusi %s workflow %s selesai: %s operasi",
            execution_id,
            workflow.id,
            final.summary.total if final is not None else 0,
        )
        return final

    # --- Prasyarat --------------------------------------------------------

    async def _require_prerequisites(
        self, workflow: WorkflowRecord
    ) -> CoursePlanRecord:
        plan = await self._plans.get_latest(workflow.id or "")
        if plan is None or plan.status is not CoursePlanStatus.APPROVED:
            raise ExecutionPreconditionError(
                PLAN_NOT_APPROVED,
                log_message=f"workflow {workflow.id} belum memiliki course plan APPROVED",
            )
        if workflow.moodle_course_id is None:
            raise ExecutionPreconditionError(
                MOODLE_TARGET_NOT_SET,
                log_message=f"workflow {workflow.id} belum memiliki course target",
            )
        try:
            status = await self._moodle.get_status()
        except MOODLE_FAILURES as exc:
            raise ExecutionPreconditionError(
                MOODLE_UNAVAILABLE,
                log_message=f"Moodle tidak dapat dihubungi: {exc}",
            ) from exc
        if not status.connected:
            raise ExecutionPreconditionError(
                MOODLE_UNAVAILABLE,
                log_message="Moodle melaporkan status tidak terhubung",
            )
        return plan

    # --- Satu operasi section --------------------------------------------

    async def _run_section_operation(
        self,
        execution: ExecutionRecord,
        operation: ExecutionOperationRecord,
        week: CoursePlanWeekRecord,
        *,
        emit_event: EmitEvent | None,
    ) -> None:
        retry_count = operation.retry_count + (
            1 if operation.status is OperationStatus.FAILED else 0
        )
        await self._repository.start_operation(operation.id or "")

        metadata: dict = {
            "execution_id": execution.id,
            "week_number": week.week_number,
            "operation_type": operation.operation_type.value,
        }
        try:
            mapped_section_id = await self._mapped_section_id(week)
            result = await self._moodle.save_section(
                execution.moodle_course_id,
                name=section_name(week),
                section_number=week.week_number,
                summary=section_summary(week),
                section_id=mapped_section_id,
            )
            moodle_section_id = result.section.moodle_section_id
            await self._repository.finish_operation(
                operation.id or "",
                status=OperationStatus.SUCCESS,
                moodle_object_id=str(moodle_section_id),
                retry_count=retry_count,
            )
            await self._save_mapping(week, moodle_section_id)
            message = f"Minggu {week.week_number} diterapkan ke Moodle."
            metadata.update(
                status=OperationStatus.SUCCESS.value,
                moodle_object_id=str(moodle_section_id),
                section_created=result.created,
            )
        except MOODLE_FAILURES as exc:
            public_message = normalize_moodle_error(exc).message
            await self._repository.finish_operation(
                operation.id or "",
                status=OperationStatus.FAILED,
                error_message=public_message,
                retry_count=retry_count,
            )
            message = f"Minggu {week.week_number} gagal diterapkan ke Moodle."
            metadata.update(
                status=OperationStatus.FAILED.value,
                error_message=public_message,
            )
            logger.warning(
                "operasi section minggu %s eksekusi %s gagal: %s",
                week.week_number,
                execution.id,
                exc,
            )
        except Exception:
            # Bug aplikasi tidak boleh menghentikan minggu lain; detail hanya
            # masuk log, client menerima pesan generik.
            await self._repository.finish_operation(
                operation.id or "",
                status=OperationStatus.FAILED,
                error_message="Operasi Moodle gagal.",
                retry_count=retry_count,
            )
            message = f"Minggu {week.week_number} gagal diterapkan ke Moodle."
            metadata.update(
                status=OperationStatus.FAILED.value,
                error_message="Operasi Moodle gagal.",
            )
            logger.exception(
                "operasi section minggu %s eksekusi %s gagal di luar error Moodle",
                week.week_number,
                execution.id,
            )

        await self._emit(emit_event, message=message, metadata=metadata)

    async def _mapped_section_id(
        self, week: CoursePlanWeekRecord
    ) -> int | None:
        """ID section Moodle yang sudah tercatat untuk minggu ini (BE-04.3)."""
        if week.id is None:
            return None
        return await self._mappings.get_moodle_id(SECTION_ENTITY_TYPE, week.id)

    async def _save_mapping(
        self, week: CoursePlanWeekRecord, moodle_section_id: int
    ) -> None:
        """Simpan pemetaan minggu → section Moodle sebagai sumber idempotency."""
        if week.id is None:
            return
        try:
            await self._mappings.save(
                MoodleMapping(
                    entity_type=SECTION_ENTITY_TYPE,
                    internal_id=week.id,
                    moodle_id=moodle_section_id,
                )
            )
        except DuplicateMappingError as exc:
            logger.warning(
                "pemetaan section minggu %s tidak disimpan: %s",
                week.id,
                exc,
            )

    async def _emit(
        self,
        emit_event: EmitEvent | None,
        *,
        message: str,
        metadata: dict,
    ) -> None:
        """Terbitkan event operasi; kegagalan event tidak menggagalkan eksekusi."""
        if emit_event is None:
            return
        try:
            await emit_event(
                event=EVENT_MOODLE_OPERATION,
                message=message,
                metadata=metadata,
            )
        except Exception:
            logger.exception("gagal menerbitkan event operasi Moodle")

    # --- Read-back --------------------------------------------------------

    async def _read_back(
        self,
        execution: ExecutionRecord,
        plan: CoursePlanRecord,
    ) -> dict:
        """Bandingkan struktur course Moodle dengan course plan yang dieksekusi."""
        expected = {
            week.week_number: section_name(week)
            for week in plan.weeks
        }
        try:
            contents = await self._moodle.get_course_contents(
                execution.moodle_course_id
            )
        except MOODLE_FAILURES as exc:
            return {
                "checked": False,
                "matches": False,
                "expected_sections": len(expected),
                "error": normalize_moodle_error(exc).message,
            }

        actual = {
            section.section_number: section.name
            for section in contents.sections
        }
        # Section 0 adalah "General" bawaan Moodle, bukan bagian course plan.
        ordered_numbers = sorted(number for number in actual if number > 0)
        expected_numbers = sorted(expected)
        missing = [
            number
            for number in expected_numbers
            if number not in actual
        ]
        mismatched = [
            number
            for number in expected_numbers
            if number in actual and actual[number] != expected[number]
        ]
        ordered = ordered_numbers[: len(expected_numbers)] == expected_numbers
        return {
            "checked": True,
            "matches": not missing and not mismatched and ordered,
            "expected_sections": len(expected),
            "actual_sections": len(ordered_numbers),
            "ordered": ordered,
            "missing_weeks": missing,
            "mismatched_weeks": mismatched,
        }


def _planned_sections(
    workflow: WorkflowRecord,
    plan: CoursePlanRecord,
) -> list[PlannedOperation]:
    """Satu operasi ``SECTION`` per minggu, dengan kunci idempotency stabil."""
    return [
        PlannedOperation(
            operation_type=OperationType.SECTION,
            course_plan_week_id=week.id,
            idempotency_key=(
                f"{workflow.id}:week:{week.week_number}:{OperationType.SECTION.value}"
            ),
        )
        for week in plan.weeks
    ]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)