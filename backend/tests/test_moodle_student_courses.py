"""Test akses course Moodle untuk mahasiswa yang login ke aplikasi.

Frontend memakai ``GET /integrations/moodle/courses``, ``/courses/{id}``, dan
``/courses/{id}/contents`` untuk dosen maupun mahasiswa. Yang dibuktikan:

- mahasiswa hanya melihat course terlihat tempat ia terdaftar;
- isi course bagi mahasiswa tidak memuat section dan activity tersembunyi, tetapi
  memuat isi page, alamat url, dan intro assignment/quiz hasil eksekusi;
- course yang tidak dapat diakses mahasiswa menghasilkan 404 yang sama seperti
  course yang tidak ada;
- dosen tetap melihat seluruh course dan isi course apa adanya.
"""

from __future__ import annotations

import httpx
import pytest
import pytest_asyncio

from src.main import create_app
from src.services.dependencies import get_current_user, get_moodle_integration_service
from src.services.moodle_client import MoodleClient
from src.services.moodle_integration_service import MoodleIntegrationService
from src.services.user.domain import User
from src.services.user.enums import UserRole
from tests.moodle_fakes import (
    BASE_URL,
    OTHER_STUDENT_ACCOUNT,
    STUDENT_ACCOUNT,
    STUDENT_COURSE_ID,
    TOKEN,
    StudentMoodle,
    moodle_exception,
)

BASE = "/api/v1/integrations/moodle"
OTHER_COURSE_ID = 7
HIDDEN_COURSE_ID = 8


class GeneratedCourseMoodle(StudentMoodle):
    """Course 2 berisi hasil eksekusi FULL; course 7 dan 8 milik kelas lain."""

    def __init__(self) -> None:
        super().__init__()
        week_one = self.sections[STUDENT_COURSE_ID][1]
        week_one["modules"] = [
            {"id": 501, "name": "Pengantar HTML", "modname": "page", "visible": 1, "description": ""},
            {"id": 502, "name": "Tugas 1", "modname": "assign", "visible": 1, "description": ""},
            {
                "id": 503,
                "name": "Artikel HTML",
                "modname": "url",
                "visible": 1,
                "description": "",
                "contents": [{"type": "url", "filename": "Artikel HTML", "fileurl": "https://example.com/html"}],
            },
            {"id": 504, "name": "Kuis 1", "modname": "quiz", "visible": 1, "description": ""},
            {"id": 505, "name": "Draf dosen", "modname": "page", "visible": 0, "description": ""},
        ]
        self.sections[STUDENT_COURSE_ID][3]["visible"] = 0
        self.pages[505] = "<p>belum siap</p>"
        for course_id, visible in ((OTHER_COURSE_ID, 1), (HIDDEN_COURSE_ID, 0)):
            self.courses[course_id] = {
                "id": course_id,
                "fullname": f"Course {course_id}",
                "shortname": f"C{course_id}",
                "format": "topics",
                "visible": visible,
                "categoryid": 1,
                "summary": "",
            }
            self.sections[course_id] = [
                {"id": 900 + course_id, "section": 0, "name": "General", "summary": "", "visible": 1, "modules": []}
            ]

    def _dispatch(self, wsfunction, params):
        if wsfunction == "mod_assign_get_assignments":
            return {
                "courses": [{"id": STUDENT_COURSE_ID, "assignments": [{"cmid": 502, "intro": "<p>Buat halaman profil.</p>"}]}],
                "warnings": [],
            }
        if wsfunction == "mod_quiz_get_quizzes_by_courses":
            return {"quizzes": [{"coursemodule": 504, "intro": "<p>Kerjakan 3 soal.</p>"}], "warnings": []}
        return super()._dispatch(wsfunction, params)

    def enrol_in(self, course_id: int, user_id: int, role_id: int = 5) -> None:
        self.enrolments.setdefault(course_id, {}).setdefault(user_id, set()).add(role_id)


def make_user(role: UserRole, username: str) -> User:
    return User(
        username=username,
        firstname="Pengguna",
        lastname="Uji",
        email=f"{username}@itk.ac.id",
        role=role,
    )


@pytest.fixture
def fake() -> GeneratedCourseMoodle:
    fake = GeneratedCourseMoodle()
    fake.enrol_in(STUDENT_COURSE_ID, 20)
    fake.enrol_in(HIDDEN_COURSE_ID, 20)
    fake.enrol_in(OTHER_COURSE_ID, 21)
    return fake


@pytest_asyncio.fixture
async def app(fake):
    application = create_app()
    moodle_client = MoodleClient(BASE_URL, TOKEN, transport=httpx.MockTransport(fake.handler))
    service = MoodleIntegrationService(moodle_client)
    application.dependency_overrides[get_moodle_integration_service] = lambda: service
    application.dependency_overrides[get_current_user] = lambda: make_user(UserRole.STUDENT, STUDENT_ACCOUNT[0])
    yield application
    await moodle_client.aclose()
    application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client


def as_user(app, role: UserRole, username: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: make_user(role, username)


def modules_by_id(contents: dict) -> dict[int, dict]:
    return {
        module["moodle_module_id"]: module
        for section in contents["sections"]
        for module in section["modules"]
    }


@pytest.mark.asyncio
async def test_student_lists_only_visible_courses_they_are_enrolled_in(client):
    response = await client.get(f"{BASE}/courses")

    assert response.status_code == 200
    assert [course["moodle_course_id"] for course in response.json()["courses"]] == [STUDENT_COURSE_ID]


@pytest.mark.asyncio
async def test_student_reads_the_generated_course_without_hidden_items(client, fake):
    course = await client.get(f"{BASE}/courses/{STUDENT_COURSE_ID}")
    response = await client.get(f"{BASE}/courses/{STUDENT_COURSE_ID}/contents")

    assert course.status_code == 200
    assert course.json()["fullname"] == "Pemrograman Web"
    assert response.status_code == 200
    contents = response.json()
    assert [section["section_number"] for section in contents["sections"]] == [0, 1, 2]
    modules = modules_by_id(contents)
    assert sorted(modules) == [501, 502, 503, 504]
    assert modules[501]["content"] == "<h2>Isi halaman yang digenerate</h2>"
    assert modules[502]["description"] == "<p>Buat halaman profil.</p>"
    assert modules[503]["url"] == "https://example.com/html"
    assert modules[504]["description"] == "<p>Kerjakan 3 soal.</p>"
    assert "belum siap" not in response.text
    # Akun integrasi tidak terdaftar di course; tanpa flag ini Moodle tidak mengembalikan assignment.
    assert fake.called("mod_assign_get_assignments")[0]["includenotenrolledcourses"] == "1"


@pytest.mark.asyncio
@pytest.mark.parametrize("course_id", [OTHER_COURSE_ID, HIDDEN_COURSE_ID, 999])
async def test_courses_a_student_cannot_access_look_like_missing_courses(client, course_id):
    detail = await client.get(f"{BASE}/courses/{course_id}")
    contents = await client.get(f"{BASE}/courses/{course_id}/contents")

    for response in (detail, contents):
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_student_without_a_moodle_enrolment_sees_no_course(app, client):
    as_user(app, UserRole.STUDENT, "mahasiswa.baru")

    courses = await client.get(f"{BASE}/courses")
    contents = await client.get(f"{BASE}/courses/{STUDENT_COURSE_ID}/contents")

    assert courses.json()["courses"] == []
    assert contents.status_code == 404


@pytest.mark.asyncio
async def test_student_access_follows_the_moodle_enrolment(app, client, fake):
    as_user(app, UserRole.STUDENT, OTHER_STUDENT_ACCOUNT[0])
    before = await client.get(f"{BASE}/courses/{STUDENT_COURSE_ID}/contents")
    fake.enrol_in(STUDENT_COURSE_ID, 21)
    after = await client.get(f"{BASE}/courses/{STUDENT_COURSE_ID}/contents")

    assert before.status_code == 404
    assert after.status_code == 200


@pytest.mark.asyncio
async def test_instructor_still_sees_every_course_and_hidden_items(app, client):
    as_user(app, UserRole.INSTRUCTOR, "dosen.uji")

    courses = await client.get(f"{BASE}/courses")
    contents = await client.get(f"{BASE}/courses/{STUDENT_COURSE_ID}/contents")

    assert [course["moodle_course_id"] for course in courses.json()["courses"]] == [
        STUDENT_COURSE_ID,
        OTHER_COURSE_ID,
        HIDDEN_COURSE_ID,
    ]
    assert [section["section_number"] for section in contents.json()["sections"]] == [0, 1, 2, 3]
    modules = modules_by_id(contents.json())
    assert modules[505]["visible"] is False
    assert modules[502]["description"] == "<p>Buat halaman profil.</p>"


@pytest.mark.asyncio
async def test_intro_lookup_failures_do_not_break_the_course_page(client, fake):
    fake.failing["mod_assign_get_assignments"] = moodle_exception(
        "accessexception", "Access control exception", "webservice_access_exception"
    )

    response = await client.get(f"{BASE}/courses/{STUDENT_COURSE_ID}/contents")

    assert response.status_code == 200
    modules = modules_by_id(response.json())
    assert modules[502]["description"] == ""
    assert modules[504]["description"] == "<p>Kerjakan 3 soal.</p>"


@pytest.mark.asyncio
async def test_student_responses_never_contain_moodle_credentials(client):
    for path in ("/courses", f"/courses/{STUDENT_COURSE_ID}", f"/courses/{STUDENT_COURSE_ID}/contents"):
        response = await client.get(f"{BASE}{path}")
        assert TOKEN not in response.text