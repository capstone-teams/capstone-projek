from __future__ import annotations

import enum
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from dataclasses import dataclass, replace
from typing import Protocol, TypeVar

from src.services.moodle_adapter_exceptions import (
    MoodleCapabilityUnavailableError,
    MoodleEntityNotFoundError,
    MoodleOperationFailedError,
)

T = TypeVar("T")

MAX_ERROR_MESSAGE_LENGTH = 500


class MoodleExecutionStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    RETRYING = "RETRYING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass(frozen=True)
class MoodleExecution:
    id: uuid.UUID
    operation: str
    entity_type: str
    internal_id: str
    status: MoodleExecutionStatus = MoodleExecutionStatus.PENDING
    attempts: int = 0
    moodle_id: int | None = None
    error_category: str | None = None
    error_message: str | None = None


class IMoodleExecutionRepository(Protocol):
    async def add(self, execution: MoodleExecution) -> None: ...

    async def update(self, execution: MoodleExecution) -> None: ...

    async def get(self, execution_id: uuid.UUID) -> MoodleExecution | None: ...

    async def list_for_entity(
        self, entity_type: str, internal_id: str
    ) -> list[MoodleExecution]: ...


class InMemoryMoodleExecutionRepository:
    def __init__(self) -> None:
        self._executions: dict[uuid.UUID, MoodleExecution] = {}

    async def add(self, execution: MoodleExecution) -> None:
        self._executions[execution.id] = execution

    async def update(self, execution: MoodleExecution) -> None:
        if execution.id not in self._executions:
            raise MoodleEntityNotFoundError(f"Execution '{execution.id}' tidak ditemukan.")
        self._executions[execution.id] = execution

    async def get(self, execution_id: uuid.UUID) -> MoodleExecution | None:
        return self._executions.get(execution_id)

    async def list_for_entity(self, entity_type: str, internal_id: str) -> list[MoodleExecution]:
        return [
            execution
            for execution in self._executions.values()
            if execution.entity_type == entity_type and execution.internal_id == internal_id
        ]


class _Progress:
    def __init__(self, execution: MoodleExecution) -> None:
        self.execution = execution


_current_progress: ContextVar[_Progress | None] = ContextVar("moodle_execution", default=None)


def describe_error(error: Exception) -> tuple[str, str]:
    message = str(error)[:MAX_ERROR_MESSAGE_LENGTH]
    if isinstance(error, MoodleOperationFailedError):
        return error.category.value, message
    if isinstance(error, MoodleCapabilityUnavailableError):
        return "capability_unavailable", message
    if isinstance(error, MoodleEntityNotFoundError):
        return "not_found", message
    if isinstance(error, ValueError):
        return "validation", message
    return "unexpected", message


class MoodleExecutionTracker:
    def __init__(self, repository: IMoodleExecutionRepository) -> None:
        self._repository = repository

    async def run(
        self,
        operation: str,
        entity_type: str,
        internal_id: str,
        action: Callable[[], Awaitable[T]],
        *,
        moodle_id_of: Callable[[T], int | None] | None = None,
    ) -> T:
        pending = MoodleExecution(
            id=uuid.uuid4(),
            operation=operation,
            entity_type=entity_type,
            internal_id=internal_id,
        )
        await self._repository.add(pending)
        progress = _Progress(replace(pending, status=MoodleExecutionStatus.RUNNING, attempts=1))
        await self._repository.update(progress.execution)

        token = _current_progress.set(progress)
        try:
            result = await action()
        except Exception as error:
            category, message = describe_error(error)
            progress.execution = replace(
                progress.execution,
                status=MoodleExecutionStatus.FAILED,
                error_category=category,
                error_message=message,
            )
            await self._repository.update(progress.execution)
            raise
        finally:
            _current_progress.reset(token)

        moodle_id = moodle_id_of(result) if moodle_id_of is not None else None
        progress.execution = replace(
            progress.execution,
            status=MoodleExecutionStatus.SUCCESS,
            moodle_id=moodle_id,
            error_category=None,
            error_message=None,
        )
        await self._repository.update(progress.execution)
        return result

    async def observe_retry(self, error: MoodleOperationFailedError) -> None:
        progress = _current_progress.get()
        if progress is None:
            return
        category, message = describe_error(error)
        progress.execution = replace(
            progress.execution,
            status=MoodleExecutionStatus.RETRYING,
            attempts=progress.execution.attempts + 1,
            error_category=category,
            error_message=message,
        )
        await self._repository.update(progress.execution)