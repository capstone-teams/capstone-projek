"""Melanjutkan run workflow yang terputus saat server berhenti.

Analisis RPS, penyusunan rencana, pembuatan konten, dan eksekusi Moodle berjalan
**in-process**. Restart container (deploy, reload) mematikan proses di tengah
jalan tanpa sempat menulis status akhir, sehingga workflow tertahan di tahap
"berjalan" dan UI menampilkan progres yang tidak pernah selesai. Saat startup
tidak ada run yang mungkin masih hidup, jadi tahap yang sedang berjalan
dijadwalkan ulang di latar belakang — dosen tidak perlu mengulang dari awal.

ponytail: lanjutan memanggil ulang tahap, bukan menyimpan checkpoint per item.
Tahap satu-panggilan-model (analisis RPS, penyusunan rencana) diulang utuh karena
hasil antaranya tidak disimpan; tahap konten melewati item yang sudah tersimpan
sehingga tidak ada panggilan model yang dibayar dua kali. Status ``VALIDATING``
tanpa konten tersimpan dianggap bagian perencanaan, ``EXECUTING_TO_MOODLE``
dilanjutkan lewat eksekusi yang masih PENDING, sedangkan ``VERIFYING``,
``RETRYING``, dan ``QUEUED`` belum punya jalur lanjut sehingga ditutup gagal.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from functools import partial

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session_factory
from src.models.content import Content
from src.models.moodle_execution import ExecutionStatus, MoodleExecution
from src.models.workflow import Workflow, WorkflowStatus
from src.models.workflow_event import EventType, WorkflowEvent
from src.services.workflow.domain import STAGE_BY_STATUS

__all__ = ["FAILED_MESSAGE", "INTERRUPTED_STATUSES", "reconcile_interrupted_runs"]

logger = logging.getLogger(__name__)

#: Status yang hanya mungkin dipegang selama proses aplikasi masih hidup.
INTERRUPTED_STATUSES = frozenset(
    {
        WorkflowStatus.QUEUED,
        WorkflowStatus.PROCESSING_RPS,
        WorkflowStatus.ANALYZING_RPS,
        WorkflowStatus.PLANNING_COURSE,
        WorkflowStatus.GENERATING_CONTENT,
        WorkflowStatus.VALIDATING,
        WorkflowStatus.EXECUTING_TO_MOODLE,
        WorkflowStatus.VERIFYING,
        WorkflowStatus.RETRYING,
    }
)

FAILED_EVENT = "WORKFLOW_FAILED"
FAILED_MESSAGE = (
    "Proses berhenti karena server dimulai ulang dan tidak dapat dilanjutkan. "
    "Silakan jalankan ulang langkah ini."
)

ResumeJob = Callable[[], Awaitable[None]]


async def reconcile_interrupted_runs() -> int:
    """Jadwalkan lanjutan seluruh run yang terputus; jumlah yang dilanjutkan dikembalikan."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        return await resume_interrupted_runs(session)


async def resume_interrupted_runs(session: AsyncSession) -> int:
    """Lanjutkan workflow pada status berjalan, atau tutup bila tidak ada jalannya."""
    statement = select(Workflow).where(Workflow.status.in_(INTERRUPTED_STATUSES))
    victims = (await session.execute(statement)).scalars().all()

    resumed = 0
    failed = 0
    for victim in victims:
        job = await _resume_job(session, victim)
        if job is None:
            _mark_failed(session, victim)
            failed += 1
            continue
        # Dijadwalkan, bukan ditunggu: startup tidak boleh menahan proses model.
        asyncio.create_task(job(), name=f"resume-workflow-{victim.id}")
        resumed += 1

    await session.commit()
    if victims:
        logger.warning(
            "%s workflow terputus setelah server mulai ulang: %s dilanjutkan, %s gagal",
            len(victims),
            resumed,
            failed,
        )
    return resumed


async def _resume_job(session: AsyncSession, workflow: Workflow) -> ResumeJob | None:
    """Pilih runner tahap yang harus dilanjutkan untuk satu workflow."""
    # Impor lokal memutus siklus: orkestrator mengimpor service workflow, dan modul
    # ini dipanggil dari lifespan aplikasi.
    from src.services.workflow import orchestrator

    workflow_id = workflow.id
    owner_id = workflow.owner_id
    status = workflow.status

    if status is WorkflowStatus.PROCESSING_RPS:
        return partial(
            orchestrator.run_rps_processing_workflow,
            rps_id=workflow.rps_id,
            owner_id=owner_id,
        )
    if status is WorkflowStatus.ANALYZING_RPS:
        return partial(
            orchestrator.run_rps_analysis_workflow,
            rps_id=workflow.rps_id,
            owner_id=owner_id,
        )
    if status is WorkflowStatus.PLANNING_COURSE:
        return partial(
            orchestrator.run_course_planning_workflow,
            workflow_id=workflow_id,
            owner_id=owner_id,
        )
    if status is WorkflowStatus.GENERATING_CONTENT:
        return partial(
            orchestrator.run_content_generation_workflow,
            workflow_id=workflow_id,
            owner_id=owner_id,
        )
    if status is WorkflowStatus.VALIDATING:
        # Validasi rencana terjadi di dalam tahap perencanaan; validasi konten
        # baru mungkin setelah ada konten tersimpan.
        if await _content_count(session, workflow_id):
            return partial(
                orchestrator.run_content_generation_workflow,
                workflow_id=workflow_id,
                owner_id=owner_id,
            )
        return partial(
            orchestrator.run_course_planning_workflow,
            workflow_id=workflow_id,
            owner_id=owner_id,
        )
    if status is WorkflowStatus.EXECUTING_TO_MOODLE:
        execution_id = await _pending_execution_id(session, workflow_id)
        if execution_id is None:
            return None
        return partial(
            orchestrator.run_execution_workflow,
            workflow_id=workflow_id,
            owner_id=owner_id,
            execution_id=execution_id,
        )
    return None


async def _content_count(session: AsyncSession, workflow_id: str) -> int:
    statement = (
        select(func.count())
        .select_from(Content)
        .where(Content.workflow_id == workflow_id)
    )
    return int((await session.execute(statement)).scalar_one())


async def _pending_execution_id(
    session: AsyncSession, workflow_id: str
) -> str | None:
    statement = (
        select(MoodleExecution.id)
        .where(
            MoodleExecution.workflow_id == workflow_id,
            MoodleExecution.status.in_(
                {ExecutionStatus.PENDING, ExecutionStatus.RUNNING}
            ),
        )
        .order_by(MoodleExecution.created_at.desc())
        .limit(1)
    )
    return (await session.execute(statement)).scalar_one_or_none()


def _mark_failed(session: AsyncSession, workflow: Workflow) -> None:
    """Tutup workflow yang tahapnya tidak punya jalur lanjut."""
    stage = STAGE_BY_STATUS.get(workflow.status)
    now = datetime.now(UTC)
    workflow.status = WorkflowStatus.FAILED
    workflow.completed_at = now
    workflow.updated_at = now
    session.add(
        WorkflowEvent(
            workflow_id=workflow.id,
            event_type=EventType.ERROR_FAILURE,
            event=FAILED_EVENT,
            stage=stage,
            message=FAILED_MESSAGE,
        )
    )
