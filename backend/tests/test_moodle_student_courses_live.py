"""Integration test: mahasiswa melihat hasil eksekusi FULL lewat aplikasi (opt-in).

Jalankan dengan ``MOODLE_LIVE_TESTS=1``. Akun mahasiswa uji dari
``scripts.setup_moodle_test_accounts`` harus ada di Moodle; passwordnya tidak
dipakai karena yang diuji adalah endpoint aplikasi untuk user ber-role
mahasiswa (``MOODLE_STUDENT_USERNAME`` terdaftar, ``MOODLE_STUDENT2_USERNAME``
tidak terdaftar; bawaan ``mhs.uji`` dan ``mhs.uji2``).

Course baru dieksekusi FULL (section dan keempat jenis activity di minggu 1),
mahasiswa uji didaftarkan, lalu section minggu 2 disembunyikan. Endpoint
aplikasi harus menampilkan course dan activity itu kepada mahasiswa terdaftar,
tanpa section tersembunyi, dan menolak mahasiswa lain.
"""

import os
import uuid

import httpx
import pytest
import pytest_asyncio

from src.config.settings import settings
from src.main import create_app
from src.services.content.domain import ContentKind
from src.services.dependencies import get_current_user
from src.services.moodle_client import MoodleClient
from src.services.moodle_integration_service import MoodleIntegrationService
from src.services.rps.storage import LocalDocumentStorage
from src.services.user.domain import User
from src.services.user.enums import UserRole
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

STUDENT = os.getenv("MOODLE_STUDENT_USERNAME") or "mhs.uji"
OTHER_STUDENT = os.getenv("MOODLE_STUDENT2_USERNAME") or "mhs.uji2"
BASE = "/api/v1/integrations/moodle"

pytestmark = pytest.mark.skipif(
    os.getenv("MOODLE_LIVE_TESTS") != "1",
    reason="Set MOODLE_LIVE_TESTS=1 untuk menjalankan test terhadap Moodle yang sedang menyala",
)


@pytest_asyncio.fixture
async def moodle():
    client = MoodleClient.from_settings(settings)
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
async def course_id(db_session, tmp_path, moodle, runner_env):
    course = await moodle.create_course(
        "Student Course View Test", f"view-{uuid.uuid4().hex[:8]}", 1
    )
    owner_id = await create_instructor(db_session)
    workflow, plan = await prepare_structure_workflow(
        db_session,
        owner_id,
        LocalDocumentStorage(tmp_path),
        moodle_course_id=course.moodle_course_id,
        weeks=semester_weeks(2),
    )
    await enable_all_activities(db_session, owner_id)
    for kind, data in (
        (ContentKind.LEARNING_MATERIAL, material_data(1)),
        (ContentKind.RESOURCE, resource_data(1)),
        (ContentKind.ASSIGNMENT, assignment_data(1)),
        (ContentKind.QUIZ, quiz_data(1)),
    ):
        await approve_content(db_session, workflow.id or "", plan, kind, 1, data)
    await execute_full(db_session, moodle, workflow.id or "", owner_id)

    student = await moodle.get_user_by_username(STUDENT)
    if student is None:
        pytest.skip(f"Akun Moodle '{STUDENT}' belum ada (scripts.setup_moodle_test_accounts)")
    await moodle.enrol_users(course.moodle_course_id, [(student.moodle_user_id, "student")])
    contents = await moodle.get_course_contents(course.moodle_course_id)
    week_two = next(item for item in contents.sections if item.section_number == 2)
    await moodle.set_section_visibility(
        course.moodle_course_id, [week_two.moodle_section_id], False
    )
    return course.moodle_course_id


@pytest_asyncio.fixture
async def as_user():
    application = create_app()
    current = {}
    application.dependency_overrides[get_current_user] = lambda: current["user"]
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver", timeout=120
    ) as client:

        def login(username: str, role: UserRole = UserRole.STUDENT) -> httpx.AsyncClient:
            current["user"] = User(
                username=username,
                firstname="Pengguna",
                lastname="Uji",
                email=f"{username}@itk.ac.id",
                role=role,
            )
            return client

        yield login
    application.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_enrolled_student_sees_the_generated_course_in_the_app(as_user, course_id):
    client = as_user(STUDENT)

    listed = await client.get(f"{BASE}/courses")
    detail = await client.get(f"{BASE}/courses/{course_id}")
    contents = await client.get(f"{BASE}/courses/{course_id}/contents")

    assert course_id in [item["moodle_course_id"] for item in listed.json()["courses"]]
    assert detail.status_code == 200
    assert contents.status_code == 200, contents.text
    sections = {item["section_number"]: item for item in contents.json()["sections"]}
    assert 2 not in sections
    modules = {item["modname"]: item for item in sections[1]["modules"]}
    assert set(modules) == {"page", "url", "assign", "quiz"}
    assert modules["page"]["content"]
    assert modules["url"]["url"] == "https://example.com/artikel"
    assert modules["assign"]["description"]
    assert modules["quiz"]["description"]
    token = settings.MOODLE_WEB_SERVICE_TOKEN or ""
    assert not token or token not in contents.text


@pytest.mark.asyncio
async def test_other_student_cannot_open_the_course(as_user, course_id):
    client = as_user(OTHER_STUDENT)

    listed = await client.get(f"{BASE}/courses")
    contents = await client.get(f"{BASE}/courses/{course_id}/contents")

    assert course_id not in [item["moodle_course_id"] for item in listed.json()["courses"]]
    assert contents.status_code == 404