import uuid
from dataclasses import replace

import pytest

from src.services.moodle_adapter_exceptions import (
    MoodleAuthenticationFailedError,
    MoodleEntityNotFoundError,
)
from src.services.moodle_execution import (
    MoodleExecution,
    MoodleExecutionStatus,
    MoodleExecutionTracker,
)
from src.services.moodle_execution_sql import SqlMoodleExecutionRepository


def new_execution(**overrides):
    values = {
        "id": uuid.uuid4(),
        "operation": "create_course",
        "entity_type": "course",
        "internal_id": "course_1",
    }
    values.update(overrides)
    return MoodleExecution(**values)


@pytest.mark.asyncio
async def test_add_and_get_round_trip(db_session):
    repo = SqlMoodleExecutionRepository(db_session)
    execution = new_execution()

    await repo.add(execution)

    stored = await repo.get(execution.id)
    assert stored == execution
    assert stored.status is MoodleExecutionStatus.PENDING


@pytest.mark.asyncio
async def test_get_unknown_execution_returns_none(db_session):
    repo = SqlMoodleExecutionRepository(db_session)

    assert await repo.get(uuid.uuid4()) is None


@pytest.mark.asyncio
async def test_update_persists_status_and_moodle_id(db_session):
    repo = SqlMoodleExecutionRepository(db_session)
    execution = new_execution()
    await repo.add(execution)

    updated = replace(
        execution, status=MoodleExecutionStatus.SUCCESS, attempts=2, moodle_id=42
    )
    await repo.update(updated)

    stored = await repo.get(execution.id)
    assert stored.status is MoodleExecutionStatus.SUCCESS
    assert stored.attempts == 2
    assert stored.moodle_id == 42


@pytest.mark.asyncio
async def test_update_unknown_execution_raises_not_found(db_session):
    repo = SqlMoodleExecutionRepository(db_session)

    with pytest.raises(MoodleEntityNotFoundError):
        await repo.update(new_execution())


@pytest.mark.asyncio
async def test_list_for_entity_returns_only_matching_executions(db_session):
    repo = SqlMoodleExecutionRepository(db_session)
    await repo.add(new_execution(internal_id="course_1"))
    await repo.add(new_execution(internal_id="course_1", operation="update_course"))
    await repo.add(new_execution(internal_id="course_2"))

    records = await repo.list_for_entity("course", "course_1")

    assert len(records) == 2
    assert {record.operation for record in records} == {"create_course", "update_course"}


@pytest.mark.asyncio
async def test_tracker_state_survives_in_the_database_after_failure(db_session):
    repo = SqlMoodleExecutionRepository(db_session)
    tracker = MoodleExecutionTracker(repo)

    async def action():
        raise MoodleAuthenticationFailedError("token ditolak")

    with pytest.raises(MoodleAuthenticationFailedError):
        await tracker.run("create_course", "course", "course_1", action)

    record = (await repo.list_for_entity("course", "course_1"))[0]
    assert record.status is MoodleExecutionStatus.FAILED
    assert record.error_category == "authentication"
    assert record.attempts == 1


@pytest.mark.asyncio
async def test_tracker_records_success_with_moodle_id_in_the_database(db_session):
    repo = SqlMoodleExecutionRepository(db_session)
    tracker = MoodleExecutionTracker(repo)

    async def action():
        return 77

    await tracker.run("create_course", "course", "course_1", action, moodle_id_of=lambda value: value)

    record = (await repo.list_for_entity("course", "course_1"))[0]
    assert record.status is MoodleExecutionStatus.SUCCESS
    assert record.moodle_id == 77