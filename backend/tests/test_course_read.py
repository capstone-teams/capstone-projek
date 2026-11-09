"""Test endpoint baca course, plan, dan konten mingguan.

Data dibuat langsung lewat ORM (bukan lewat generator yang belum ada). Yang
diuji adalah kontrak HTTP dan scoping akses:

- ``GET /api/v1/courses`` hanya memuat course milik dosen yang login;
- course milik dosen lain → ``404 RESOURCE_NOT_FOUND`` (bukan 403);
- mahasiswa → ``403 AUTHORIZATION_DENIED``;
- ``GET .../plan`` memakai versi plan tertinggi beserta minggunya;
- ``GET .../content`` memakai versi terbaru per ``(minggu, jenis)`` dan
  mendukung filter ``?week=N``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio

from src.main import create_app
from src.models import (
    Activity,
    ActivityStatus,
    ActivityType,
    Category,
    Content,
    ContentStatus,
    ContentType,
    Course,
    CoursePlan,
    CoursePlanStatus,
    CoursePlanWeek,
    RPS,
    RPSAnalysis,
    RPSStatus,
)
from src.services.auth import hash_password
from src.services.dependencies import get_db_session
from src.services.user import UserRole, UserService

PASSWORD = "SecretPassword123"
COURSES_URL = "/api/v1/courses"


@pytest_asyncio.fixture
async def app(db_session):
    application = create_app()

    async def override_get_db_session():
        yield db_session

    application.dependency_overrides[get_db_session] = override_get_db_session
    yield application
    application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client


@pytest_asyncio.fixture
async def user_service(db_session) -> UserService:
    return UserService.from_session(db_session)


async def create_user(user_service: UserService, *, email: str, role: UserRole):
    return await user_service.create_user(
        username=email.split("@")[0],
        firstname="Pengguna",
        lastname="Uji",
        email=email,
        role=role,
        password=hash_password(PASSWORD),
    )


async def login(client: httpx.AsyncClient, *, email: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login", json={"username": email, "password": PASSWORD}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest_asyncio.fixture
async def instructors(client, user_service) -> dict[str, tuple[str, dict[str, str]]]:
    owner = await create_user(user_service, email="dosen@itk.ac.id", role=UserRole.INSTRUCTOR)
    other = await create_user(user_service, email="dosen2@itk.ac.id", role=UserRole.INSTRUCTOR)
    return {
        "owner": (owner.id, await login(client, email="dosen@itk.ac.id")),
        "other": (other.id, await login(client, email="dosen2@itk.ac.id")),
    }


@pytest_asyncio.fixture
async def student_headers(client, user_service) -> dict[str, str]:
    await create_user(
        user_service, email="mahasiswa@student.itk.ac.id", role=UserRole.STUDENT
    )
    return await login(client, email="mahasiswa@student.itk.ac.id")


async def create_course(db_session, *, instructor_id: str, shortname: str, with_plan: bool = True):
    category = Category(name=f"Kategori {shortname}", sort_order=0)
    db_session.add(category)
    await db_session.flush()

    rps = RPS(
        owner_id=instructor_id,
        file_name=f"rps-{shortname}.pdf",
        file_type="application/pdf",
        file_path=f"owner/ab/rps-{shortname}.pdf",
        file_hash="b" * 64,
        schema_version="2.0",
        status=RPSStatus.ANALYZED,
    )
    db_session.add(rps)
    await db_session.flush()

    course = Course(
        instructor_id=instructor_id,
        rps_id=rps.id,
        category=category.id,
        course_format=f"topics-{shortname}",
        sortorder=1,
        fullname=f"Course {shortname}",
        shortname=shortname,
        semester="3",
    )
    db_session.add(course)
    await db_session.flush()

    if not with_plan:
        return course

    analysis = RPSAnalysis(rps_id=rps.id, version=1)
    db_session.add(analysis)
    await db_session.flush()

    # Versi 1 lama + versi 2 terbaru: endpoint wajib memakai versi 2.
    old_plan = CoursePlan(
        course_id=course.id,
        rps_analysis_id=analysis.id,
        version=1,
        status=CoursePlanStatus.REJECTED,
    )
    db_session.add(old_plan)

    plan = CoursePlan(
        course_id=course.id,
        rps_analysis_id=analysis.id,
        version=2,
        status=CoursePlanStatus.PENDING_REVIEW,
        plan_data={"weeks": []},
    )
    db_session.add(plan)
    await db_session.flush()

    week_one = CoursePlanWeek(
        course_plan_id=plan.id,
        week_number=1,
        title="Query SQL dan JOIN",
        learning_outcomes=["SUB-3"],
        topics=["Query SQL dan JOIN"],
        methods=["Praktikum"],
    )
    week_two = CoursePlanWeek(
        course_plan_id=plan.id,
        week_number=2,
        title="Ujian Tengah Semester",
        learning_outcomes=[],
        topics=[],
        methods=[],
    )
    db_session.add_all([week_one, week_two])
    await db_session.flush()

    # Dua versi material untuk minggu 1; hanya versi terbaru yang tampil.
    db_session.add_all(
        [
            Content(
                course_plan_week_id=week_one.id,
                title="Materi lama",
                content_type=ContentType.LEARNING_MATERIAL,
                content_data={"type": "learning_material", "summary": "lama"},
                version=1,
                status=ContentStatus.DRAFT,
            ),
            Content(
                course_plan_week_id=week_one.id,
                title="Query SQL dan JOIN",
                content_type=ContentType.LEARNING_MATERIAL,
                content_data={
                    "type": "learning_material",
                    "summary": "baru",
                    "sections": [{"order": 1, "title": "INNER JOIN", "content": "..."}],
                },
                content_markdown="# Query SQL dan JOIN\n",
                version=2,
                status=ContentStatus.VALIDATED,
            ),
            Content(
                course_plan_week_id=week_one.id,
                title="Referensi tambahan",
                content_type=ContentType.RESOURCE,
                content_data={
                    "type": "resource",
                    "resource_type": "external_link",
                    "url": None,
                },
                version=1,
                status=ContentStatus.VALIDATED,
            ),
            Activity(
                course_plan_week_id=week_one.id,
                type=ActivityType.ASSIGNMENT,
                title="Latihan Query JOIN",
                activity_data={"type": "assignment", "grading": {"max_grade": 100}},
                enabled=True,
                version=1,
                status=ActivityStatus.VALIDATED,
            ),
        ]
    )
    await db_session.flush()
    await db_session.commit()
    return course


@pytest.mark.asyncio
async def test_list_only_returns_owner_courses(client, instructors, db_session):
    owner_id, owner_headers = instructors["owner"]
    other_id, _ = instructors["other"]
    await create_course(db_session, instructor_id=owner_id, shortname="IF2230-A")
    await create_course(db_session, instructor_id=other_id, shortname="IF2230-B")

    response = await client.get(COURSES_URL, headers=owner_headers)

    assert response.status_code == 200
    assert [item["shortname"] for item in response.json()["items"]] == ["IF2230-A"]


@pytest.mark.asyncio
async def test_detail_returns_owner_course_and_hides_other_course(
    client, instructors, db_session
):
    owner_id, owner_headers = instructors["owner"]
    other_id, other_headers = instructors["other"]
    course = await create_course(db_session, instructor_id=owner_id, shortname="IF2230-A")

    allowed = await client.get(f"{COURSES_URL}/{course.id}", headers=owner_headers)
    hidden = await client.get(f"{COURSES_URL}/{course.id}", headers=other_headers)

    assert allowed.status_code == 200
    assert allowed.json()["shortname"] == "IF2230-A"
    assert "rps_id" in allowed.json()
    assert hidden.status_code == 404
    assert hidden.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_student_is_forbidden(client, student_headers):
    response = await client.get(COURSES_URL, headers=student_headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTHORIZATION_DENIED"


@pytest.mark.asyncio
async def test_plan_uses_latest_version(client, instructors, db_session):
    owner_id, owner_headers = instructors["owner"]
    course = await create_course(db_session, instructor_id=owner_id, shortname="IF2230-A")

    response = await client.get(f"{COURSES_URL}/{course.id}/plan", headers=owner_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 2
    assert body["status"] == "PENDING_REVIEW"
    assert [week["week_number"] for week in body["weeks"]] == [1, 2]


@pytest.mark.asyncio
async def test_content_uses_latest_version_and_supports_week_filter(
    client, instructors, db_session
):
    owner_id, owner_headers = instructors["owner"]
    course = await create_course(db_session, instructor_id=owner_id, shortname="IF2230-A")

    response = await client.get(f"{COURSES_URL}/{course.id}/content", headers=owner_headers)
    assert response.status_code == 200
    weeks = response.json()["weeks"]
    assert [week["week"] for week in weeks] == [1, 2]

    week_one = weeks[0]
    assert [material["version"] for material in week_one["materials"]] == [2]
    assert week_one["materials"][0]["body_markdown"].startswith("# Query SQL")
    assert [resource["type"] for resource in week_one["resources"]] == ["resource"]
    assert week_one["activities"]["assignment"]["title"] == "Latihan Query JOIN"
    assert week_one["activities"]["quiz"] is None

    filtered = await client.get(
        f"{COURSES_URL}/{course.id}/content?week=2", headers=owner_headers
    )
    assert [week["week"] for week in filtered.json()["weeks"]] == [2]
    assert filtered.json()["weeks"][0]["materials"] == []


@pytest.mark.asyncio
async def test_course_without_plan_returns_empty_payload(client, instructors, db_session):
    owner_id, owner_headers = instructors["owner"]
    course = await create_course(
        db_session, instructor_id=owner_id, shortname="IF2230-NOPLAN", with_plan=False
    )

    plan = await client.get(f"{COURSES_URL}/{course.id}/plan", headers=owner_headers)
    content = await client.get(f"{COURSES_URL}/{course.id}/content", headers=owner_headers)

    assert plan.status_code == 200
    assert plan.json()["plan_id"] is None
    assert plan.json()["weeks"] == []
    assert content.status_code == 200
    assert content.json()["weeks"] == []
