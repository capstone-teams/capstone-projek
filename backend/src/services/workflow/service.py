"""Operasi aplikasi workflow (BE-11.2).

Service ini menjawab "perubahan apa yang boleh terjadi pada sebuah workflow dan
event apa yang harus tercatat?", bukan "bagaimana barisnya disimpan?" (itu
:class:`~src.services.workflow.repository.WorkflowRepository`) dan bukan
"tahap apa yang dijalankan berikutnya?" (itu
:mod:`src.services.workflow.orchestrator`).

Pemisahan itu disengaja: orkestrator memegang urutan tahap, sedangkan seluruh
transisi status dan penulisan event melewati service ini — satu tempat untuk
aturan "setiap perubahan tahap, retry, dan kegagalan tercatat sebagai event"
(issue BE-11.2). Setelah event tersimpan, service menerbitkannya ke broker
sehingga klien WebSocket menerima payload yang sama dengan riwayat HTTP.
"""

from __future__ import annotations

import shortuuid
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import get_settings
from src.models.workflow import WorkflowStatus
from src.models.workflow_event import EventType
from src.services.workflow.broker import WorkflowEventBroker, workflow_event_broker
from src.services.workflow.domain import (
    WorkflowEventRecord,
    WorkflowRecord,
    stage_name,
)
from src.services.workflow.errors import WorkflowNotFoundError, WorkflowValidationError
from src.services.workflow.repository import WorkflowRepository
from src.services.workflow.validation import normalize_identifier

__all__ = ["WorkflowService"]

# Nama event publik (design-api §17). Selalu berpola ``WORKFLOW_*`` sehingga
# client memakai satu parser untuk riwayat HTTP dan frame WebSocket.
EVENT_STARTED = "WORKFLOW_STARTED"
EVENT_STAGE_STARTED = "WORKFLOW_STAGE_STARTED"
EVENT_STAGE_PROGRESS = "WORKFLOW_STAGE_PROGRESS"
EVENT_STAGE_COMPLETED = "WORKFLOW_STAGE_COMPLETED"
EVENT_RETRY = "WORKFLOW_RETRY"
EVENT_COMPLETED = "WORKFLOW_COMPLETED"
EVENT_FAILED = "WORKFLOW_FAILED"

# Label tahap untuk pesan event yang dapat dibaca dosen. Nama tahap pada API
# tetap versi Inggris (design-api §16), sedangkan pesannya berbahasa Indonesia.
STAGE_LABELS: dict[WorkflowStatus, str] = {
    WorkflowStatus.PROCESSING_RPS: "pemrosesan RPS",
    WorkflowStatus.ANALYZING_RPS: "analisis RPS",
    WorkflowStatus.PLANNING_COURSE: "penyusunan rencana pembelajaran",
    WorkflowStatus.GENERATING_CONTENT: "generasi konten",
    WorkflowStatus.VALIDATING: "validasi",
    WorkflowStatus.WAITING_FOR_REVIEW: "peninjauan dosen",
    WorkflowStatus.EXECUTING_TO_MOODLE: "eksekusi ke Moodle",
    WorkflowStatus.VERIFYING: "verifikasi",
}


class WorkflowService:
    """Operasi aplikasi workflow di atas satu ``AsyncSession``."""

    def __init__(
        self,
        repository: WorkflowRepository,
        *,
        broker: WorkflowEventBroker | None = None,
    ) -> None:
        self._repository = repository
        self._broker = broker or workflow_event_broker

    @classmethod
    def from_session(
        cls,
        session: AsyncSession,
        *,
        broker: WorkflowEventBroker | None = None,
    ) -> WorkflowService:
        """Bangun service dengan dependency bawaan.

        ``broker`` dapat diganti pengujian supaya langganan event tidak bocor
        antar-test.
        """
        return cls(WorkflowRepository(session), broker=broker)

    @staticmethod
    def new_id() -> str:
        """Identifier workflow baru.

        Dipakai pemanggil yang harus menentukan id **sebelum** baris workflow
        dibuat — endpoint reanalyze meneruskan id yang sama ke
        ``RPSService.begin_analysis`` agar RPS dan workflow menunjuk workflow
        yang sama (issue BE-11.2).
        """
        return shortuuid.uuid()

    async def create_for_rps(
        self,
        *,
        owner_id: str,
        rps_id: str,
        total: int,
        workflow_id: str | None = None,
    ) -> WorkflowRecord:
        """Workflow baru berstatus ``QUEUED`` untuk sebuah RPS."""
        return await self._repository.create(
            WorkflowRecord.create(
                id=workflow_id,
                owner_id=owner_id,
                rps_id=rps_id,
                progress_total=total,
            )
        )

    async def ensure_for_rps(
        self,
        *,
        owner_id: str,
        rps_id: str,
        workflow_id: str,
        total: int,
    ) -> WorkflowRecord:
        """Ambil workflow yang sudah ada, atau buat dengan ``workflow_id`` itu.

        Reanalyze memakai workflow yang sama (issue BE-11.2). Dokumen lama yang
        dianalisis sebelum tabel ``workflows`` ada hanya menyimpan id pada
        ``rps.workflow_id``; barisnya dibentuk di sini saat reanalyze pertama
        sehingga riwayat berikutnya tercatat pada workflow yang sama.
        """
        identifier = normalize_identifier(workflow_id)
        if identifier is None:
            raise WorkflowValidationError("workflow_id", "wajib diisi")

        existing = await self._repository.get_by_id(identifier)
        if existing is not None:
            if existing.owner_id != owner_id or existing.rps_id != rps_id:
                # Jangan pernah memakai workflow milik dosen/RPS lain, sekalipun
                # id-nya tercatat pada dokumen yang sedang diproses.
                raise WorkflowNotFoundError(identifier)
            return existing

        return await self.create_for_rps(
            owner_id=owner_id,
            rps_id=rps_id,
            total=total,
            workflow_id=identifier,
        )

    async def get_workflow(self, *, workflow_id: str, owner_id: str) -> WorkflowRecord:
        """Workflow milik dosen yang login; ``404`` bila tidak ada/ milik orang lain."""
        identifier = normalize_identifier(workflow_id)
        if identifier is None:
            raise WorkflowNotFoundError(workflow_id)

        workflow = await self._repository.find_by_id_and_owner(identifier, owner_id)
        if workflow is None:
            raise WorkflowNotFoundError(identifier)
        return workflow

    async def list_workflows(self, *, owner_id: str) -> list[WorkflowRecord]:
        """Seluruh workflow milik dosen, terbaru lebih dulu."""
        return await self._repository.list_by_owner(owner_id)

    async def list_events(
        self, *, workflow_id: str, owner_id: str
    ) -> list[WorkflowEventRecord]:
        """Riwayat event workflow, dari yang paling lama (design-api §16.3)."""
        workflow = await self.get_workflow(workflow_id=workflow_id, owner_id=owner_id)
        return await self._repository.list_events(workflow.id or "")

    async def set_moodle_course_id(
        self,
        *,
        workflow_id: str,
        owner_id: str,
        moodle_course_id: int | None,
    ) -> WorkflowRecord:
        """Simpan course target Moodle pada workflow (issue BE-11.3)."""
        workflow = await self.get_workflow(workflow_id=workflow_id, owner_id=owner_id)
        workflow.set_moodle_course_id(moodle_course_id)
        updated = await self._repository.update(workflow)
        if updated is None:
            raise WorkflowNotFoundError(workflow_id)
        return updated

    # --- Lifecycle yang dipanggil orkestrator -----------------------------

    async def begin_run(self, workflow: WorkflowRecord, *, total: int) -> WorkflowRecord:
        """Mulai satu run dan catat event ``WORKFLOW_STARTED``."""
        settings = get_settings()
        workflow.begin_run(
            total=total,
            model_name=settings.llm_model_for(settings.llm_provider) or None,
        )
        updated = await self._update(workflow)
        await self._record(
            updated,
            event_type=EventType.PERUBAHAN_TAHAP,
            event=EVENT_STARTED,
            stage=None,
            message="Workflow dimulai.",
        )
        return updated

    async def begin_stage(
        self, workflow: WorkflowRecord, status: WorkflowStatus
    ) -> WorkflowRecord:
        """Masuk ke sebuah tahap dan catat ``WORKFLOW_STAGE_STARTED``."""
        workflow.enter_stage(status)
        updated = await self._update(workflow)
        await self._record(
            updated,
            event_type=EventType.PERUBAHAN_TAHAP,
            event=EVENT_STAGE_STARTED,
            stage=stage_name(status),
            message=f"Tahap {_label(status)} dimulai.",
        )
        return updated

    async def complete_stage(
        self, workflow: WorkflowRecord, status: WorkflowStatus
    ) -> WorkflowRecord:
        """Tandai satu tahap selesai dan catat ``WORKFLOW_STAGE_COMPLETED``."""
        workflow.complete_stage()
        updated = await self._update(workflow)
        await self._record(
            updated,
            event_type=EventType.PERUBAHAN_TAHAP,
            event=EVENT_STAGE_COMPLETED,
            stage=stage_name(status),
            message=f"Tahap {_label(status)} selesai.",
        )
        return updated

    async def complete_run(self, workflow: WorkflowRecord) -> WorkflowRecord:
        """Seluruh tahap selesai dan catat ``WORKFLOW_COMPLETED``."""
        workflow.complete_run()
        updated = await self._update(workflow)
        await self._record(
            updated,
            event_type=EventType.PERUBAHAN_TAHAP,
            event=EVENT_COMPLETED,
            stage=None,
            message="Workflow selesai.",
        )
        return updated

    async def fail_run(
        self,
        workflow: WorkflowRecord,
        *,
        stage: str | None,
        message: str,
        emit_event: bool = True,
    ) -> WorkflowRecord:
        """Workflow gagal; event ``WORKFLOW_FAILED`` ditulis kecuali sudah tercatat.

        Kegagalan di dalam service analisis sudah menerbitkan event
        ``ERROR_FAILURE`` (beserta metadata penyebabnya) sebelum exception naik.
        ``emit_event=False`` mencegah event kegagalan ganda untuk kejadian yang
        sama.
        """
        workflow.fail_run()
        updated = await self._update(workflow)
        if emit_event:
            await self._record(
                updated,
                event_type=EventType.ERROR_FAILURE,
                event=EVENT_FAILED,
                stage=stage,
                message=message,
            )
        return updated

    async def mark_retrying(self, workflow: WorkflowRecord) -> WorkflowRecord:
        """Tandai tahap sedang mencoba ulang (event ``RETRY_FIX`` ditulis terpisah)."""
        workflow.mark_retrying()
        return await self._update(workflow)

    async def resume_stage(
        self, workflow: WorkflowRecord, status: WorkflowStatus
    ) -> WorkflowRecord:
        """Kembali ke tahap kerja setelah percobaan ulang dimulai."""
        workflow.resume_stage(status)
        return await self._update(workflow)

    async def record_event(
        self,
        workflow: WorkflowRecord,
        *,
        event_type: EventType,
        event: str,
        stage: str | None,
        message: str | None = None,
        metadata: dict | None = None,
    ) -> WorkflowEventRecord:
        """Simpan satu event lalu terbitkan ke klien real-time."""
        return await self._record(
            workflow,
            event_type=event_type,
            event=event,
            stage=stage,
            message=message,
            metadata=metadata,
        )

    # --- Internal ---------------------------------------------------------

    async def _update(self, workflow: WorkflowRecord) -> WorkflowRecord:
        updated = await self._repository.update(workflow)
        if updated is None:
            raise WorkflowNotFoundError(workflow.id)
        return updated

    async def _record(
        self,
        workflow: WorkflowRecord,
        *,
        event_type: EventType,
        event: str,
        stage: str | None,
        message: str | None = None,
        metadata: dict | None = None,
    ) -> WorkflowEventRecord:
        """Simpan event beserta snapshot kemajuan, lalu publikasikan.

        Snapshot kemajuan ikut disimpan agar riwayat event tidak berubah ketika
        workflow berjalan lebih jauh — ``progress`` pada event adalah keadaan
        saat kejadian itu terjadi.
        """
        merged = {
            key: value for key, value in (metadata or {}).items() if value is not None
        }
        merged["progress_completed"] = workflow.progress_completed
        merged["progress_total"] = workflow.progress_total

        record = WorkflowEventRecord(
            workflow_id=workflow.id or "",
            event_type=event_type,
            event=event,
            stage=stage,
            message=message,
            metadata_=merged,
        )
        stored = await self._repository.create_event(record)
        self._broker.publish(stored.workflow_id, event_payload(stored))
        return stored


def event_payload(event: WorkflowEventRecord) -> dict:
    """Bentuk frame event untuk WebSocket (design-api §17).

    Bentuknya sama dengan item pada ``GET /workflows/{id}/events`` sehingga
    client memakai satu parser. Tidak ada credential, API key, isi prompt,
    maupun detail internal lain di payload.
    """
    metadata = event.metadata_ or {}
    progress = None
    if "progress_completed" in metadata and "progress_total" in metadata:
        progress = {
            "completed": metadata["progress_completed"],
            "total": metadata["progress_total"],
        }

    return {
        "event": event.event,
        "workflow_id": event.workflow_id,
        "stage": event.stage,
        "progress": progress,
        "message": event.message,
        "timestamp": event.created_at.isoformat() if event.created_at else None,
    }


def _label(status: WorkflowStatus) -> str:
    return STAGE_LABELS.get(status, status.value.lower())
