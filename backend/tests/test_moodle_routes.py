
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio

from src.config.settings import get_settings
from src.main import create_app
from src.services.dependencies import (
    get_auth_service,
    get_current_user,
    get_moodle_integration_service,
)
from src.services.moodle_client import MoodleClient
from src.services.moodle_integration_service import MoodleIntegrationService
from src.services.user.domain import User
from src.services.user.enums import UserRole
from tests.moodle_fakes import BASE_URL, TOKEN, FakeMoodle, moodle_exception

BASE = "/api/v1/integrations/moodle"

NEW_COURSE = {"fullname": "Basis Data", "shortname": "BD101"}
NEW_SECTION = {"name": "Minggu 2"}

READ_ENDPOINTS = [
    ("GET", "/status", None),
    ("GET", "/courses", None),
    ("GET", "/courses/2", None),
    ("GET", "/courses/2/contents", None),
]
WRITE_ENDPOINTS = [
    ("POST", "/courses", NEW_COURSE),
    ("POST", "/courses/2/sections", NEW_SECTION),
]


def make_user(role: UserRole) -> User:
    return User(
        username="dosen",
        firstname="Dosen",
        lastname="Uji",
        email="dosen@itk.ac.id",
        role=role,
    )


@pytest.fixture
def fake() -> FakeMoodle:
    return FakeMoodle()


@pytest_asyncio.fixture
async def app(fake):
    application = create_app()
    moodle_client = MoodleClient(BASE_URL, TOKEN, transport=httpx.MockTransport(fake.handler))
    service = MoodleIntegrationService(moodle_client)
    application.dependency_overrides[get_moodle_integration_service] = lambda: service
    application.dependency_overrides[get_current_user] = lambda: make_user(UserRole.INSTRUCTOR)
    application.dependency_overrides[get_settings] = lambda: SimpleNamespace(APP_ENV="development")
    yield application
    await moodle_client.aclose()
    application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client


def as_role(app, role: UserRole) -> None:
    app.dependency_overrides[get_current_user] = lambda: make_user(role)


def set_environment(app, name: str) -> None:
    app.dependency_overrides[get_settings] = lambda: SimpleNamespace(APP_ENV=name)


async def call(client, method: str, path: str, body=None) -> httpx.Response:
    return await client.request(method, f"{BASE}{path}", json=body)


@pytest.mark.asyncio
async def test_status_reports_connection_version_and_functions(client):
    response = await call(client, "GET", "/status")

    assert response.status_code == 200
    body = response.json()
    assert body["connected"] is True
    assert body["status"] == "CONNECTED"
    assert body["message"]
    assert body["site_name"] == "Moodle ITK"
    assert body["release"].startswith("4.5")
    assert body["version"] == "2024100701"
    assert body["all_functions_available"] is True
    assert {item["name"] for item in body["functions"]} >= {
        "core_course_get_courses",
        "core_course_get_contents",
    }


@pytest.mark.asyncio
async def test_status_flags_missing_functions(client, fake):
    fake.functions.remove("core_course_get_contents")

    body = (await call(client, "GET", "/status")).json()

    assert body["all_functions_available"] is False
    missing = [item["name"] for item in body["functions"] if not item["available"]]
    assert missing == ["core_course_get_contents"]


@pytest.mark.asyncio
async def test_course_list_contains_selectable_courses_only(client):
    response = await call(client, "GET", "/courses")

    assert response.status_code == 200
    courses = response.json()["courses"]
    assert [course["moodle_course_id"] for course in courses] == [2]
    assert set(courses[0]) == {
        "id",
        "moodle_course_id",
        "fullname",
        "shortname",
        "visible",
        "summary",
        "category_id",
        "category",
    }


@pytest.mark.asyncio
async def test_single_course_can_be_read(client):
    response = await call(client, "GET", "/courses/2")

    assert response.status_code == 200
    assert response.json()["shortname"] == "PW101"


@pytest.mark.asyncio
async def test_unknown_course_returns_resource_not_found(client):
    for path in ("/courses/999", "/courses/999/contents"):
        response = await call(client, "GET", path)

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_contents_expose_what_actually_exists_in_moodle(client, fake):
    fake.pages[501] = "<h2>Konten hasil generate Minggu 1</h2>"

    response = await call(client, "GET", "/courses/2/contents")

    assert response.status_code == 200
    body = response.json()
    assert body["moodle_course_id"] == 2
    week_one = body["sections"][1]
    assert week_one["name"] == "Minggu 1"
    page = week_one["modules"][0]
    assert page["modname"] == "page"
    assert page["content"] == "<h2>Konten hasil generate Minggu 1</h2>"
    assert week_one["modules"][1]["modname"] == "assign"


@pytest.mark.asyncio
async def test_created_course_can_be_read_back(client):
    created = await call(client, "POST", "/courses", NEW_COURSE)

    assert created.status_code == 201
    course_id = created.json()["moodle_course_id"]
    assert created.json()["shortname"] == "BD101"

    single = await call(client, "GET", f"/courses/{course_id}")
    listing = await call(client, "GET", "/courses")

    assert single.json()["fullname"] == "Basis Data"
    assert course_id in [course["moodle_course_id"] for course in listing.json()["courses"]]


@pytest.mark.asyncio
async def test_created_section_can_be_read_back(client):
    created = await call(client, "POST", "/courses/2/sections", NEW_SECTION)

    assert created.status_code == 201
    assert created.json()["name"] == "Minggu 2"

    contents = await call(client, "GET", "/courses/2/contents")

    names = [section["name"] for section in contents.json()["sections"]]
    assert names == ["General", "Minggu 1", "Minggu 2"]


@pytest.mark.asyncio
async def test_existing_section_is_updated_instead_of_duplicated(client):
    response = await call(
        client, "POST", "/courses/2/sections", {"name": "Pendahuluan", "section_number": 1}
    )

    assert response.status_code == 200
    assert response.json()["moodle_section_id"] == 202
    contents = await call(client, "GET", "/courses/2/contents")
    assert [section["name"] for section in contents.json()["sections"]] == [
        "General",
        "Pendahuluan",
    ]


@pytest.mark.asyncio
async def test_write_endpoints_are_disabled_outside_development(app, client, fake):
    set_environment(app, "production")

    for method, path, body in WRITE_ENDPOINTS:
        response = await call(client, method, path, body)

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"

    assert fake.called("core_course_create_courses") == []
    assert fake.called("core_courseformat_update_course") == []


@pytest.mark.asyncio
async def test_read_endpoints_stay_available_outside_development(app, client):
    set_environment(app, "production")

    for method, path, body in READ_ENDPOINTS:
        assert (await call(client, method, path, body)).status_code == 200


@pytest.mark.asyncio
async def test_only_instructors_can_use_the_endpoints(app, client, fake):
    """Status dan write khusus dosen; course boleh dibaca mahasiswa (lihat
    ``test_moodle_student_courses.py``), admin tidak memakai endpoint ini."""
    students_denied = [READ_ENDPOINTS[0], *WRITE_ENDPOINTS]
    for role, endpoints in (
        (UserRole.STUDENT, students_denied),
        (UserRole.ADMIN, READ_ENDPOINTS + WRITE_ENDPOINTS),
    ):
        as_role(app, role)

        for method, path, body in endpoints:
            response = await call(client, method, path, body)

            assert response.status_code == 403
            assert response.json()["error"]["code"] == "AUTHORIZATION_DENIED"

    assert fake.calls == []


@pytest.mark.asyncio
async def test_requests_without_authentication_are_rejected(app, client, fake):
    del app.dependency_overrides[get_current_user]
    app.dependency_overrides[get_auth_service] = lambda: None

    for method, path, body in READ_ENDPOINTS + WRITE_ENDPOINTS:
        response = await call(client, method, path, body)

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"

    assert fake.calls == []


MOODLE_FAILURES = [
    ("authentication", 502, moodle_exception("invalidtoken", "Invalid token - token not found")),
    (
        "permission",
        502,
        moodle_exception("accessexception", "Access control exception", "webservice_access_exception"),
    ),
    ("validation", 422, moodle_exception("invalidparameter", "Invalid parameter value detected")),
    ("execution", 502, moodle_exception("somethingunexpected", "Unexpected failure")),
]


@pytest.mark.asyncio
async def test_moodle_errors_are_normalized_with_a_category(client, fake):
    for category, status_code, payload in MOODLE_FAILURES:
        fake.failing["core_webservice_get_site_info"] = payload

        response = await call(client, "GET", "/status")

        assert response.status_code == status_code
        error = response.json()["error"]
        assert error["code"] == "MOODLE_ERROR"
        assert error["details"][0]["category"] == category
        assert error["details"][0]["moodle_code"] == payload["errorcode"]
        assert TOKEN not in response.text


@pytest.mark.asyncio
async def test_timeout_is_reported_as_a_transient_gateway_timeout(client, fake):
    fake.raise_on_request = httpx.ReadTimeout("timed out")

    response = await call(client, "GET", "/status")

    assert response.status_code == 504
    error = response.json()["error"]
    assert error["code"] == "MOODLE_ERROR"
    assert error["details"][0]["category"] == "transient"
    assert error["details"][0]["retryable"] is True


@pytest.mark.asyncio
async def test_connection_failure_is_reported_as_transient(client, fake):
    fake.raise_on_request = httpx.ConnectError("connection refused")

    response = await call(client, "GET", "/courses")

    assert response.status_code == 502
    assert response.json()["error"]["details"][0]["category"] == "transient"


@pytest.mark.asyncio
async def test_wrong_moodle_token_is_an_authentication_error(app):
    fake = FakeMoodle(token="the-real-token")
    wrong_client = MoodleClient(BASE_URL, TOKEN, transport=httpx.MockTransport(fake.handler))
    app.dependency_overrides[get_moodle_integration_service] = lambda: MoodleIntegrationService(
        wrong_client
    )
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        response = await call(http_client, "GET", "/status")

    await wrong_client.aclose()
    assert response.status_code == 502
    assert response.json()["error"]["details"][0]["category"] == "authentication"
    assert TOKEN not in response.text


@pytest.mark.asyncio
async def test_duplicate_shortname_is_a_validation_error(client):
    response = await call(client, "POST", "/courses", {"fullname": "Lain", "shortname": "PW101"})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "MOODLE_ERROR"
    assert error["details"][0]["category"] == "validation"
    assert error["details"][0]["moodle_code"] == "shortnametaken"


@pytest.mark.asyncio
async def test_invalid_request_bodies_and_ids_are_rejected(client, fake):
    assert (await call(client, "POST", "/courses", {"fullname": "Tanpa shortname"})).status_code == 422
    assert (await call(client, "POST", "/courses/2/sections", {"name": ""})).status_code == 422
    assert (await call(client, "GET", "/courses/0")).status_code == 422
    assert fake.calls == []


@pytest.mark.asyncio
async def test_responses_never_contain_moodle_credentials(client):
    for method, path, body in READ_ENDPOINTS + WRITE_ENDPOINTS:
        response = await call(client, method, path, body)

        assert TOKEN not in response.text
        assert "wstoken" not in response.text.lower()
        assert BASE_URL not in response.text


@pytest.mark.asyncio
async def test_endpoints_are_documented_in_openapi(client):
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    expected = {
        f"{BASE}/status": {"get"},
        f"{BASE}/courses": {"get", "post"},
        f"{BASE}/courses/{{moodle_course_id}}": {"get"},
        f"{BASE}/courses/{{moodle_course_id}}/contents": {"get"},
        f"{BASE}/courses/{{moodle_course_id}}/sections": {"post"},
    }
    for path, methods in expected.items():
        assert methods <= set(paths[path])
        for method in methods:
            assert paths[path][method]["tags"] == ["Moodle Integration"]
            assert paths[path][method]["summary"]
    assert "502" in paths[f"{BASE}/status"]["get"]["responses"]
    assert TOKEN not in response.text


@pytest.mark.asyncio
async def test_course_list_matches_the_frontend_course_target_contract(client):
    courses = (await call(client, "GET", "/courses")).json()["courses"]

    assert courses
    for course in courses:
        assert course["id"] == course["moodle_course_id"]
        assert {"fullname", "shortname", "summary", "category"} <= set(course)
