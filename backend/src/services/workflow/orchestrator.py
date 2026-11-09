"""Orkestrator workflow (BE-11.2, BE-14.3, BE-17.1).

Orkestrator mengendalikan urutan tahap dan transisi status; LLM tidak dapat
mengubah status workflow. Empat rangkaian tahap berjalan di atas workflow yang
sama:

```text
Post /rps/{id}/process            PROCESSING_RPS → ANALYZING_RPS
Post /workflows/{id}/plan         PLANNING_COURSE → VALIDATING
Post /rps/{id}/reanalyze          ANALYZING_RPS
Post /workflows/{id}/executions   EXECUTING_TO_MOODLE
```

Setelah rangkaian tahap selesai, workflow berhenti pada
``WAITING_FOR_REVIEW`` — status tunggu DL-012, bukan ``COMPLETED`` — karena
keputusan dosen (review rencana, generate konten, eksekusi) melanjutkan
workflow yang sama.

Daftar ``WorkflowStage`` sengaja berupa tuple sehingga tahap berikutnya
ditambahkan dengan menambahkan entri — tanpa mengubah tahap yang sudah ada.
Setiap perubahan status, aktivitas agent, retry, dan kegagalan melewati
:class:`~src.services.workflow.service.WorkflowService` dan tercatat sebagai
``workflow_events``. Proses berjalan di background dengan session database
sendiri; kegagalan tidak pernah dilempar ke request yang sudah selesai.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.config.database import get_session_factory
from src.config.settings import get_settings
from src.models.workflow import WorkflowStatus
from src.models.workflow_event import EventType
from src.services.analysis.service import RPSEvent
from src.services.course_plan.errors import CoursePlanDomainError
from src.services.course_plan.planner import (
    CoursePlanner,
    PlannedCoursePlan,
    PlanningRequest,
    get_course_planner,
)
from src.services.execution.errors import ExecutionDomainError
from src.services.llm.base import LLMProviderError
from src.services.moodle_client import MoodleClient
from src.services.moodle_integration_service import MoodleIntegrationService
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
    "COURSE_PLANNING_STAGES",
    "EXECUTION_STAGES",
    "RPS_ANALYSIS_STAGES",
    "RPS_PROCESSING_STAGES",
    "WorkflowStage",
    "execute_workflow",
    "run_course_planning_workflow",
    "run_execution_workflow",
    "run_rps_analysis_workflow",
    "run_rps_processing_workflow",
]

if TYPE_CHECKING:  # pragma: no cover - hanya untuk anotasi tipe
    from src.services.course_plan.service import CoursePlanService
    from src.services.execution.service import ExecutionService


logger = logging.getLogger(__name__)

#: Event publik setelah sebuah versi course plan tersimpan (BE-14.3).
EVENT_PLAN_GENERATED = "WORKFLOW_PLAN_GENERATED"

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

#: Pemetaan event Course Planning Service (BE-14.3) ke event workflow.
#: ``PLANNING_COMPLETED`` tidak dipetakan: tahap yang berakhir sudah menulis
#: ``WORKFLOW_STAGE_COMPLETED``.
PLANNING_EVENT_MAP: dict[str, tuple[EventType, str]] = {
    "LLM_CALLING": (EventType.AKTIVITAS_AGENT, EVENT_STAGE_PROGRESS),
    "LLM_RESPONDED": (EventType.AKTIVITAS_AGENT, EVENT_STAGE_PROGRESS),
    "VALIDATING": (EventType.AKTIVITAS_AGENT, EVENT_STAGE_PROGRESS),
    "RETRY_FIX": (EventType.RETRY_FIX, EVENT_RETRY),
    "PLANNING_FAILED": (EventType.ERROR_FAILURE, EVENT_FAILED),
}

#: Nama tahap perencanaan/validasi pada event.
PLANNING_STAGE_NAME = stage_name(WorkflowStatus.PLANNING_COURSE) or "course_planning"
PLAN_VALIDATION_STAGE_NAME = stage_name(WorkflowStatus.VALIDATING) or "validation"


@dataclass
class WorkflowContext:
    """Keadaan satu run yang dibagikan ke seluruh handler tahap."""

    workflow: WorkflowRecord
    workflow_service: WorkflowService
    rps_service: RPSService
    #: Hanya terisi pada rangkaian tahap course planning (BE-14.3).
    course_plan_service: CoursePlanService | None = None
    planner: CoursePlanner | None = None
    instruction: str | None = None
    planning_request: PlanningRequest | None = None
    planned_plan: PlannedCoursePlan | None = None
    #: Hanya terisi pada rangkaian tahap eksekusi Moodle (BE-17.1).
    execution_service: ExecutionService | None = None
    execution_id: str | None = None
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


# --- Tahap: course planning (BE-14.3) ----------------------------------------


def _planning_emitter(ctx: WorkflowContext) -> Callable[..., Awaitable[None]]:
    """Terjemahkan event Course Planning Service menjadi WorkflowEvent.

    Retry service memindahkan workflow ke ``RETRYING`` dan kembali ke
    ``PLANNING_COURSE`` saat percobaan berikutnya benar-benar dikirim ke model —
    pola yang sama dengan tahap analisis RPS.
    """

    async def emit(*, event: str, message: str, **data: object) -> None:
        mapped = PLANNING_EVENT_MAP.get(event)
        if mapped is None:
            return

        event_category, public_event = mapped
        if event_category is EventType.ERROR_FAILURE:
            ctx.failure_emitted = True

        if public_event == EVENT_RETRY:
            ctx.workflow = await ctx.workflow_service.mark_retrying(ctx.workflow)
        elif event == "LLM_CALLING" and int(data.get("attempt") or 1) > 1:
            ctx.workflow = await ctx.workflow_service.resume_stage(
                ctx.workflow, WorkflowStatus.PLANNING_COURSE
            )

        await ctx.workflow_service.record_event(
            ctx.workflow,
            event_type=event_category,
            event=public_event,
            stage=PLANNING_STAGE_NAME,
            message=message,
            metadata={key: value for key, value in data.items() if value is not None},
        )

    return emit


async def _run_course_planning(ctx: WorkflowContext) -> None:
    """Susun konteks dan jalankan Course Planning Service (BE-14.3)."""
    if ctx.course_plan_service is None or ctx.planner is None:
        raise RuntimeError(
            "tahap course planning memerlukan CoursePlanService dan CoursePlanner"
        )

    ctx.planning_request = await ctx.course_plan_service.prepare_planning(
        workflow=ctx.workflow, instruction=ctx.instruction
    )
    ctx.planned_plan = await ctx.planner.generate(
        ctx.planning_request, emit_event=_planning_emitter(ctx)
    )


async def _run_plan_validation(ctx: WorkflowContext) -> None:
    """Validasi akademik lalu simpan hasil sebagai versi DRAFT baru."""
    if (
        ctx.course_plan_service is None
        or ctx.planning_request is None
        or ctx.planned_plan is None
    ):
        raise RuntimeError("tahap validasi memerlukan hasil perencanaan")

    record = await ctx.course_plan_service.store_planned_plan(
        workflow=ctx.workflow,
        request=ctx.planning_request,
        planned=ctx.planned_plan,
    )
    issues = (record.validation_result or {}).get("issues") or []

    await ctx.workflow_service.record_event(
        ctx.workflow,
        event_type=EventType.AKTIVITAS_AGENT,
        event=EVENT_PLAN_GENERATED,
        stage=PLAN_VALIDATION_STAGE_NAME,
        message=f"Course plan versi {record.version} tersimpan.",
        metadata={
            "version": record.version,
            "course_plan_id": record.id,
            "validation_passed": record.validation_passed,
            "issues": len(issues),
        },
    )



PLANNING_COURSE_STAGE = WorkflowStage(
    WorkflowStatus.PLANNING_COURSE, _run_course_planning
)
PLAN_VALIDATION_STAGE = WorkflowStage(
    WorkflowStatus.VALIDATING, _run_plan_validation
)

#: Urutan tahap generate/regenerate course plan: PLANNING_COURSE → VALIDATING.
COURSE_PLANNING_STAGES: tuple[WorkflowStage, ...] = (
    PLANNING_COURSE_STAGE,
    PLAN_VALIDATION_STAGE,
)

# --- Tahap: eksekusi ke Moodle (BE-17.1) -------------------------------------

#: Nama tahap eksekusi pada event (sama dengan ``stage_name`` domain).
EXECUTION_STAGE_NAME = stage_name(WorkflowStatus.EXECUTING_TO_MOODLE) or (
    "moodle_execution"
)


async def _run_execution(ctx: WorkflowContext) -> None:
    """Jalankan eksekusi struktur course plan yang sudah dibuat route (BE-17.1).

    Prasyarat dan pembuatan ``MoodleExecution`` berstatus ``PENDING`` dilakukan
    endpoint ``POST /workflows/{id}/executions`` sebelum runner dijadwalkan,
    sehingga tahap ini hanya menjalankan operasi yang belum berhasil dan
    mencatat satu event ``OPERASI_MOODLE`` per operasi.
    """
    if ctx.execution_service is None or ctx.execution_id is None:
        raise RuntimeError("tahap eksekusi memerlukan ExecutionService dan execution_id")

    async def emit(*, event: str, message: str, metadata: dict | None = None) -> None:
        await ctx.workflow_service.record_event(
            ctx.workflow,
            event_type=EventType.OPERASI_MOODLE,
            event=event,
            stage=EXECUTION_STAGE_NAME,
            message=message,
            metadata=metadata,
        )

    await ctx.execution_service.execute(
        execution_id=ctx.execution_id,
        owner_id=ctx.owner_id,
        emit_event=emit,
    )


EXECUTION_STAGE = WorkflowStage(
    WorkflowStatus.EXECUTING_TO_MOODLE, _run_execution
)

#: Run eksekusi: EXECUTING_TO_MOODLE. Sukses kembali ke WAITING_FOR_REVIEW (DL-012).
EXECUTION_STAGES: tuple[WorkflowStage, ...] = (EXECUTION_STAGE,)


# --- Eksekusi ----------------------------------------------------------------


async def execute_workflow(
    *,
    workflow: WorkflowRecord,
    stages: tuple[WorkflowStage, ...],
    workflow_service: WorkflowService,
    rps_service: RPSService,
    course_plan_service: CoursePlanService | None = None,
    planner: CoursePlanner | None = None,
    instruction: str | None = None,
    execution_service: ExecutionService | None = None,
    execution_id: str | None = None,
) -> None:
    """Jalankan deretan tahap pada satu workflow.

    Kegagalan tahap menghentikan rangkaian, menandai workflow ``FAILED``, dan
    menulis satu event kegagalan (kecuali event itu sudah ditulis oleh service
    yang gagal). Rangkaian yang selesai berakhir di ``WAITING_FOR_REVIEW``
    (DL-012), bukan ``COMPLETED``. Tidak ada exception yang dilempar ke
    pemanggil background.
    """
    ctx = WorkflowContext(
        workflow=workflow,
        workflow_service=workflow_service,
        rps_service=rps_service,
        course_plan_service=course_plan_service,
        planner=planner,
        instruction=instruction,
        execution_service=execution_service,
        execution_id=execution_id,
    )
    ctx.workflow = await workflow_service.begin_run(workflow, total=len(stages))

    for stage in stages:
        ctx.workflow = await workflow_service.begin_stage(ctx.workflow, stage.status)
        try:
            await stage.handler(ctx)
        except CoursePlanDomainError as exc:
            await workflow_service.fail_run(
                ctx.workflow,
                stage=stage.name,
                message=exc.public_message,
                emit_event=not ctx.failure_emitted,
            )
            return
        except RPSDomainError as exc:
            await workflow_service.fail_run(
                ctx.workflow,
                stage=stage.name,
                message=exc.public_reason,
                emit_event=not ctx.failure_emitted,
            )
            return
        except ExecutionDomainError as exc:
            await workflow_service.fail_run(
                ctx.workflow,
                stage=stage.name,
                message=exc.public_message,
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

    # Rangkaian selesai; workflow menunggu tindakan dosen (DL-012).
    await workflow_service.wait_for_review(ctx.workflow)


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


async def run_course_planning_workflow(
    *,
    workflow_id: str,
    owner_id: str,
    instruction: str | None = None,
    planner: CoursePlanner | None = None,
) -> None:
    """Jalankan generate/regenerate course plan di background (BE-14.3).

    Route sudah mengklaim workflow (:meth:`WorkflowService.claim_planning`)
    sebelum menjadwalkan fungsi ini, sehingga dua permintaan tidak dapat
    memulai dua run. ``planner`` dapat diganti pengujian; nilai bawaannya
    :func:`~src.services.course_plan.planner.get_course_planner`.

    Seluruh kegagalan ditelan dan dilaporkan lewat status workflow, event, dan
    log — tidak ada client yang menunggu pekerjaan background.
    """
    # Import lokal memutus siklus impor paket: workflow/__init__ mengekspor
    # orkestrator, sedangkan course_plan.service mengimpor workflow domain/service.
    from src.services.course_plan.service import CoursePlanService

    session_factory = get_session_factory()
    async with session_factory() as session:
        workflow_service = WorkflowService.from_session(session)
        rps_service = RPSService.from_session(session)
        course_plan_service = CoursePlanService.from_session(session)
        try:
            workflow = await workflow_service.get_workflow(
                workflow_id=workflow_id, owner_id=owner_id
            )
            try:
                active_planner = planner or get_course_planner()
            except LLMProviderError as exc:
                # Konfigurasi provider salah (mis. nama provider tidak dikenal).
                # Kegagalan ini terjadi sebelum tahap berjalan, jadi workflow
                # harus tetap ditutup sebagai FAILED, bukan menggantung di
                # status klaim PLANNING_COURSE.
                await workflow_service.fail_run(
                    workflow,
                    stage=PLANNING_STAGE_NAME,
                    message=exc.public_message,
                )
                logger.warning(
                    "course planning workflow %s gagal menyiapkan planner: %s",
                    workflow_id,
                    exc,
                )
                return

            await execute_workflow(
                workflow=workflow,
                stages=COURSE_PLANNING_STAGES,
                workflow_service=workflow_service,
                rps_service=rps_service,
                course_plan_service=course_plan_service,
                planner=active_planner,
                instruction=instruction,
            )
        except CoursePlanDomainError as exc:
            logger.warning(
                "course planning workflow %s gagal: %s", workflow_id, exc.log_message
            )
        except RPSDomainError as exc:
            logger.warning(
                "course planning workflow %s gagal: %s", workflow_id, exc.log_message
            )
        except WorkflowDomainError as exc:
            logger.warning(
                "course planning workflow %s gagal: %s", workflow_id, exc.log_message
            )
        except Exception:
            logger.exception(
                "course planning workflow %s gagal di luar error domain", workflow_id
            )
        else:
            logger.info("course planning workflow %s selesai", workflow_id)


async def run_execution_workflow(
    *,
    workflow_id: str,
    owner_id: str,
    execution_id: str,
    moodle: MoodleIntegrationService | None = None,
) -> None:
    """Jalankan tahap ``EXECUTING_TO_MOODLE`` di background (BE-17.1).

    Endpoint ``POST /workflows/{id}/executions`` sudah memeriksa prasyarat,
    mengklaim workflow, dan membuat ``MoodleExecution`` ``PENDING`` sebelum
    fungsi ini dijadwalkan. ``moodle`` dapat diganti pengujian; nilai bawaannya
    client Moodle dari konfigurasi, ditutup setelah run selesai.

    Seluruh kegagalan ditelan dan dilaporkan lewat status workflow, eksekusi,
    event, dan log — tidak ada client yang menunggu pekerjaan background.
    """
    # Import lokal memutus siklus impor paket (pola yang sama dengan course
    # planning): execution.service mengimpor WorkflowService, bukan orkestrator.
    from src.services.execution.service import ExecutionService

    client: MoodleClient | None = None
    try:
        if moodle is None:
            client = MoodleClient.from_settings(get_settings())
            moodle = MoodleIntegrationService(client)

        session_factory = get_session_factory()
        async with session_factory() as session:
            workflow_service = WorkflowService.from_session(session)
            rps_service = RPSService.from_session(session)
            execution_service = ExecutionService.from_session(
                session, moodle=moodle
            )
            workflow = await workflow_service.get_workflow(
                workflow_id=workflow_id, owner_id=owner_id
            )
            await execute_workflow(
                workflow=workflow,
                stages=EXECUTION_STAGES,
                workflow_service=workflow_service,
                rps_service=rps_service,
                execution_service=execution_service,
                execution_id=execution_id,
            )
    except ExecutionDomainError as exc:
        logger.warning(
            "execution workflow %s gagal: %s", workflow_id, exc.log_message
        )
    except WorkflowDomainError as exc:
        logger.warning(
            "execution workflow %s gagal: %s", workflow_id, exc.log_message
        )
    except Exception:
        logger.exception(
            "execution workflow %s gagal di luar error domain", workflow_id
        )
    else:
        logger.info("execution workflow %s selesai", workflow_id)
    finally:
        if client is not None:
            await client.aclose()


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
