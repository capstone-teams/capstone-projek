"""Test Moodle Verification Service (BE-21.2) dengan Moodle tiruan.

Course dieksekusi ``FULL`` lebih dulu (BE-21.1) melalui ``MoodleIntegrationService``
dan plugin tiruan (``tests.moodle_fakes.ActivityMoodle``), lalu kondisi course
diubah seperti perubahan manual di Moodle (activity dihapus, diganti nama,
dipindah section, ditambah activity lain) sebelum diverifikasi. Yang dibuktikan:

- course hasil eksekusi FULL terverifikasi ``PASS`` tanpa perbaikan;
- activity yang dihapus manual terdeteksi ``MISSING``, dibuat ulang, mapping
  dan operasi memakai cmid baru, dan verifikasi berikutnya ``PASS``;
- judul berbeda, salah section, nama section berbeda, dan ID yang tidak sesuai
  mapping diperbaiki lewat eksekusi ulang operasi terkait;
- activity yang tidak berasal dari eksekusi dilaporkan ``UNEXPECTED`` (``PARTIAL``)
  dan tidak dihapus;
- perbaikan dibatasi ``max_repairs``; kegagalan Moodle menghasilkan ``UNKNOWN``;
- ``VerificationResult`` tersimpan dan hanya dapat dibaca pemilik workflow.

Integration test terhadap Moodle tim ada di ``test_moodle_verification_live.py``.
"""

from __future__ import annotations

import httpx
import pytest
import pytest_asyncio

from src.models.execution_operation import OperationStatus, OperationType
from src.models.verification import VerificationStatus
from src.services.content.domain import ContentKind
from src.services.execution.repository import ExecutionRepository
from src.services.execution.service import SECTION_ENTITY_TYPE
from src.services.moodle_client import MoodleClient
from src.services.moodle_integration_service import (
    MoodleCourseContents,
    MoodleIntegrationService,
    MoodleModule,
    MoodleSection,
)
from src.services.moodle_mapping import MoodleMapping
from src.services.moodle_mapping_sql import SqlMoodleMappingRepository
from src.services.moodle_quiz_service import QUIZ_ENTITY_TYPE
from src.services.rps.storage import LocalDocumentStorage
from src.services.verification.domain import (
    ActivityExpectation,
    DiscrepancyType,
    SectionExpectation,
    compare_course,
    status_for,
)
from src.services.verification.errors import (
    NO_EXECUTION_TO_VERIFY,
    VerificationNotFoundError,
    VerificationPreconditionError,
)
from src.services.verification.service import VerificationService
from src.services.workflow.errors import WorkflowNotFoundError
from tests.execution_fixtures import (
    FixedSessionFactory,
    approve_content,
    assignment_data,
    create_instructor,
    enable_all_activities,
    execute_full,
    material_data,
    prepare_structure_workflow,
    quiz_data,
    resource_data,
    semester_weeks,
)
from tests.moodle_fakes import ACTIVITY_COURSE_ID, BASE_URL, TOKEN, ActivityMoodle

KINDS = (
    (ContentKind.LEARNING_MATERIAL, material_data),
    (ContentKind.RESOURCE, resource_data),
    (ContentKind.ASSIGNMENT, assignment_data),
    (ContentKind.QUIZ, quiz_data),
)


@pytest.fixture
def moodle_fake() -> ActivityMoodle:
    return ActivityMoodle()


@pytest_asyncio.fixture
async def moodle(moodle_fake):
    client = MoodleClient(
        BASE_URL, TOKEN, transport=httpx.MockTransport(moodle_fake.handler)
    )
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
async def workflow(db_session, tmp_path, runner_env):
    """Workflow 2 minggu dengan keempat jenis konten APPROVED pada minggu 1."""
    owner_id = await create_instructor(db_session)
    record, plan = await prepare_structure_workflow(
        db_session,
        owner_id,
        LocalDocumentStorage(tmp_path),
        moodle_course_id=ACTIVITY_COURSE_ID,
        weeks=semester_weeks(2),
    )
    await enable_all_activities(db_session, owner_id)
    for kind, data in KINDS:
        await approve_content(db_session, record.id or "", plan, kind, 1, data(1))
    return owner_id, record.id or "", plan


@pytest_asyncio.fixture
async def executed(db_session, moodle, workflow):
    owner_id, workflow_id, plan = workflow
    execution_id = await execute_full(db_session, moodle, workflow_id, owner_id)
    execution = await ExecutionRepository(db_session).get(execution_id)
    cmids = {
        operation.operation_type: int(operation.moodle_object_id)
        for operation in execution.operations
        if operation.operation_type is not OperationType.SECTION
        and operation.moodle_object_id
    }
    return owner_id, workflow_id, plan, execution_id, cmids


def service(db_session, moodle, **kwargs) -> VerificationService:
    return VerificationService.from_session(db_session, moodle=moodle, **kwargs)


def types(items) -> set[tuple[str, str]]:
    return {(item.type.value, item.target) for item in items}


# --- Hasil sesuai -------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_execution_is_verified_as_pass_without_repairs(
    db_session, moodle, moodle_fake, executed
):
    owner_id, workflow_id, _, execution_id, cmids = executed

    result = await service(db_session, moodle).verify(
        workflow_id=workflow_id, owner_id=owner_id
    )

    assert result.status is VerificationStatus.PASS
    assert result.matches is True
    assert result.execution_id == execution_id
    assert (
        result.discrepancies,
        result.repaired,
        result.repair_count,
        result.repair_rounds,
    ) == ((), (), 0, 0)
    assert result.summary == {
        "expected_sections": 2,
        "actual_sections": 2,
        "expected_activities": 4,
        "found_activities": 4,
    }
    assert result.verified_at is not None
    assert len(moodle_fake.weekly_modules()) == 4


# --- Perbaikan otomatis ---------------------------------------------------------


@pytest.mark.asyncio
async def test_deleted_activity_is_recreated_and_the_next_verification_passes(
    db_session, moodle, moodle_fake, executed
):
    owner_id, workflow_id, _, execution_id, cmids = executed
    old_quiz = cmids[OperationType.QUIZ]
    moodle_fake.delete_module(old_quiz)

    first = await service(db_session, moodle).verify(
        workflow_id=workflow_id, owner_id=owner_id
    )
    second = await service(db_session, moodle).verify(
        workflow_id=workflow_id, owner_id=owner_id
    )

    execution = await ExecutionRepository(db_session).get(execution_id)
    quiz_operation = next(
        op for op in execution.operations if op.operation_type is OperationType.QUIZ
    )
    new_quiz = int(quiz_operation.moodle_object_id)
    content_key = next(
        op.idempotency_key
        for op in execution.operations
        if op.operation_type is OperationType.QUIZ
    )
    assert first.status is VerificationStatus.PASS
    assert types(first.repaired) == {("MISSING", "QUIZ")}
    assert first.repaired[0].moodle_object_id == old_quiz
    assert (first.repair_count, first.repair_rounds) == (1, 1)
    assert first.discrepancies == ()
    assert new_quiz != old_quiz
    assert moodle_fake.module(new_quiz)["modname"] == "quiz"
    assert moodle_fake.section_of(new_quiz) == 1
    assert (
        await SqlMoodleMappingRepository(db_session).get_moodle_id(
            QUIZ_ENTITY_TYPE, content_key
        )
        == new_quiz
    )
    assert quiz_operation.status is OperationStatus.SUCCESS
    assert second.status is VerificationStatus.PASS
    assert (second.repaired, second.repair_count) == ((), 0)
    assert len(moodle_fake.weekly_modules()) == 4


@pytest.mark.asyncio
async def test_renamed_and_moved_activities_and_renamed_section_are_repaired(
    db_session, moodle, moodle_fake, executed
):
    owner_id, workflow_id, plan, _, cmids = executed
    moodle_fake.module(cmids[OperationType.LEARNING_MATERIAL])["name"] = "Diubah manual"
    moodle_fake.move_module(cmids[OperationType.LEARNING_RESOURCE], 2)
    moodle_fake.sections[ACTIVITY_COURSE_ID][1]["name"] = "Section diubah"

    result = await service(db_session, moodle).verify(
        workflow_id=workflow_id, owner_id=owner_id
    )

    assert result.status is VerificationStatus.PASS
    assert types(result.repaired) == {
        ("TITLE_MISMATCH", "LEARNING_MATERIAL"),
        ("WRONG_SECTION", "LEARNING_RESOURCE"),
        ("TITLE_MISMATCH", "SECTION"),
    }
    assert result.repair_count == 3
    assert (
        moodle_fake.module(cmids[OperationType.LEARNING_MATERIAL])["name"]
        == "LEARNING_MATERIAL minggu 1"
    )
    assert moodle_fake.section_of(cmids[OperationType.LEARNING_RESOURCE]) == 1
    assert (
        moodle_fake.sections[ACTIVITY_COURSE_ID][1]["name"]
        == "Minggu 1 - Materi minggu 1"
    )


@pytest.mark.asyncio
async def test_operation_id_that_differs_from_the_mapping_is_repaired(
    db_session, moodle, executed
):
    owner_id, workflow_id, _, execution_id, cmids = executed
    repository = ExecutionRepository(db_session)
    execution = await repository.get(execution_id)
    assignment = next(
        op
        for op in execution.operations
        if op.operation_type is OperationType.ASSIGNMENT
    )
    await repository.finish_operation(
        assignment.id, status=OperationStatus.SUCCESS, moodle_object_id="1"
    )

    result = await service(db_session, moodle).verify(
        workflow_id=workflow_id, owner_id=owner_id
    )

    repaired = next(
        op
        for op in (await repository.get(execution_id)).operations
        if op.id == assignment.id
    )
    assert result.status is VerificationStatus.PASS
    assert types(result.repaired) == {("MAPPING_MISMATCH", "ASSIGNMENT")}
    assert repaired.moodle_object_id == str(cmids[OperationType.ASSIGNMENT])


@pytest.mark.asyncio
async def test_unexpected_activity_is_reported_and_left_alone(
    db_session, moodle, moodle_fake, executed
):
    owner_id, workflow_id, _, _, _ = executed
    manual = moodle_fake.add_manual_module(1, "Forum diskusi dosen")

    result = await service(db_session, moodle).verify(
        workflow_id=workflow_id, owner_id=owner_id
    )

    [unexpected] = result.discrepancies
    assert result.status is VerificationStatus.PARTIAL
    assert result.matches is False
    assert unexpected.type is DiscrepancyType.UNEXPECTED
    assert (unexpected.moodle_object_id, unexpected.week_number) == (manual, 1)
    assert unexpected.repairable is False
    assert result.repair_count == 0
    assert moodle_fake.module(manual) is not None


@pytest.mark.asyncio
async def test_repairs_are_limited_by_max_repairs(
    db_session, moodle, moodle_fake, executed
):
    owner_id, workflow_id, _, _, cmids = executed
    moodle_fake.delete_module(cmids[OperationType.QUIZ])

    without = await service(db_session, moodle, max_repairs=0).verify(
        workflow_id=workflow_id, owner_id=owner_id
    )
    moodle_fake.failing["local_capstonebridge_create_quiz"] = {
        "exception": "invalid_parameter_exception",
        "errorcode": "invalidparameter",
        "message": "Invalid parameter value detected",
    }
    attempts_before = len(moodle_fake.called("local_capstonebridge_create_quiz"))
    limited = await service(db_session, moodle, max_repairs=2).verify(
        workflow_id=workflow_id, owner_id=owner_id
    )

    assert without.status is VerificationStatus.FAIL
    assert types(without.discrepancies) == {("MISSING", "QUIZ")}
    assert without.discrepancies[0].repairable is True
    assert (without.repair_count, without.repair_rounds) == (0, 0)
    assert limited.status is VerificationStatus.FAIL
    assert (limited.repair_count, limited.repair_rounds) == (2, 2)
    assert limited.repaired == ()
    assert (
        len(moodle_fake.called("local_capstonebridge_create_quiz")) - attempts_before
        == 2
    )


@pytest.mark.asyncio
async def test_moodle_failure_during_read_back_is_unknown(
    db_session, moodle, moodle_fake, executed
):
    owner_id, workflow_id, _, _, _ = executed
    moodle_fake.raise_on_request = httpx.ConnectError("connection refused")

    result = await service(db_session, moodle).verify(
        workflow_id=workflow_id, owner_id=owner_id
    )

    assert result.status is VerificationStatus.UNKNOWN
    assert result.error_message
    assert TOKEN not in result.error_message
    assert result.discrepancies == ()


# --- Prasyarat dan akses --------------------------------------------------------


@pytest.mark.asyncio
async def test_workflow_without_a_finished_full_execution_is_rejected(
    db_session, moodle, workflow
):
    owner_id, workflow_id, _ = workflow

    with pytest.raises(VerificationPreconditionError) as rejected:
        await service(db_session, moodle).verify(
            workflow_id=workflow_id, owner_id=owner_id
        )

    assert rejected.value.reason == NO_EXECUTION_TO_VERIFY
    assert rejected.value.details == [
        {"field": "reason", "message": NO_EXECUTION_TO_VERIFY}
    ]


@pytest.mark.asyncio
async def test_results_are_stored_and_scoped_to_the_workflow_owner(
    db_session, moodle, moodle_fake, executed
):
    owner_id, workflow_id, _, _, cmids = executed
    verifications = service(db_session, moodle)
    first = await verifications.verify(workflow_id=workflow_id, owner_id=owner_id)
    moodle_fake.delete_module(cmids[OperationType.LEARNING_MATERIAL])
    second = await verifications.verify(workflow_id=workflow_id, owner_id=owner_id)
    other_owner = await create_instructor(db_session)

    listed = await verifications.list_results(
        workflow_id=workflow_id, owner_id=owner_id
    )
    stored = await verifications.get_result(
        workflow_id=workflow_id, owner_id=owner_id, verification_id=second.id
    )

    assert {item.id for item in listed} == {first.id, second.id}
    assert stored == second
    assert types(stored.repaired) == {("MISSING", "LEARNING_MATERIAL")}
    with pytest.raises(VerificationNotFoundError):
        await verifications.get_result(
            workflow_id=workflow_id, owner_id=owner_id, verification_id="tidak-ada"
        )
    with pytest.raises(WorkflowNotFoundError):
        await verifications.list_results(workflow_id=workflow_id, owner_id=other_owner)


@pytest.mark.asyncio
async def test_stale_section_mapping_is_discarded_and_saved_again(
    db_session, moodle, executed
):
    owner_id, workflow_id, plan, _, _ = executed
    mappings = SqlMoodleMappingRepository(db_session)
    week_two = plan.weeks[1]
    actual_section = await mappings.get_moodle_id(SECTION_ENTITY_TYPE, week_two.id)
    await mappings.delete(SECTION_ENTITY_TYPE, week_two.id)
    await mappings.save(
        MoodleMapping(
            entity_type=SECTION_ENTITY_TYPE, internal_id=week_two.id, moodle_id=9999
        )
    )

    result = await service(db_session, moodle).verify(
        workflow_id=workflow_id, owner_id=owner_id
    )

    assert result.status is VerificationStatus.PASS
    assert types(result.repaired) == {("MAPPING_MISMATCH", "SECTION")}
    assert (
        await mappings.get_moodle_id(SECTION_ENTITY_TYPE, week_two.id) == actual_section
    )


# --- Aturan pembandingan (tanpa Moodle dan database) ------------------------------


def contents(*modules_by_section: list[MoodleModule]) -> MoodleCourseContents:
    sections = [
        MoodleSection(
            moodle_section_id=100,
            section_number=0,
            name="General",
            summary="",
            visible=True,
            modules=[
                MoodleModule(
                    moodle_module_id=1, name="Pengumuman", modname="forum", visible=True
                )
            ],
        )
    ]
    for number, modules in enumerate(modules_by_section, start=1):
        sections.append(
            MoodleSection(
                moodle_section_id=100 + number,
                section_number=number,
                name=f"Minggu {number}",
                summary="",
                visible=True,
                modules=list(modules),
            )
        )
    return MoodleCourseContents(moodle_course_id=ACTIVITY_COURSE_ID, sections=sections)


def page(cmid: int, name: str = "Materi") -> MoodleModule:
    return MoodleModule(moodle_module_id=cmid, name=name, modname="page", visible=True)


SECTIONS = [
    SectionExpectation(
        week_number=1, name="Minggu 1", operation_id="s1", mapped_section_id=101
    ),
    SectionExpectation(
        week_number=2, name="Minggu 2", operation_id="s2", mapped_section_id=102
    ),
]


def expected_page(**overrides) -> ActivityExpectation:
    values = dict(
        operation_id="p1",
        operation_type=OperationType.LEARNING_MATERIAL,
        week_number=1,
        title="Materi",
        mapped_cmid=50,
        recorded_cmid=50,
    )
    values.update(overrides)
    return ActivityExpectation(**values)


def test_matching_course_has_no_discrepancies_and_ignores_the_general_section():
    comparison = compare_course(contents([page(50)], []), SECTIONS, [expected_page()])

    assert comparison.discrepancies == ()
    assert comparison.summary == {
        "expected_sections": 2,
        "actual_sections": 2,
        "expected_activities": 1,
        "found_activities": 1,
    }
    assert status_for(comparison.discrepancies) is VerificationStatus.PASS


@pytest.mark.parametrize(
    ("course", "expectation", "expected"),
    [
        (contents([], []), expected_page(), ("MISSING", True)),
        (
            contents([], []),
            expected_page(mapped_cmid=None, recorded_cmid=None),
            ("MISSING", False),
        ),
        (contents([], [page(50)]), expected_page(), ("WRONG_SECTION", False)),
        (contents([page(50, "Lain")], []), expected_page(), ("TITLE_MISMATCH", False)),
        (
            contents([page(50)], []),
            expected_page(recorded_cmid=7),
            ("MAPPING_MISMATCH", False),
        ),
        (
            contents(
                [
                    MoodleModule(
                        moodle_module_id=50, name="Materi", modname="quiz", visible=True
                    )
                ],
                [],
            ),
            expected_page(),
            ("MAPPING_MISMATCH", True),
        ),
    ],
)
def test_each_activity_difference_has_its_own_type(course, expectation, expected):
    comparison = compare_course(
        course, SECTIONS, [expectation], report_unexpected=False
    )

    [discrepancy] = comparison.discrepancies
    assert (discrepancy.type.value, discrepancy.stale_mapping) == expected
    assert discrepancy.repairable is True
    assert discrepancy.to_dict()["operation_id"] == "p1"
    assert status_for(comparison.discrepancies) is VerificationStatus.FAIL


def test_missing_and_renamed_sections_are_reported():
    course = contents([page(50)])
    renamed = [
        SectionExpectation(week_number=1, name="Minggu 1 - baru", operation_id="s1"),
        SECTIONS[1],
    ]

    comparison = compare_course(course, renamed, [expected_page()])

    assert [
        (item.type.value, item.target, item.week_number)
        for item in comparison.discrepancies
    ] == [
        ("TITLE_MISMATCH", "SECTION", 1),
        ("MISSING", "SECTION", 2),
    ]


def test_unexpected_modules_only_make_the_result_partial():
    comparison = compare_course(
        contents([page(50), page(60, "Tambahan dosen")], []),
        SECTIONS,
        [expected_page()],
    )

    [unexpected] = comparison.discrepancies
    assert unexpected.type is DiscrepancyType.UNEXPECTED
    assert unexpected.to_dict()["label"] == "tidak terduga"
    assert unexpected.repairable is False
    assert status_for(comparison.discrepancies) is VerificationStatus.PARTIAL