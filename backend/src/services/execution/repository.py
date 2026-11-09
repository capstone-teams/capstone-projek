"""Akses data eksekusi Moodle (BE-16.1/BE-17.1).

Satu-satunya tempat query tabel ``moodle_executions`` dan
``execution_operations``. Repository hanya menjawab "bagaimana eksekusi dan
operasinya diambil/disimpan?", tanpa aturan prasyarat maupun urutan eksekusi —
keduanya berada di :mod:`src.services.execution.service`.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.course_plan_week import CoursePlanWeek
from src.models.execution_operation import (
    ExecutionOperation as ExecutionOperationEntity,
)
from src.models.execution_operation import OperationStatus, OperationType
from src.models.moodle_execution import (
    ExecutionScope,
    ExecutionStatus,
    MoodleExecution as MoodleExecutionEntity,
)
from src.services.execution.domain import (
    ExecutionOperationRecord,
    ExecutionRecord,
    PlannedOperation,
)

__all__ = ["ExecutionRepository"]


class ExecutionRepository:
    """Akses data eksekusi di atas ``AsyncSession`` yang di-inject dari luar."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        workflow_id: str,
        course_plan_id: str,
        moodle_course_id: int,
        scope: ExecutionScope,
        operations: Sequence[PlannedOperation],
    ) -> ExecutionRecord:
        """Simpan satu eksekusi ``PENDING`` beserta seluruh operasinya."""
        entity = MoodleExecutionEntity(
            workflow_id=workflow_id,
            course_plan_id=course_plan_id,
            moodle_course_id=moodle_course_id,
            scope=scope,
            status=ExecutionStatus.PENDING,
        )
        self._session.add(entity)
        await self._session.flush()

        for planned in operations:
            self._session.add(
                ExecutionOperationEntity(
                    execution_id=entity.id,
                    course_plan_week_id=planned.course_plan_week_id,
                    content_id=planned.content_id,
                    operation_type=planned.operation_type,
                    idempotency_key=planned.idempotency_key,
                    status=OperationStatus.PENDING,
                )
            )

        await self._session.commit()
        stored = await self.get(entity.id)
        if stored is None:  # pragma: no cover - baris baru tidak mungkin hilang
            raise RuntimeError("eksekusi gagal dibaca setelah disimpan")
        return stored

    async def get(self, execution_id: str) -> ExecutionRecord | None:
        entity = await self._session.get(MoodleExecutionEntity, execution_id)
        if entity is None:
            return None
        return await self._to_record(entity)

    async def get_for_workflow(
        self, workflow_id: str, execution_id: str
    ) -> ExecutionRecord | None:
        """Eksekusi milik workflow tertentu; scoping owner dilakukan pemanggil."""
        entity = (
            await self._session.execute(
                select(MoodleExecutionEntity).where(
                    MoodleExecutionEntity.id == execution_id,
                    MoodleExecutionEntity.workflow_id == workflow_id,
                )
            )
        ).scalar_one_or_none()
        if entity is None:
            return None
        return await self._to_record(entity)

    async def list_for_workflow(self, workflow_id: str) -> list[ExecutionRecord]:
        """Riwayat eksekusi satu workflow, terbaru lebih dulu."""
        entities = (
            (
                await self._session.execute(
                    select(MoodleExecutionEntity)
                    .where(MoodleExecutionEntity.workflow_id == workflow_id)
                    .order_by(MoodleExecutionEntity.created_at.desc())
                )
            )
            .scalars()
            .all()
        )
        return [await self._to_record(entity) for entity in entities]

    async def mark_running(self, execution_id: str, *, at: datetime) -> None:
        entity = await self._session.get(MoodleExecutionEntity, execution_id)
        if entity is None:
            return
        entity.status = ExecutionStatus.RUNNING
        entity.started_at = at
        entity.completed_at = None
        entity.error_message = None
        await self._session.commit()

    async def reset_for_retry(self, execution_id: str) -> None:
        """Kembalikan eksekusi gagal ke ``PENDING`` sebelum dijadwalkan ulang."""
        entity = await self._session.get(MoodleExecutionEntity, execution_id)
        if entity is None:
            return
        entity.status = ExecutionStatus.PENDING
        entity.error_message = None
        entity.completed_at = None
        await self._session.commit()

    async def finish(
        self,
        execution_id: str,
        *,
        status: ExecutionStatus,
        at: datetime,
        readback: dict | None = None,
        error_message: str | None = None,
    ) -> None:
        entity = await self._session.get(MoodleExecutionEntity, execution_id)
        if entity is None:
            return
        entity.status = status
        entity.readback = readback
        entity.error_message = error_message
        entity.completed_at = at
        await self._session.commit()

    async def start_operation(self, operation_id: str) -> None:
        entity = await self._session.get(ExecutionOperationEntity, operation_id)
        if entity is None:
            return
        entity.status = OperationStatus.RUNNING
        entity.error_message = None
        await self._session.commit()

    async def finish_operation(
        self,
        operation_id: str,
        *,
        status: OperationStatus,
        moodle_object_id: str | None = None,
        error_message: str | None = None,
        retry_count: int | None = None,
    ) -> None:
        entity = await self._session.get(ExecutionOperationEntity, operation_id)
        if entity is None:
            return
        entity.status = status
        entity.moodle_object_id = moodle_object_id
        entity.error_message = error_message
        if retry_count is not None:
            entity.retry_count = retry_count
        await self._session.commit()

    # --- Mapping ----------------------------------------------------------

    async def _to_record(self, entity: MoodleExecutionEntity) -> ExecutionRecord:
        rows = (
            await self._session.execute(
                select(ExecutionOperationEntity, CoursePlanWeek.week_number)
                .outerjoin(
                    CoursePlanWeek,
                    ExecutionOperationEntity.course_plan_week_id == CoursePlanWeek.id,
                )
                .where(ExecutionOperationEntity.execution_id == entity.id)
                .order_by(
                    CoursePlanWeek.week_number.asc().nulls_last(),
                    ExecutionOperationEntity.created_at.asc(),
                    ExecutionOperationEntity.id.asc(),
                )
            )
        ).all()
        operations = tuple(
            _to_operation(operation, week_number) for operation, week_number in rows
        )
        return ExecutionRecord(
            id=entity.id,
            workflow_id=entity.workflow_id,
            course_plan_id=entity.course_plan_id,
            moodle_course_id=entity.moodle_course_id,
            scope=entity.scope,
            status=entity.status,
            error_message=entity.error_message,
            readback=entity.readback,
            started_at=entity.started_at,
            completed_at=entity.completed_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            operations=operations,
        )


def _to_operation(
    entity: ExecutionOperationEntity, week_number: int | None
) -> ExecutionOperationRecord:
    return ExecutionOperationRecord(
        id=entity.id,
        execution_id=entity.execution_id,
        course_plan_week_id=entity.course_plan_week_id,
        content_id=entity.content_id,
        operation_type=OperationType(entity.operation_type),
        idempotency_key=entity.idempotency_key,
        moodle_object_id=entity.moodle_object_id,
        status=OperationStatus(entity.status),
        error_message=entity.error_message,
        retry_count=entity.retry_count,
        week_number=week_number,
    )
