"""Akses data workflow (BE-11.1).

Satu-satunya tempat query tabel ``workflows`` dan ``workflow_events``.
Repository hanya menjawab "bagaimana data workflow diambil/disimpan?", tanpa
aturan state machine maupun keputusan orkestrasi — keduanya berada di
:mod:`src.services.workflow.service`.

Pemetaan entity ↔ domain berada di modul ini (pola yang sama dengan
:mod:`src.services.instructor.repository`) supaya domain tetap bebas SQLAlchemy.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.workflow import Workflow as WorkflowEntity
from src.models.workflow_event import WorkflowEvent as WorkflowEventEntity
from src.services.workflow.domain import WorkflowEventRecord, WorkflowRecord

__all__ = ["WorkflowRepository"]


class WorkflowRepository:
    """Akses data workflow di atas ``AsyncSession`` yang di-inject dari luar."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, workflow: WorkflowRecord) -> WorkflowRecord:
        """Simpan workflow baru dan kembalikan hasil persist."""
        entity = _apply_to_entity(workflow, WorkflowEntity())
        self._session.add(entity)
        await self._session.commit()
        await self._session.refresh(entity)
        return _to_domain(entity)

    async def get_by_id(self, workflow_id: str) -> WorkflowRecord | None:
        """Ambil workflow berdasarkan identifier; ``None`` bila tidak ada."""
        entity = await self._session.get(WorkflowEntity, workflow_id)
        return _to_domain(entity) if entity is not None else None

    async def find_by_id_and_owner(
        self, workflow_id: str, owner_id: str
    ) -> WorkflowRecord | None:
        """Ambil workflow milik owner tertentu.

        Scoping owner dilakukan di query — bukan dengan memeriksa hasilnya di
        service — supaya workflow milik dosen lain tidak pernah termuat ke
        dalam proses ini.
        """
        statement = select(WorkflowEntity).where(
            WorkflowEntity.id == workflow_id,
            WorkflowEntity.owner_id == owner_id,
        )
        entity = (await self._session.execute(statement)).scalar_one_or_none()
        return _to_domain(entity) if entity is not None else None

    async def list_by_owner(self, owner_id: str) -> list[WorkflowRecord]:
        """Seluruh workflow milik satu dosen, terbaru lebih dulu."""
        statement = (
            select(WorkflowEntity)
            .where(WorkflowEntity.owner_id == owner_id)
            .order_by(WorkflowEntity.created_at.desc())
        )
        entities = (await self._session.execute(statement)).scalars().all()
        return [_to_domain(entity) for entity in entities]

    async def update(self, workflow: WorkflowRecord) -> WorkflowRecord | None:
        """Perbarui workflow yang sudah dipersist; ``None`` bila barisnya tidak ada."""
        if workflow.id is None:
            raise ValueError(
                "update memerlukan workflow yang sudah dipersist (id tidak boleh kosong)"
            )

        entity = await self._session.get(WorkflowEntity, workflow.id)
        if entity is None:
            return None

        _apply_to_entity(workflow, entity)
        await self._session.commit()
        await self._session.refresh(entity)
        return _to_domain(entity)

    async def create_event(self, event: WorkflowEventRecord) -> WorkflowEventRecord:
        """Simpan satu event workflow dan kembalikan hasil persist."""
        entity = WorkflowEventEntity(
            workflow_id=event.workflow_id,
            event_type=event.event_type,
            event=event.event,
            stage=event.stage,
            message=event.message,
            metadata_=event.metadata_,
        )
        if event.id is not None:
            entity.id = event.id
        self._session.add(entity)
        await self._session.commit()
        await self._session.refresh(entity)
        return _event_to_domain(entity)

    async def list_events(self, workflow_id: str) -> list[WorkflowEventRecord]:
        """Riwayat event satu workflow, dari yang paling lama (design-api §16.3).

        ``created_at`` adalah waktu database saat event disimpan; identifier
        menjadi tie-breaker deterministik bila dua event tercatat pada
        microsecond yang sama.
        """
        statement = (
            select(WorkflowEventEntity)
            .where(WorkflowEventEntity.workflow_id == workflow_id)
            .order_by(
                WorkflowEventEntity.created_at.asc(),
                WorkflowEventEntity.id.asc(),
            )
        )
        entities = (await self._session.execute(statement)).scalars().all()
        return [_event_to_domain(entity) for entity in entities]


def _to_domain(entity: WorkflowEntity) -> WorkflowRecord:
    return WorkflowRecord(
        id=entity.id,
        owner_id=entity.owner_id,
        rps_id=entity.rps_id,
        status=entity.status,
        moodle_course_id=entity.moodle_course_id,
        model_name=entity.model_name,
        progress_completed=entity.progress_completed,
        progress_total=entity.progress_total,
        started_at=entity.started_at,
        completed_at=entity.completed_at,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def _apply_to_entity(workflow: WorkflowRecord, entity: WorkflowEntity) -> WorkflowEntity:
    if workflow.id is not None:
        entity.id = workflow.id
    entity.owner_id = workflow.owner_id
    entity.rps_id = workflow.rps_id
    entity.status = workflow.status
    entity.moodle_course_id = workflow.moodle_course_id
    entity.model_name = workflow.model_name
    entity.progress_completed = workflow.progress_completed
    entity.progress_total = workflow.progress_total
    entity.started_at = workflow.started_at
    entity.completed_at = workflow.completed_at
    return entity


def _event_to_domain(entity: WorkflowEventEntity) -> WorkflowEventRecord:
    return WorkflowEventRecord(
        id=entity.id,
        workflow_id=entity.workflow_id,
        event_type=entity.event_type,
        event=entity.event,
        stage=entity.stage,
        message=entity.message,
        metadata_=entity.metadata_,
        created_at=entity.created_at,
    )
