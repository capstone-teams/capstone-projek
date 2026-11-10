"""Test Execution Service cakupan ``FULL`` (BE-21.1).

Membuktikan acceptance criteria BE-21.1 tanpa Moodle sungguhan:

- operasi ``SECTION`` per minggu ditambah satu operasi untuk setiap jenis konten
  (learning material, learning resource, assignment, quiz);
- hanya versi terbaru berstatus ``APPROVED`` yang dieksekusi; jenis nonaktif
  atau tanpa konten ``APPROVED`` dicatat ``SKIPPED`` beserta alasannya;
- setiap konten dipasang pada section minggunya (page, url, assign, quiz) dengan
  kunci idempotency berbasis ``content_key``, sehingga versi baru memperbarui
  activity yang sama;
- kegagalan satu operasi tidak menghentikan operasi lain dan retry hanya
  mengulang operasi gagal.

Moodle diganti tiruan berbasis HTTP (``tests.moodle_fakes``) supaya payload web
service yang benar-benar dikirim ikut diuji.
"""

from __future__ import annotations

import httpx
import pytest
import pytest_asyncio

from src.models.execution_operation import OperationStatus, OperationType
from src.models.moodle_execution import ExecutionScope, ExecutionStatus
from src.models.workflow import WorkflowStatus
from src.models.workflow_event import EventType
from src.services.content.domain import ContentKind
from src.services.execution.repository import ExecutionRepository
from src.services.execution.service import ExecutionService
from src.services.moodle_client import MoodleClient
from src.services.moodle_integration_service import MoodleIntegrationService
from src.services.rps.storage import LocalDocumentStorage
from src.services.workflow.orchestrator import run_execution_workflow
from src.services.workflow.service import WorkflowService
from tests.execution_fixtures import (
    FixedSessionFactory,
    approve_content,
    assignment_data,
    create_instructor,
    enable_all_activities,
    material_data,
    prepare_structure_workflow,
    quiz_data,
    resource_data,
    semester_weeks,
)
from tests.moodle_fakes import BASE_URL, TOKEN, FakeMoodle, moodle_exception

COURSE_ID = 3

CREATE_FUNCTIONS = {
    "local_capstonebridge_create_page": "page",
    "local_capstonebridge_create_url": "url",
    "local_capstonebridge_create_assign": "assign",
    "local_capstonebridge_create_quiz": "quiz",
}
UPDATE_FUNCTIONS = {
    "local_capstonebridge_update_page": "page",
    "local_capstonebridge_update_url": "url",
    "local_capstonebridge_update_assign": "assign",
    "local_capstonebridge_update_quiz": "quiz",
}


class ContentMoodle(FakeMoodle):
    """Moodle tiruan: course kosong + plugin activity yang dapat gagal per section."""

    def __init__(self) -> None:
        super().__init__()
        self.courses[COURSE_ID] = {
            "id": COURSE_ID,
            "fullname": "Basis Data",
            "shortname": "IF123",
            "format": "topics",
            "visible": 1,
            "categoryid": 1,
            "summary": "",
        }
        self.sections[COURSE_ID] = [
            {"id": 300, "section": 0, "name": "General", "summary": "", "visible": 1, "modules": []}
        ]
        #: idnumber → module yang sudah dibuat plugin.
        self.modules: dict[str, dict] = {}
        #: web service create yang gagal (mis. Moodle menolak parameter).
        self.fail_functions: set[str] = set()
        self.updates: list[str] = []
        self._next_cmid = 900

    def module(self, idnumber: str) -> dict:
        return self.modules[idnumber]

    def created(self, function: str) -> list[dict]:
        return self.called(function)

    def _dispatch(self, wsfunction, params):
        if wsfunction in CREATE_FUNCTIONS or wsfunction in UPDATE_FUNCTIONS:
            return self._activity(wsfunction, params)
        return super()._dispatch(wsfunction, params)

    def _activity(self, wsfunction, params):
        section = int(params.get("section") or 0)
        if wsfunction in CREATE_FUNCTIONS:
            if wsfunction in self.fail_functions:
                return moodle_exception(
                    "invalidparameter",
                    "Invalid parameter value detected",
                    "invalid_parameter_exception",
                )
            idnumber = params.get("idnumber", "")
            existing = self.modules.get(idnumber)
            if existing is not None:
                return self._response(existing, created=0)
            module = {
                "cmid": self._next_cmid,
                "instanceid": self._next_cmid + 1000,
                "section": section,
                "name": params.get("name", ""),
                "idnumber": idnumber,
                "fields": dict(params),
            }
            self._next_cmid += 2
            self.modules[idnumber] = module
            return self._response(module, created=1)

        cmid = int(params["cmid"])
        module = next((item for item in self.modules.values() if item["cmid"] == cmid), None)
        if module is None:
            return moodle_exception("invalidrecord", "Can't find data record in database.")
        module["section"] = section
        module["name"] = params.get("name", module["name"])
        module["fields"] = dict(params)
        self.updates.append(module["idnumber"])
        return self._response(module, created=0)

    @staticmethod
    def _response(module: dict, *, created: int) -> dict:
        return {
            "cmid": module["cmid"],
            "instanceid": module["instanceid"],
            "created": created,
            "section": module["section"],
            "questioncount": 1,
            "questionsreplaced": 1 if created == 0 else 0,
            "hasattempts": 0,
        }


@pytest.fixture
def moodle_fake() -> ContentMoodle:
    return ContentMoodle()


@pytest_asyncio.fixture
async def moodle(moodle_fake):
    client = MoodleClient(BASE_URL, TOKEN, transport=httpx.MockTransport(moodle_fake.handler))
    try:
        yield MoodleIntegrationService(client)
    finally:
        await client.aclose()


@pytest.fixture
def runner_env(monkeypatch, db_session):
    import src.services.workflow.orchestrator as orchestrator_module

    monkeypatch.setattr(
        orchestrator_module,
        "get_session_factory",
        lambda: FixedSessionFactory(db_session),
    )


@pytest_asyncio.fixture
async def semester(db_session, tmp_path, runner_env):
    owner_id = await create_instructor(db_session)
    workflow, plan = await prepare_structure_workflow(
        db_session,
        owner_id,
        LocalDocumentStorage(tmp_path),
        moodle_course_id=COURSE_ID,
        weeks=semester_weeks(2),
    )
    return owner_id, workflow.id or "", plan


async def start_full(session, moodle, workflow_id: str, owner_id: str):
    return await ExecutionService.from_session(session, moodle=moodle).start_full(
        workflow_id=workflow_id, owner_id=owner_id
    )


async def run_full(session, moodle, workflow_id: str, owner_id: str, execution_id: str):
    await run_execution_workflow(
        workflow_id=workflow_id,
        owner_id=owner_id,
        execution_id=execution_id,
        moodle=moodle,
    )
    return await ExecutionRepository(session).get(execution_id)


def operations(execution, operation_type: OperationType, week: int | None = None):
    return [
        operation
        for operation in execution.operations
        if operation.operation_type is operation_type
        and (week is None or operation.week_number == week)
    ]


@pytest.mark.asyncio
async def test_full_plan_skips_inactive_and_unapproved_content(
    db_session, moodle, semester
):
    owner_id, workflow_id, plan = semester
    # Default Activity Configuration: hanya learning material aktif.
    approved = await approve_content(
        db_session, workflow_id, plan, ContentKind.LEARNING_MATERIAL, 1, material_data(1)
    )

    execution = await start_full(db_session, moodle, workflow_id, owner_id)

    assert execution.scope is ExecutionScope.FULL
    assert len(execution.operations) == 2 + 2 * 4

    material = operations(execution, OperationType.LEARNING_MATERIAL, 1)
    [material_operation] = material
    assert material_operation.status is OperationStatus.PENDING
    assert material_operation.content_id == approved.id
    assert material_operation.idempotency_key == approved.content_key

    # Jenis nonaktif dicatat SKIPPED, bukan dihilangkan.
    resource = operations(execution, OperationType.LEARNING_RESOURCE, 1)
    [resource_operation] = resource
    assert resource_operation.status is OperationStatus.SKIPPED
    assert "Activity Configuration" in (resource_operation.error_message or "")

    # Materi minggu 2 aktif tetapi belum disetujui.
    [material_week_two] = operations(execution, OperationType.LEARNING_MATERIAL, 2)
    assert material_week_two.status is OperationStatus.SKIPPED
    assert "APPROVED" in (material_week_two.error_message or "")


@pytest.mark.asyncio
async def test_full_execution_publishes_each_content_on_its_week(
    db_session, moodle, moodle_fake, semester
):
    owner_id, workflow_id, plan = semester
    await enable_all_activities(db_session, owner_id)
    for kind, data in (
        (ContentKind.LEARNING_MATERIAL, material_data(1)),
        (ContentKind.RESOURCE, resource_data(1)),
        (ContentKind.ASSIGNMENT, assignment_data(1)),
        (ContentKind.QUIZ, quiz_data(1)),
    ):
        await approve_content(db_session, workflow_id, plan, kind, 1, data)

    started = await start_full(db_session, moodle, workflow_id, owner_id)
    execution = await run_full(
        db_session, moodle, workflow_id, owner_id, started.id or ""
    )

    assert execution.status is ExecutionStatus.SUCCESS
    assert all(
        operation.status is OperationStatus.SUCCESS
        for operation in execution.operations
        if operation.week_number == 1
    )

    page = moodle_fake.module(
        next(key for key in moodle_fake.modules if key.startswith("capstone-page-"))
    )
    assert page["section"] == 1
    assert page["name"] == "LEARNING_MATERIAL minggu 1"
    # Markdown → HTML tersanitasi, tautan http(s) dirender, skema lain tidak.
    assert "<h3>Tujuan Pembelajaran</h3>" in page["fields"]["content"]
    assert '<a href="https://developer.mozilla.org">MDN</a>' in page["fields"]["content"]
    assert 'href="javascript:' not in page["fields"]["content"]

    resource = moodle_fake.module(
        next(key for key in moodle_fake.modules if key.startswith("capstone-resource-"))
    )
    assert resource["fields"]["externalurl"] == "https://example.com/artikel"
    assert resource["section"] == 1

    assignment = moodle_fake.module(
        next(key for key in moodle_fake.modules if key.startswith("capstone-assignment-"))
    )
    assert assignment["section"] == 1

    quiz = moodle_fake.module(
        next(key for key in moodle_fake.modules if key.startswith("capstone-quiz-"))
    )
    assert quiz["section"] == 1

    workflow_service = WorkflowService.from_session(db_session)
    workflow = await workflow_service.get_workflow(
        workflow_id=workflow_id, owner_id=owner_id
    )
    assert workflow.status is WorkflowStatus.WAITING_FOR_REVIEW

    # Event OPERASI_MOODLE per operasi konten, membawa jenis kontennya.
    events = await workflow_service.list_events(
        workflow_id=workflow_id, owner_id=owner_id
    )
    content_events = [
        event
        for event in events
        if event.event_type is EventType.OPERASI_MOODLE
        and (event.metadata_ or {}).get("content_type")
    ]
    assert {event.metadata_["content_type"] for event in content_events} == {
        "LEARNING_MATERIAL",
        "RESOURCE",
        "ASSIGNMENT",
        "QUIZ",
    }
    assert all(
        event.metadata_["status"] == "SUCCESS" for event in content_events
    )


@pytest.mark.asyncio
async def test_regenerated_content_updates_same_activity(
    db_session, moodle, moodle_fake, semester
):
    owner_id, workflow_id, plan = semester
    first = await approve_content(
        db_session, workflow_id, plan, ContentKind.LEARNING_MATERIAL, 1, material_data(1)
    )
    started = await start_full(db_session, moodle, workflow_id, owner_id)
    await run_full(db_session, moodle, workflow_id, owner_id, started.id or "")

    idnumber = f"capstone-page-{first.content_key}"
    cmid = moodle_fake.module(idnumber)["cmid"]

    regenerated = await approve_content(
        db_session,
        workflow_id,
        plan,
        ContentKind.LEARNING_MATERIAL,
        1,
        {**material_data(1), "sections": [{"heading": "Revisi", "body_markdown": "Isi baru."}]},
    )
    assert regenerated.version == 2

    second = await start_full(db_session, moodle, workflow_id, owner_id)
    [material] = operations(second, OperationType.LEARNING_MATERIAL, 1)
    assert material.content_id == regenerated.id

    execution = await run_full(
        db_session, moodle, workflow_id, owner_id, second.id or ""
    )
    assert execution.status is ExecutionStatus.SUCCESS

    module = moodle_fake.module(idnumber)
    assert module["cmid"] == cmid
    assert "<h3>Revisi</h3>" in module["fields"]["content"]
    # Satu activity saja: create pertama, update pada regenerasi.
    pages = [key for key in moodle_fake.modules if key.startswith("capstone-page-")]
    assert pages == [idnumber]
    assert len(moodle_fake.created("local_capstonebridge_create_page")) == 1
    assert moodle_fake.updates == [idnumber]


@pytest.mark.asyncio
async def test_failed_content_does_not_stop_others_and_retry_repeats_failures(
    db_session, moodle, moodle_fake, semester
):
    owner_id, workflow_id, plan = semester
    await enable_all_activities(db_session, owner_id)
    await approve_content(db_session, workflow_id, plan, ContentKind.LEARNING_MATERIAL, 1, material_data(1))
    await approve_content(db_session, workflow_id, plan, ContentKind.ASSIGNMENT, 1, assignment_data(1))
    moodle_fake.fail_functions = {"local_capstonebridge_create_page"}

    started = await start_full(db_session, moodle, workflow_id, owner_id)
    execution = await run_full(
        db_session, moodle, workflow_id, owner_id, started.id or ""
    )

    assert execution.status is ExecutionStatus.FAILED
    [material] = operations(execution, OperationType.LEARNING_MATERIAL, 1)
    [assignment] = operations(execution, OperationType.ASSIGNMENT, 1)
    assert material.status is OperationStatus.FAILED
    # Kegagalan page tidak menghentikan assignment pada minggu yang sama.
    assert assignment.status is OperationStatus.SUCCESS
    assert execution.summary.failed == 1

    await ExecutionService.from_session(db_session, moodle=moodle).retry_failed(
        workflow_id=workflow_id, owner_id=owner_id, execution_id=execution.id or ""
    )
    moodle_fake.fail_functions = set()
    retried = await run_full(
        db_session, moodle, workflow_id, owner_id, execution.id or ""
    )

    assert retried.status is ExecutionStatus.SUCCESS
    [material] = operations(retried, OperationType.LEARNING_MATERIAL, 1)
    [assignment] = operations(retried, OperationType.ASSIGNMENT, 1)
    assert material.status is OperationStatus.SUCCESS
    assert material.retry_count == 1
    assert assignment.status is OperationStatus.SUCCESS
    assert assignment.retry_count == 0
    assert len(moodle_fake.created("local_capstonebridge_create_assign")) == 1


@pytest.mark.asyncio
async def test_resource_without_url_is_skipped_at_execution(
    db_session, moodle, moodle_fake, semester
):
    owner_id, workflow_id, plan = semester
    await enable_all_activities(db_session, owner_id)
    await approve_content(
        db_session, workflow_id, plan, ContentKind.RESOURCE, 1, resource_data(1, url=None)
    )

    started = await start_full(db_session, moodle, workflow_id, owner_id)
    execution = await run_full(
        db_session, moodle, workflow_id, owner_id, started.id or ""
    )

    [resource] = operations(execution, OperationType.LEARNING_RESOURCE, 1)
    assert resource.status is OperationStatus.SKIPPED
    assert "URL" in (resource.error_message or "")
    assert execution.status is ExecutionStatus.SUCCESS
    assert moodle_fake.created("local_capstonebridge_create_url") == []
