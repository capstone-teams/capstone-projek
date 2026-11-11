"""Mode otomatis workflow: RPS sampai konten siap direview dalam satu rangkaian.

Dipicu ``POST /rps/{id}/process`` dengan ``autopilot: true``. Rangkaian memakai
service dan runner yang sama dengan endpoint manual, sehingga aturan setiap
tahap (prasyarat, klaim atomik, validasi, event) tetap berlaku:

```text
proses + analisis RPS → susun course plan → setujui course plan (bila lolos
validasi) → generate konten seluruh minggu → WAITING_FOR_REVIEW
```

Rangkaian sengaja berhenti sebelum eksekusi Moodle: konten baru dikirim ke
Moodle setelah dosen menyetujuinya (Proposal §3.3.7, DL-012). Dosen cukup
melakukan satu review akhir ("Setujui & publikasikan").

Bila satu tahap gagal atau course plan tidak lolos validasi, rangkaian berhenti
dengan event yang menjelaskan alasannya; workflow tetap pada status tahap
terakhir sehingga dosen dapat melanjutkan secara manual.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from src.config.database import get_session_factory
from src.models.workflow import WorkflowStatus
from src.models.workflow_event import EventType
from src.services.rps.service import RPSService
from src.services.workflow.domain import WorkflowRecord
from src.services.workflow.service import EVENT_STAGE_PROGRESS, WorkflowService

__all__ = ["AUTOPILOT_EVENT", "run_autopilot_workflow"]

logger = logging.getLogger(__name__)

#: Event aktivitas agent yang menandai langkah mode otomatis.
AUTOPILOT_EVENT = EVENT_STAGE_PROGRESS

Runner = Callable[..., Awaitable[None]]


async def _note(workflow_service: WorkflowService, workflow: WorkflowRecord, message: str) -> None:
    await workflow_service.record_event(
        workflow,
        event_type=EventType.AKTIVITAS_AGENT,
        event=AUTOPILOT_EVENT,
        stage=None,
        message=f"Mode otomatis: {message}",
        metadata={"autopilot": True},
    )


async def _workflow_of_rps(rps_id: str, owner_id: str) -> WorkflowRecord | None:
    async with get_session_factory()() as session:
        document = await RPSService.from_session(session).get_rps(rps_id=rps_id, owner_id=owner_id)
        if document.workflow_id is None:
            return None
        return await WorkflowService.from_session(session).get_workflow(
            workflow_id=document.workflow_id, owner_id=owner_id
        )


async def _current(workflow_id: str, owner_id: str) -> WorkflowRecord:
    async with get_session_factory()() as session:
        return await WorkflowService.from_session(session).get_workflow(
            workflow_id=workflow_id, owner_id=owner_id
        )


def _stopped(workflow: WorkflowRecord) -> bool:
    """Tahap sebelumnya tidak berakhir di status tunggu dosen (mis. ``FAILED``)."""
    return workflow.status is not WorkflowStatus.WAITING_FOR_REVIEW


async def run_autopilot_workflow(
    *,
    rps_id: str,
    owner_id: str,
    processing_runner: Runner | None = None,
    planning_runner: Runner | None = None,
    content_runner: Runner | None = None,
) -> None:
    """Jalankan seluruh rangkaian otomatis di background.

    Runner tiap tahap dapat diganti pengujian; nilai bawaannya runner orkestrator
    yang juga dipakai endpoint manual. Seluruh kegagalan ditelan dan dilaporkan
    lewat status workflow, event, dan log.
    """
    # Import lokal memutus siklus impor paket (pola yang sama dengan orkestrator).
    from src.services.content.errors import ContentDomainError
    from src.services.content.generation import ContentGenerationService, ContentJob
    from src.models.course_plan import CoursePlanStatus
    from src.services.course_plan.errors import CoursePlanDomainError, CoursePlanNotFoundError
    from src.services.course_plan.service import CoursePlanService
    from src.services.workflow.orchestrator import (
        run_content_generation_workflow,
        run_course_planning_workflow,
        run_rps_processing_workflow,
    )

    processing_runner = processing_runner or run_rps_processing_workflow
    planning_runner = planning_runner or run_course_planning_workflow
    content_runner = content_runner or run_content_generation_workflow

    try:
        # 1. Proses dan analisis RPS.
        await processing_runner(rps_id=rps_id, owner_id=owner_id)
        workflow = await _workflow_of_rps(rps_id, owner_id)
        if workflow is None or _stopped(workflow):
            return
        workflow_id = workflow.id or ""

        # 2. Susun course plan (dilewati bila workflow sudah punya rencana).
        async with get_session_factory()() as session:
            workflows = WorkflowService.from_session(session)
            plans = CoursePlanService.from_session(session)
            try:
                existing = await plans.get_latest(workflow_id=workflow_id, owner_id=owner_id)
            except CoursePlanNotFoundError:
                existing = None
            if existing is None:
                await _note(workflows, workflow, "menyusun course plan dari hasil analisis RPS.")
                await plans.start_planning(workflow_id=workflow_id, owner_id=owner_id, regenerate=False)
        if existing is None:
            await planning_runner(workflow_id=workflow_id, owner_id=owner_id, instruction=None)
            workflow = await _current(workflow_id, owner_id)
            if _stopped(workflow):
                return

        # 3. Setujui course plan bila lolos validasi; bila tidak, dosen meninjaunya.
        async with get_session_factory()() as session:
            workflows = WorkflowService.from_session(session)
            plans = CoursePlanService.from_session(session)
            workflow = await workflows.get_workflow(workflow_id=workflow_id, owner_id=owner_id)
            try:
                latest = await plans.get_latest(workflow_id=workflow_id, owner_id=owner_id)
            except CoursePlanNotFoundError:
                return
            if latest.status is not CoursePlanStatus.APPROVED:
                try:
                    await plans.approve(workflow_id=workflow_id, owner_id=owner_id)
                except CoursePlanDomainError as exc:
                    await _note(
                        workflows,
                        workflow,
                        f"berhenti di review course plan ({exc.public_message}).",
                    )
                    return
                await _note(workflows, workflow, "course plan lolos validasi dan disetujui otomatis.")

            # 4. Generate konten seluruh minggu.
            try:
                await ContentGenerationService.from_session(session).start(
                    workflow_id=workflow_id, owner_id=owner_id, job=ContentJob()
                )
            except ContentDomainError as exc:
                await _note(workflows, workflow, f"generate konten tidak dapat dimulai ({exc.public_message}).")
                return
            await _note(workflows, workflow, "membuat konten seluruh minggu.")

        await content_runner(workflow_id=workflow_id, owner_id=owner_id)
        workflow = await _current(workflow_id, owner_id)
        if not _stopped(workflow):
            async with get_session_factory()() as session:
                await _note(
                    WorkflowService.from_session(session),
                    workflow,
                    "konten selesai dibuat. Tinjau lalu setujui untuk mempublikasikan ke Moodle.",
                )
    except Exception:
        logger.exception("autopilot workflow untuk rps %s gagal di luar tahap", rps_id)
