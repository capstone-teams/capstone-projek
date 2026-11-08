"""Integration test BE-04.5: enrolment dan akses course oleh akun uji (opt-in).

Jalankan dengan ``MOODLE_LIVE_TESTS=1``. Akun uji dibuat lebih dulu dengan
``python -m scripts.setup_moodle_test_accounts``, lalu username dan password-nya
diisi lewat environment:

* ``MOODLE_STUDENT_USERNAME`` / ``MOODLE_STUDENT_PASSWORD``: mahasiswa yang didaftarkan;
* ``MOODLE_STUDENT2_USERNAME`` / ``MOODLE_STUDENT2_PASSWORD``: mahasiswa yang **tidak** didaftarkan;
* ``MOODLE_TEACHER_USERNAME`` / ``MOODLE_TEACHER_PASSWORD``: dosen (opsional).
"""

import os
import uuid

import httpx
import pytest
import pytest_asyncio

from src.config.settings import settings
from src.services.moodle_client import MoodleClient
from src.services.moodle_error_category import MoodleErrorCategory, normalize_moodle_error
from src.services.moodle_exceptions import MoodlePermissionError
from src.services.moodle_integration_service import MoodleIntegrationService

pytestmark = pytest.mark.skipif(
    os.getenv("MOODLE_LIVE_TESTS") != "1",
    reason="Set MOODLE_LIVE_TESTS=1 untuk menjalankan test terhadap Moodle yang sedang menyala",
)

STUDENT = (os.getenv("MOODLE_STUDENT_USERNAME"), os.getenv("MOODLE_STUDENT_PASSWORD"))
OTHER_STUDENT = (os.getenv("MOODLE_STUDENT2_USERNAME"), os.getenv("MOODLE_STUDENT2_PASSWORD"))
TEACHER = (os.getenv("MOODLE_TEACHER_USERNAME"), os.getenv("MOODLE_TEACHER_PASSWORD"))

needs_two_students = pytest.mark.skipif(
    not (all(STUDENT) and all(OTHER_STUDENT)),
    reason="Isi MOODLE_STUDENT_* dan MOODLE_STUDENT2_* (akun dari scripts.setup_moodle_test_accounts)",
)


@pytest_asyncio.fixture
async def client():
    moodle = MoodleClient.from_settings(settings)
    try:
        yield moodle
    finally:
        await moodle.aclose()


async def user_token(username, password):
    async with httpx.AsyncClient(timeout=settings.moodle_timeout_seconds) as http:
        response = await http.post(
            f"{settings.MOODLE_BASE_URL.rstrip('/')}/login/token.php",
            data={"username": username, "password": password, "service": "moodle_mobile_app"},
        )
    token = response.json().get("token")
    assert token, f"token untuk {username} tidak didapat (cek akun dan service Mobile app)"
    return token


async def contents_as(username, password, course_id):
    async with MoodleClient(
        settings.MOODLE_BASE_URL, await user_token(username, password), timeout=settings.moodle_timeout_seconds
    ) as user_client:
        return await user_client.call("core_course_get_contents", {"courseid": course_id})


async def new_course(service):
    course = await service.create_course("Access Test", f"acc-{uuid.uuid4().hex[:8]}", 1)
    return course.moodle_course_id


async def require_user(service, username):
    user = await service.get_user_by_username(username)
    assert user is not None, f"akun {username} belum ada; jalankan scripts.setup_moodle_test_accounts"
    return user


@needs_two_students
@pytest.mark.asyncio
async def test_enrolled_student_can_open_the_course_and_others_are_rejected(client):
    service = MoodleIntegrationService(client)
    course_id = await new_course(service)
    student = await require_user(service, STUDENT[0])
    other = await require_user(service, OTHER_STUDENT[0])

    await service.enrol_users(course_id, [(student.moodle_user_id, "student")])
    await service.enrol_users(course_id, [(student.moodle_user_id, "student")])  # aman diulang

    enrolled = await service.get_enrolled_users(course_id)
    sections = await contents_as(*STUDENT, course_id)
    with pytest.raises(MoodlePermissionError) as rejected:
        await contents_as(*OTHER_STUDENT, course_id)

    assert [(item.user.username, item.roles) for item in enrolled] == [(student.username, ("student",))]
    assert other.moodle_user_id not in [item.user.moodle_user_id for item in enrolled]
    assert sections and sections[0]["section"] == 0
    assert normalize_moodle_error(rejected.value).category == MoodleErrorCategory.PERMISSION


@pytest.mark.skipif(not all(TEACHER), reason="Isi MOODLE_TEACHER_USERNAME dan MOODLE_TEACHER_PASSWORD")
@pytest.mark.asyncio
async def test_teacher_is_enrolled_as_editing_teacher_and_can_open_the_course(client):
    service = MoodleIntegrationService(client)
    course_id = await new_course(service)
    teacher = await require_user(service, TEACHER[0])

    await service.enrol_users(course_id, [(teacher.moodle_user_id, "teacher")])

    enrolled = await service.get_enrolled_users(course_id)
    sections = await contents_as(*TEACHER, course_id)
    assert [(item.user.username, item.roles) for item in enrolled] == [(teacher.username, ("editingteacher",))]
    assert sections and sections[0]["section"] == 0