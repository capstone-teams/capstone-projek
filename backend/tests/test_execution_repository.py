"""Test model dan repository eksekusi Moodle (BE-16.1).

Membuktikan acceptance criteria BE-16.1 pada level repository:

- eksekusi (``MoodleExecution``) dapat dibuat, diperbarui, dan dibaca beserta
  operasinya (``ExecutionOperation``);
- seluruh status eksekusi (termasuk ``SKIPPED``) dan seluruh tipe operasi dapat
  disimpan dan dibaca kembali;
- hasil operasi (ID objek Moodle, pesan error, jumlah retry) tersimpan;
- kunci idempotency unik per eksekusi, dan ID objek Moodle operasi section
  sama dengan yang dicatat di tabel mapping BE-04.3.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
import shortuuid
from sqlalchemy.exc import IntegrityError

from src.models.content import Content, ContentType
from src.models.execution_operation import OperationStatus, OperationType
from src.models.moodle_execution import ExecutionScope, ExecutionStatus
from src.services.auth import hash_password
from src.services.course_plan.domain import CoursePlanDraft, CoursePlanWeekRecord
from src.services.course_plan.repository import CoursePlanRepository
from src.services.execution.domain import ExecutionSummary, PlannedOperation
from src.services.execution.repository import ExecutionRepository
from src.services.execution.service import SECTION_ENTITY_TYPE
from src.services.moodle_mapping import MoodleMapping
from src.services.moodle_mapping_sql import SqlMoodleMappingRepository
from src.services.rps.converter import DocumentConversion, DocumentConverter
from src.services.rps.service import RPSService
from src.services.rps.storage import LocalDocumentStorage
from src.services.user import UserRole, UserService
from src.services.workflow.broker import WorkflowEventBroker
from src.services.workflow.service import WorkflowService

PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"
MOODLE_COURSE_ID = 42
NOW = datetime(2026, 11, 9, 8, 0, tzinfo=timezone.utc)


class UnusedConverter(DocumentConverter):
    name = "unused"

    @property
    def version(self) -> str:
        return "unused-1"

    async def convert(self, *, content: bytes, file_name: str) -> DocumentConversion:
        raise AssertionError("test repository tidak mengonversi dokumen")


@pytest_asyncio.fixture
async def plan(db_session, tmp_path):
    """Workflow + course plan dua minggu, satu konten di minggu pertama."""
    suffix = shortuuid.uuid()[:10].lower()
    owner = await UserService.from_session(db_session).create_user(
        username=f"repo{suffix}",
        firstname="Pengguna",
        lastname="Uji",
        email=f"repo-{suffix}@itk.ac.id",
        role=UserRole.INSTRUCTOR,
        password=hash_password("SecretPassword123"),
    )
    rps_service = RPSService.from_session(
        db_session, storage=LocalDocumentStorage(tmp_path), converter=UnusedConverter()
    )
    uploaded = await rps_service.upload_rps(
        owner_id=owner.id or "", file_name="rps.pdf", content=PDF_BYTES
    )
    workflow = await WorkflowService.from_session(
        db_session, broker=WorkflowEventBroker()
    ).create_for_rps(owner_id=owner.id or "", rps_id=uploaded.document.id or "", total=1)
    course_plan = await CoursePlanRepository(db_session).create(
        CoursePlanDraft(
            workflow_id=workflow.id or "",
            rps_id=uploaded.document.id or "",
            course={"name": "Basis Data", "code": "IF123"},
            weeks=tuple(
                CoursePlanWeekRecord(week_number=number, title=f"Materi minggu {number}")
                for number in (1, 2)
            ),
            plan_data={"weeks": 2},
        )
    )
    content = Content(
        workflow_id=workflow.id,
        course_plan_id=course_plan.id,
        course_plan_week_id=course_plan.weeks[0].id,
        week_number=1,
        title="Pengantar Basis Data",
        content_type=ContentType.LEARNING_MATERIAL,
    )
    db_session.add(content)
    await db_session.commit()
    return workflow.id or "", course_plan, content.id


def _key(workflow_id: str, week: int, operation_type: OperationType) -> str:
    return f"{workflow_id}:week:{week}:{operation_type.value}"


async def _create(repository, workflow_id, course_plan, *, scope=ExecutionScope.STRUCTURE, operations=None):
    if operations is None:
        operations = [
            PlannedOperation(
                operation_type=OperationType.SECTION,
                course_plan_week_id=week.id,
                idempotency_key=_key(workflow_id, week.week_number, OperationType.SECTION),
            )
            for week in course_plan.weeks
        ]
    return await repository.create(
        workflow_id=workflow_id,
        course_plan_id=course_plan.id,
        moodle_course_id=MOODLE_COURSE_ID,
        scope=scope,
        operations=operations,
    )


@pytest.mark.asyncio
async def test_execution_is_created_pending_with_its_operations(db_session, plan):
    workflow_id, course_plan, _ = plan
    repository = ExecutionRepository(db_session)

    created = await _create(repository, workflow_id, course_plan)
    loaded = await repository.get(created.id)

    assert loaded == created
    assert loaded.workflow_id == workflow_id
    assert loaded.course_plan_id == course_plan.id
    assert loaded.moodle_course_id == MOODLE_COURSE_ID
    assert loaded.scope is ExecutionScope.STRUCTURE
    assert loaded.status is ExecutionStatus.PENDING
    assert (loaded.error_message, loaded.readback, loaded.started_at, loaded.completed_at) == (
        None, None, None, None,
    )
    assert [(op.week_number, op.operation_type, op.status, op.retry_count) for op in loaded.operations] == [
        (1, OperationType.SECTION, OperationStatus.PENDING, 0),
        (2, OperationType.SECTION, OperationStatus.PENDING, 0),
    ]
    assert [op.course_plan_week_id for op in loaded.operations] == [week.id for week in course_plan.weeks]
    assert all(op.execution_id == created.id and op.moodle_object_id is None for op in loaded.operations)
    assert loaded.summary == ExecutionSummary(total=2)


@pytest.mark.asyncio
async def test_full_scope_stores_every_operation_type_and_the_optional_content(db_session, plan):
    workflow_id, course_plan, content_id = plan
    week_one = course_plan.weeks[0]
    operations = [
        PlannedOperation(
            operation_type=operation_type,
            course_plan_week_id=week_one.id,
            content_id=None if operation_type is OperationType.SECTION else content_id,
            idempotency_key=_key(workflow_id, 1, operation_type),
        )
        for operation_type in OperationType
    ]

    created = await _create(
        ExecutionRepository(db_session), workflow_id, course_plan, scope=ExecutionScope.FULL, operations=operations
    )

    assert created.scope is ExecutionScope.FULL
    assert sorted(op.operation_type.value for op in created.operations) == sorted(t.value for t in OperationType)
    assert {op.operation_type: op.content_id for op in created.operations} == {
        OperationType.SECTION: None,
        OperationType.LEARNING_MATERIAL: content_id,
        OperationType.LEARNING_RESOURCE: content_id,
        OperationType.ASSIGNMENT: content_id,
        OperationType.QUIZ: content_id,
    }


@pytest.mark.asyncio
async def test_execution_lifecycle_is_updated_and_read_back(db_session, plan):
    workflow_id, course_plan, _ = plan
    repository = ExecutionRepository(db_session)
    created = await _create(repository, workflow_id, course_plan)
    readback = {"sections": 2, "mismatched_weeks": []}

    await repository.mark_running(created.id, at=NOW)
    running = await repository.get(created.id)
    await repository.finish(
        created.id, status=ExecutionStatus.SUCCESS, at=NOW + timedelta(minutes=1), readback=readback
    )
    finished = await repository.get(created.id)

    assert running.status is ExecutionStatus.RUNNING
    assert running.started_at.replace(tzinfo=timezone.utc) == NOW
    assert running.completed_at is None
    assert finished.status is ExecutionStatus.SUCCESS
    assert finished.readback == readback
    assert finished.completed_at.replace(tzinfo=timezone.utc) == NOW + timedelta(minutes=1)
    assert finished.error_message is None


@pytest.mark.asyncio
@pytest.mark.parametrize("status", list(ExecutionStatus))
async def test_every_execution_status_can_be_stored(db_session, plan, status):
    workflow_id, course_plan, _ = plan
    repository = ExecutionRepository(db_session)
    created = await _create(repository, workflow_id, course_plan, operations=[])
    error = "Moodle tidak dapat dihubungi" if status is ExecutionStatus.FAILED else None

    await repository.finish(created.id, status=status, at=NOW, error_message=error)

    loaded = await repository.get(created.id)
    assert loaded.status is status
    assert loaded.error_message == error


@pytest.mark.asyncio
async def test_skipped_execution_has_no_operations_to_apply(db_session, plan):
    workflow_id, course_plan, _ = plan
    repository = ExecutionRepository(db_session)
    created = await _create(repository, workflow_id, course_plan, scope=ExecutionScope.FULL, operations=[])

    await repository.finish(created.id, status=ExecutionStatus.SKIPPED, at=NOW)

    loaded = await repository.get(created.id)
    assert loaded.status is ExecutionStatus.SKIPPED
    assert loaded.operations == ()
    assert loaded.summary == ExecutionSummary()


@pytest.mark.asyncio
async def test_operation_results_are_stored(db_session, plan):
    workflow_id, course_plan, _ = plan
    repository = ExecutionRepository(db_session)
    created = await _create(repository, workflow_id, course_plan)
    first, second = created.operations

    await repository.start_operation(first.id)
    started = (await repository.get(created.id)).operations[0]
    await repository.finish_operation(first.id, status=OperationStatus.SUCCESS, moodle_object_id="201")
    await repository.finish_operation(
        second.id,
        status=OperationStatus.FAILED,
        error_message="Moodle menolak rename section",
        retry_count=2,
    )
    loaded = await repository.get(created.id)

    assert started.status is OperationStatus.RUNNING
    assert [(op.status, op.moodle_object_id, op.error_message, op.retry_count) for op in loaded.operations] == [
        (OperationStatus.SUCCESS, "201", None, 0),
        (OperationStatus.FAILED, None, "Moodle menolak rename section", 2),
    ]
    assert loaded.summary == ExecutionSummary(total=2, success=1, failed=1)
    assert [op.id for op in loaded.failed_operations] == [second.id]


@pytest.mark.asyncio
async def test_failed_execution_is_reset_for_retry_on_the_same_row(db_session, plan):
    workflow_id, course_plan, _ = plan
    repository = ExecutionRepository(db_session)
    created = await _create(repository, workflow_id, course_plan)
    await repository.mark_running(created.id, at=NOW)
    await repository.finish(created.id, status=ExecutionStatus.FAILED, at=NOW, error_message="gagal")

    await repository.reset_for_retry(created.id)
    await repository.finish_operation(created.operations[0].id, status=OperationStatus.SKIPPED)

    loaded = await repository.get(created.id)
    assert loaded.id == created.id
    assert loaded.status is ExecutionStatus.PENDING
    assert (loaded.error_message, loaded.completed_at) == (None, None)
    assert loaded.started_at is not None
    assert loaded.summary == ExecutionSummary(total=2, skipped=1)


@pytest.mark.asyncio
async def test_executions_are_listed_and_scoped_per_workflow(db_session, plan):
    workflow_id, course_plan, _ = plan
    repository = ExecutionRepository(db_session)
    first = await _create(repository, workflow_id, course_plan)
    second = await _create(repository, workflow_id, course_plan)

    listed = await repository.list_for_workflow(workflow_id)

    assert {item.id for item in listed} == {first.id, second.id}
    assert listed[0].created_at >= listed[1].created_at
    assert (await repository.get_for_workflow(workflow_id, first.id)).id == first.id
    assert await repository.get_for_workflow("workflow-lain", first.id) is None
    assert await repository.list_for_workflow("workflow-lain") == []
    assert await repository.get("tidak-ada") is None


@pytest.mark.asyncio
async def test_updates_on_unknown_ids_are_ignored(db_session):
    repository = ExecutionRepository(db_session)

    await repository.mark_running("tidak-ada", at=NOW)
    await repository.finish("tidak-ada", status=ExecutionStatus.SUCCESS, at=NOW)
    await repository.reset_for_retry("tidak-ada")
    await repository.start_operation("tidak-ada")
    await repository.finish_operation("tidak-ada", status=OperationStatus.SUCCESS)

    assert await repository.get("tidak-ada") is None


@pytest.mark.asyncio
async def test_idempotency_key_is_unique_per_execution(db_session, plan):
    workflow_id, course_plan, _ = plan
    repository = ExecutionRepository(db_session)
    duplicate = PlannedOperation(
        operation_type=OperationType.SECTION,
        course_plan_week_id=course_plan.weeks[0].id,
        idempotency_key=_key(workflow_id, 1, OperationType.SECTION),
    )

    first = await _create(repository, workflow_id, course_plan, operations=[duplicate])
    second = await _create(repository, workflow_id, course_plan, operations=[duplicate])
    with pytest.raises(IntegrityError):
        await _create(repository, workflow_id, course_plan, operations=[duplicate, duplicate])
    await db_session.rollback()

    assert first.operations[0].idempotency_key == second.operations[0].idempotency_key
    assert first.id != second.id


@pytest.mark.asyncio
async def test_section_operation_matches_the_mapping_table(db_session, plan):
    """ID objek Moodle operasi section sama dengan sumber idempotency BE-04.3."""
    workflow_id, course_plan, _ = plan
    repository = ExecutionRepository(db_session)
    mappings = SqlMoodleMappingRepository(db_session)
    created = await _create(repository, workflow_id, course_plan)
    operation = created.operations[0]

    await mappings.save(
        MoodleMapping(entity_type=SECTION_ENTITY_TYPE, internal_id=operation.course_plan_week_id, moodle_id=201)
    )
    await repository.finish_operation(operation.id, status=OperationStatus.SUCCESS, moodle_object_id="201")

    stored = (await repository.get(created.id)).operations[0]
    mapped = await mappings.get_moodle_id(SECTION_ENTITY_TYPE, stored.course_plan_week_id)
    assert stored.moodle_object_id == str(mapped)