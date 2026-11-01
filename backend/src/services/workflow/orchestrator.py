"""Orkestrator workflow RPS (BE-11.2).

Orkestrator mengendalikan urutan tahap dan transisi status; LLM tidak dapat
mengubah status workflow. Pada sprint ini dua tahap dijalankan berurutan dalam
satu workflow:

```text
PROCESSING_RPS  (pipeline Docling BE-05.2)
      ↓
ANALYZING_RPS   (BE-08.1 → BE-09.2 → BE-08.2)
```

Daftar ``WorkflowStage`` sengaja berupa tuple sehingga tahap berikutnya
(``PLANNING_COURSE`` dan seterusnya, issue BE-11.2) ditambahkan dengan
menambahkan entri — tanpa mengubah tahap yang sudah ada.

Setiap perubahan status, aktivitas agent, retry, dan kegagalan melewati
:class:`~src.services.workflow.service.WorkflowService` dan tercatat sebagai
``workflow_events``. Proses berjalan di background dengan session database
sendiri; kegagalan tidak pernah dilempar ke request yang sudah selesai.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from src.config.database import get_session_factory
from src.models.workflow import WorkflowStatus
from src.models.workflow_event import EventType
from src.services.analysis.service import RPSEvent
from src.services.rps.errors import RPSDomainError
from src.services.rps.service import RPSService
from src.services.workflow.domain import WorkflowRecord, stage_name
from src.services.workflow.errors import WorkflowDomainError
from src.services.workflow.service import (
    EVENT_FAILED,
    EVENT_RETRY,
    EVENT_STAGE_PROGRESS,
    WorkflowService,
)

__all__ = [
    "RPS_ANALYSIS_STAGES",
    "RPS_PROCESSING_STAGES",
    "WorkflowStage",
    "execute_workflow",
    "run_rps_analysis_workflow",
    "run_rps_processing_workflow",
]

logger = logging.getLogger(__name__)

#: Nama tahap analisis pada event (sama dengan ``stage_name`` domain).
ANALYSIS_STAGE_NAME = stage_name(WorkflowStatus.ANALYZING_RPS) or "rps_analysis"

#: Pemetaan event service analisis (BE-09.2) ke kategori dan nama event publik.
#: ``ANALYSIS_COMPLETED`` tidak dipetakan: orkestrator sudah mencatat
#: ``WORKFLOW_STAGE_COMPLETED`` ketika tahap itu benar-benar selesai.
ANALYSIS_EVENT_MAP: dict[str, tuple[EventType, str]] = {
    "ANALYSIS_STARTED": (EventType.AKTIVITAS_AGENT, EVENT_STAGE_PROGRESS),
    "YAML_PARSING": (EventType.AKTIVITAS_AGENT, EVENT_STAGE_PROGRESS),
    "YAML_PARSED": (EventType.AKTIVITAS_AGENT, EVENT_STAGE_PROGRESS),
    "LLM_CALLING": (EventType.AKTIVITAS_AGENT, EVENT_STAGE_PROGRESS),
    "LLM_RESPONDED": (EventType.AKTIVITAS_AGENT, EVENT_STAGE_PROGRESS),
    "VALIDATING": (EventType.AKTIVITAS_AGENT, EVENT_STAGE_PROGRESS),
    "RETRY_FIX": (EventType.RETRY_FIX, EVENT_RETRY),
    "ANALYSIS_FAILED": (EventType.ERROR_FAILURE, EVENT_FAILED),
}


@dataclass
class WorkflowContext:
    """Keadaan satu run yang dibagikan ke seluruh handler tahap."""

    workflow: WorkflowRecord
    workflow_service: WorkflowService
    rps_service: RPSService
    #: Event kegagalan sudah ditulis oleh service yang gagal (mis. analisis),
    #: sehingga orkestrator tidak perlu menulis event kegagalan kedua.
    failure_emitted: bool = False

    @property
    def workflow_id(self) -> str:
        return self.workflow.id or ""

    @property
    def rps_id(self) -> str:
        return self.workflow.rps_id

    @property
    def owner_id(self) -> str:
        return self.workflow.owner_id


StageHandler = Callable[[WorkflowContext], Awaitable[None]]


@dataclass(frozen=True)
class WorkflowStage:
    """Satu tahap pekerjaan: status workflow dan aksi yang dijalankan."""

    status: WorkflowStatus
    handler: StageHandler

    @property
    def name(self) -> str | None:
        return stage_name(self.status)


# --- Tahap: pemrosesan RPS ---------------------------------------------------


async def _run_processing(ctx: WorkflowContext) -> None:
    """Konversi dokumen RPS (BE-05.2), bila belum dikonversi.

    Endpoint ``POST /rps/{id}/process`` sudah menandai dokumen ``PROCESSING``
    sebelum orkestrator dijadwalkan; pemeriksaan status di sini membuat tahap
    yang sama aman dipanggil ulang (mis. runner dijalankan setelah proses
    server sempat berhenti).
    """
    document = await ctx.rps_service.get_rps(
        rps_id=ctx.rps_id, owner_id=ctx.owner_id
    )
    if not document.is_processing:
        start = await ctx.rps_service.begin_processing(
            rps_id=ctx.rps_id, owner_id=ctx.owner_id
        )
        if start.reused:
            # Sudah diproses untuk hash + versi skema yang sama (BE-05).
            return

    await ctx.rps_service.convert(rps_id=ctx.rps_id, owner_id=ctx.owner_id)


# --- Tahap: analisis RPS -----------------------------------------------------


async def _run_analysis(ctx: WorkflowContext) -> None:
    """Analisis RPS menjadi RPS Structured Data (BE-08.1 → BE-09.2 → BE-08.2).

    Analisis yang sudah selesai tidak dijalankan dua kali untuk dokumen yang
    sama (``begin_analysis`` mengembalikan ``scheduled=False``), sehingga
    workflow yang dibuat ulang tetap berakhir konsisten.
    """
    document = await ctx.rps_service.get_rps(
        rps_id=ctx.rps_id, owner_id=ctx.owner_id
    )
    if not document.is_analyzing:
        start = await ctx.rps_service.begin_analysis(
            rps_id=ctx.rps_id,
            owner_id=ctx.owner_id,
            force=False,
            workflow_id=ctx.workflow_id,
        )
        if not start.scheduled:
            return

    await ctx.rps_service.analyze(
        rps_id=ctx.rps_id,
        owner_id=ctx.owner_id,
        emit_event=_analysis_emitter(ctx),
    )


def _analysis_emitter(ctx: WorkflowContext) -> Callable[..., Awaitable[None]]:
    """Terjemahkan event service analisis menjadi WorkflowEvent dan status retry.

    Kegagalan penerbitan event tidak boleh menggagalkan analisis — sama seperti
    kontrak ``emit_event`` pada service analisis; ``_emit_safely`` menelannya
    dan mencatat di log.
    """

    async def emit(*, event_type: RPSEvent, message: str, **data: object) -> None:
        name = getattr(event_type, "name", str(event_type))
        mapped = ANALYSIS_EVENT_MAP.get(name)
        if mapped is None:
            return

        event_category, public_event = mapped
        if event_category is EventType.ERROR_FAILURE:
            ctx.failure_emitted = True

        # Status workflow mengikuti retry internal service analisis: RETRYING
        # selama memperbaiki output, kembali ke ANALYZING_RPS saat percobaan
        # berikutnya benar-benar dikirim ke model.
        if public_event == EVENT_RETRY:
            ctx.workflow = await ctx.workflow_service.mark_retrying(ctx.workflow)
        elif name == "LLM_CALLING" and int(data.get("attempt") or 1) > 1:
            ctx.workflow = await ctx.workflow_service.resume_stage(
                ctx.workflow, WorkflowStatus.ANALYZING_RPS
            )

        await ctx.workflow_service.record_event(
            ctx.workflow,
            event_type=event_category,
            event=public_event,
            stage=ANALYSIS_STAGE_NAME,
            message=message,
            metadata={key: value for key, value in data.items() if value is not None},
        )

    return emit


#: Urutan tahap per jenis pekerjaan. Entri baru (planning, generation, ...)
#: cukup ditambahkan ke tuple yang sesuai.
PROCESSING_STAGE = WorkflowStage(WorkflowStatus.PROCESSING_RPS, _run_processing)
ANALYSIS_STAGE = WorkflowStage(WorkflowStatus.ANALYZING_RPS, _run_analysis)

RPS_PROCESSING_STAGES: tuple[WorkflowStage, ...] = (PROCESSING_STAGE, ANALYSIS_STAGE)
RPS_ANALYSIS_STAGES: tuple[WorkflowStage, ...] = (ANALYSIS_STAGE,)


# --- Eksekusi ----------------------------------------------------------------


async def execute_workflow(
    *,
    workflow: WorkflowRecord,
    stages: tuple[WorkflowStage, ...],
    workflow_service: WorkflowService,
    rps_service: RPSService,
) -> None:
    """Jalankan deretan tahap pada satu workflow.

    Kegagalan tahap menghentikan rangkaian, menandai workflow ``FAILED``, dan
    menulis satu event kegagalan (kecuali event itu sudah ditulis oleh service
    yang gagal). Tidak ada exception yang dilempar ke pemanggil background.
    """
    ctx = WorkflowContext(
        workflow=workflow,
        workflow_service=workflow_service,
        rps_service=rps_service,
    )
    ctx.workflow = await workflow_service.begin_run(workflow, total=len(stages))

    for stage in stages:
        ctx.workflow = await workflow_service.begin_stage(ctx.workflow, stage.status)
        try:
            await stage.handler(ctx)
        except RPSDomainError as exc:
            await workflow_service.fail_run(
                ctx.workflow,
                stage=stage.name,
                message=exc.public_reason,
                emit_event=not ctx.failure_emitted,
            )
            return
        except Exception:
            logger.exception(
                "workflow %s gagal pada tahap %s", ctx.workflow_id, stage.name
            )
            await workflow_service.fail_run(
                ctx.workflow,
                stage=stage.name,
                message="Workflow gagal karena kesalahan tak terduga.",
                emit_event=not ctx.failure_emitted,
            )
            return

        ctx.workflow = await workflow_service.complete_stage(
            ctx.workflow, stage.status
        )

    await workflow_service.complete_run(ctx.workflow)


# --- Entry point background --------------------------------------------------


async def run_rps_processing_workflow(*, rps_id: str, owner_id: str) -> None:
    """Jalankan pemrosesan + analisis RPS di background (issue BE-11.2).

    Dipanggil setelah response ``POST /rps/{id}/process`` dikirim; workflow
    sudah ditautkan ke dokumen oleh route.
    """
    await _run_in_background(
        rps_id=rps_id,
        owner_id=owner_id,
        stages=RPS_PROCESSING_STAGES,
    )


async def run_rps_analysis_workflow(*, rps_id: str, owner_id: str) -> None:
    """Lanjutkan analisis ulang pada workflow yang sama (issue BE-11.2)."""
    await _run_in_background(
        rps_id=rps_id,
        owner_id=owner_id,
        stages=RPS_ANALYSIS_STAGES,
    )


async def _run_in_background(
    *,
    rps_id: str,
    owner_id: str,
    stages: tuple[WorkflowStage, ...],
) -> None:
    """Buka session sendiri dan jalankan workflow; kegagalan berhenti di sini.

    Session milik request sudah ditutup saat background berjalan. Exception yang
    lolos akan menjadi "Task exception was never retrieved", jadi seluruh
    kegagalan ditelan dan dilaporkan lewat status workflow, event, dan log.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        rps_service = RPSService.from_session(session)
        workflow_service = WorkflowService.from_session(session)
        try:
            document = await rps_service.get_rps(rps_id=rps_id, owner_id=owner_id)
            if document.workflow_id is None:
                logger.error(
                    "workflow untuk rps %s tidak ditemukan (workflow_id kosong)", rps_id
                )
                return

            workflow = await workflow_service.get_workflow(
                workflow_id=document.workflow_id, owner_id=owner_id
            )
            await execute_workflow(
                workflow=workflow,
                stages=stages,
                workflow_service=workflow_service,
                rps_service=rps_service,
            )
        except RPSDomainError as exc:
            logger.warning(
                "workflow rps %s gagal: %s", rps_id, exc.log_message
            )
        except WorkflowDomainError as exc:
            logger.warning(
                "workflow rps %s gagal: %s", rps_id, exc.log_message
            )
        except Exception:
            logger.exception(
                "workflow rps %s gagal di luar error domain", rps_id
            )
        else:
            logger.info("workflow rps %s selesai", rps_id)
