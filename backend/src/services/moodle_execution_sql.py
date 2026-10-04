from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.moodle_execution_record import MoodleExecutionRecord
from src.services.moodle_adapter_exceptions import MoodleEntityNotFoundError
from src.services.moodle_execution import MoodleExecution, MoodleExecutionStatus

__all__ = ["SqlMoodleExecutionRepository"]


class SqlMoodleExecutionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, execution: MoodleExecution) -> None:
        record = MoodleExecutionRecord(id=execution.id)
        _apply(execution, record)
        self._session.add(record)
        await self._session.commit()

    async def update(self, execution: MoodleExecution) -> None:
        record = await self._session.get(MoodleExecutionRecord, execution.id)
        if record is None:
            raise MoodleEntityNotFoundError(f"Execution '{execution.id}' tidak ditemukan.")
        _apply(execution, record)
        await self._session.commit()

    async def get(self, execution_id: uuid.UUID) -> MoodleExecution | None:
        record = await self._session.get(MoodleExecutionRecord, execution_id)
        return _to_domain(record) if record is not None else None

    async def list_for_entity(self, entity_type: str, internal_id: str) -> list[MoodleExecution]:
        statement = (
            select(MoodleExecutionRecord)
            .where(
                MoodleExecutionRecord.entity_type == entity_type,
                MoodleExecutionRecord.internal_id == internal_id,
            )
            .order_by(MoodleExecutionRecord.created_at)
        )
        records = (await self._session.execute(statement)).scalars().all()
        return [_to_domain(record) for record in records]


def _apply(execution: MoodleExecution, record: MoodleExecutionRecord) -> None:
    record.operation = execution.operation
    record.entity_type = execution.entity_type
    record.internal_id = execution.internal_id
    record.status = execution.status.value
    record.attempts = execution.attempts
    record.moodle_id = execution.moodle_id
    record.error_category = execution.error_category
    record.error_message = execution.error_message


def _to_domain(record: MoodleExecutionRecord) -> MoodleExecution:
    return MoodleExecution(
        id=record.id,
        operation=record.operation,
        entity_type=record.entity_type,
        internal_id=record.internal_id,
        status=MoodleExecutionStatus(record.status),
        attempts=record.attempts,
        moodle_id=record.moodle_id,
        error_category=record.error_category,
        error_message=record.error_message,
    )