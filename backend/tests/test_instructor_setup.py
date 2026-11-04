"""Test setup dosen (BE-10).

Cakupan: aturan domain (batas panjang Additional Prompt, minimal satu jenis
aktivitas aktif), penyimpanan/pembacaan lewat service di atas PostgreSQL,
kontrak HTTP design-api §7 (parsial update, role INSTRUCTOR, ``422
INVALID_REQUEST`` dengan detail per field), konteks agent (YAML beserta
penandanya), dan seed setup default akun dosen uji.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime

import httpx
import pytest
import pytest_asyncio

from src.main import create_app
from src.services.auth import hash_password
from src.services.dependencies import get_db_session
from src.services.instructor import (
    ACADEMIC_SOURCE_OF_TRUTH,
    CONTEXT_ROLE,
    ActivityConfiguration,
    InstructorProfile,
    InstructorSetup,
    InstructorSetupError,
    InstructorSetupService,
    InstructorSetupValidationError,
    normalize_setup,
    to_agent_context,
)
from src.services.seed import (
    INSTRUCTOR_ACCOUNT,
    STUDENT_ACCOUNT,
    SeedAction,
    seed_instructor_setup,
    seed_test_accounts,
)
from src.services.user import UserRole, UserService

PASSWORD = "SecretPassword123"
SETUP_URL = "/api/v1/instructors/me/setup"

SETUP_BODY = {
    "instructor_profile": {
        "teaching_style": "Banyak studi kasus",
        "expertise": "Rekayasa Perangkat Lunak",
        "delivery_preference": "Penjelasan bertahap",
        "language_preference": "Bahasa Indonesia",
    },
    "additional_prompt": "Sertakan contoh SQL.",
    "activity_configuration": {
        "learning_material": True,
        "learning_resource": True,
        "assignment": True,
        "quiz": False,
    },
}

RESPONSE_DEFAULT = {
    "instructor_profile": {
        "teaching_style": "",
        "expertise": "",
        "delivery_preference": "",
        "language_preference": "",
    },
    "additional_prompt": "",
    "activity_configuration": {
        "learning_material": True,
        "learning_resource": False,
        "assignment": False,
        "quiz": False,
    },
}


def build_profile(**overrides) -> InstructorProfile:
    values = {**SETUP_BODY["instructor_profile"], **overrides}
    return InstructorProfile(**values)


def build_activity(**overrides) -> ActivityConfiguration:
    values = {**SETUP_BODY["activity_configuration"], **overrides}
    return ActivityConfiguration(
        additional_prompt=values.pop("additional_prompt", SETUP_BODY["additional_prompt"]),
        **values,
    )


# --- Aturan domain ---------------------------------------------------------


def test_default_activity_configuration_matches_be_10_1():
    activity = ActivityConfiguration()

    assert activity.learning_material is True
    assert activity.enabled_activity_types == ("learning_material",)
    assert activity.additional_prompt is None


def test_normalize_setup_cleans_text():
    setup = normalize_setup(
        profile=InstructorProfile(
            teaching_style="  studi kasus  ",
            expertise="  Basis Data ",
            delivery_preference=" bertahap ",
            language_preference=" Bahasa Indonesia ",
        ),
        activity=ActivityConfiguration(quiz=True, additional_prompt="  pakai SQL  "),
        prompt_max_length=100,
    )

    assert setup.profile.teaching_style == "studi kasus"
    assert setup.profile.expertise == "Basis Data"
    assert setup.profile.delivery_preference == "bertahap"
    assert setup.profile.language_preference == "Bahasa Indonesia"
    assert setup.activity.quiz is True
    assert setup.activity.additional_prompt == "pakai SQL"


def test_blank_additional_prompt_is_stored_as_none():
    setup = normalize_setup(
        profile=InstructorProfile(),
        activity=ActivityConfiguration(additional_prompt="   "),
        prompt_max_length=100,
    )

    assert setup.activity.additional_prompt is None


def test_additional_prompt_over_limit_is_rejected_per_field():
    with pytest.raises(InstructorSetupValidationError) as excinfo:
        normalize_setup(
            profile=InstructorProfile(),
            activity=ActivityConfiguration(additional_prompt="x" * 51),
            prompt_max_length=50,
        )

    error = excinfo.value
    assert (error.status_code, error.error_code) == (422, "INVALID_REQUEST")
    assert error.details == [{"field": "additional_prompt", "message": "maksimal 50 karakter"}]


def test_configuration_without_any_active_activity_is_rejected():
    with pytest.raises(InstructorSetupValidationError) as excinfo:
        normalize_setup(
            profile=InstructorProfile(),
            activity=ActivityConfiguration(
                learning_material=False,
                learning_resource=False,
                assignment=False,
                quiz=False,
            ),
            prompt_max_length=2000,
        )

    assert [detail["field"] for detail in excinfo.value.details] == ["activity_configuration"]


def test_all_violations_are_reported_together():
    with pytest.raises(InstructorSetupValidationError) as excinfo:
        normalize_setup(
            profile=InstructorProfile(
                teaching_style="x" * 2001,
                expertise="y" * 2001,
                language_preference="Bahasa Indonesia " * 4,
            ),
            activity=ActivityConfiguration(
                learning_material=False, additional_prompt="z" * 11
            ),
            prompt_max_length=10,
        )

    fields = [detail["field"] for detail in excinfo.value.details]
    assert "instructor_profile.teaching_style" in fields
    assert "instructor_profile.expertise" in fields
    assert "instructor_profile.language_preference" in fields
    assert "additional_prompt" in fields
    assert "activity_configuration" in fields


# --- Service & repository -------------------------------------------------


@pytest_asyncio.fixture
async def service(db_session) -> InstructorSetupService:
    return InstructorSetupService.from_session(db_session, prompt_max_length=50)


@pytest_asyncio.fixture
async def instructor_id(db_session) -> str:
    user = await UserService.from_session(db_session).create_user(
        username="dosen.setup",
        firstname="Dosen",
        lastname="Setup",
        email="dosen.setup@itk.ac.id",
        role=UserRole.INSTRUCTOR,
        password=hash_password(PASSWORD),
    )
    return user.id


@pytest.mark.asyncio
async def test_new_instructor_gets_default_setup(service, instructor_id):
    setup = await service.get_setup(instructor_id)

    assert setup.profile == InstructorProfile()
    assert setup.activity == ActivityConfiguration()
    assert setup.updated_at is None


@pytest.mark.asyncio
async def test_partial_update_keeps_the_other_fields(service, instructor_id):
    await service.update_setup(
        instructor_id,
        profile_changes={"teaching_style": "Banyak studi kasus", "expertise": "Basis Data"},
        activity_changes={"quiz": True, "additional_prompt": "pakai SQL"},
    )
    updated = await service.update_setup(
        instructor_id, profile_changes={"delivery_preference": "ringkas"}
    )

    assert updated.profile.teaching_style == "Banyak studi kasus"
    assert updated.profile.expertise == "Basis Data"
    assert updated.profile.delivery_preference == "ringkas"
    assert updated.activity.quiz is True
    assert updated.activity.additional_prompt == "pakai SQL"
    assert updated.updated_at is not None


@pytest.mark.asyncio
async def test_empty_prompt_clears_it(service, instructor_id):
    await service.update_setup(
        instructor_id, activity_changes={"additional_prompt": "pakai SQL"}
    )

    cleared = await service.update_setup(instructor_id, activity_changes={"additional_prompt": ""})

    assert cleared.activity.additional_prompt is None


@pytest.mark.asyncio
async def test_invalid_merge_is_not_persisted(service, instructor_id):
    with pytest.raises(InstructorSetupValidationError):
        await service.update_setup(
            instructor_id,
            activity_changes={
                "learning_material": False,
                "learning_resource": False,
                "assignment": False,
                "quiz": False,
            },
        )

    assert await service.get_setup(instructor_id) == InstructorSetup()


@pytest.mark.asyncio
async def test_ensure_default_setup_does_not_overwrite_existing(service, instructor_id):
    saved = await service.update_setup(
        instructor_id, profile_changes={"teaching_style": "ringkas"}
    )

    assert await service.ensure_default_setup(instructor_id) is False
    assert await service.get_setup(instructor_id) == saved


@pytest.mark.asyncio
async def test_ensure_default_setup_creates_missing_rows(service, instructor_id):
    assert await service.ensure_default_setup(instructor_id) is True
    assert await service.ensure_default_setup(instructor_id) is False

    stored = await service.find_setup(instructor_id)
    assert stored is not None
    assert stored.profile == InstructorProfile()
    assert stored.activity == ActivityConfiguration()


# --- Konteks agent (BE-10.3) ----------------------------------------------


@pytest.mark.asyncio
async def test_agent_context_marks_itself_below_rps(service, instructor_id):
    await service.update_setup(
        instructor_id,
        profile_changes=SETUP_BODY["instructor_profile"],
        activity_changes={
            **SETUP_BODY["activity_configuration"],
            "additional_prompt": SETUP_BODY["additional_prompt"],
        },
    )

    context = await service.get_agent_context(instructor_id)

    assert context["context_role"] == CONTEXT_ROLE == "supporting"
    assert context["academic_source_of_truth"] == ACADEMIC_SOURCE_OF_TRUTH == "rps"
    assert context["instructor_profile"]["expertise"] == "Rekayasa Perangkat Lunak"
    assert context["additional_prompt"] == "Sertakan contoh SQL."
    # Seluruh jenis aktivitas ditulis eksplisit, termasuk yang nonaktif.
    assert context["activity_configuration"] == {
        "learning_material": True,
        "learning_resource": True,
        "assignment": True,
        "quiz": False,
    }


def test_empty_profile_fields_are_left_out_of_the_context():
    context = to_agent_context(
        normalize_setup(
            profile=InstructorProfile(),
            activity=ActivityConfiguration(),
            prompt_max_length=2000,
        )
    )

    assert "instructor_profile" not in context
    assert "additional_prompt" not in context
    assert context["activity_configuration"]["learning_material"] is True


@pytest.mark.asyncio
async def test_agent_context_yaml_is_renderable(service, instructor_id):
    await service.update_setup(
        instructor_id,
        profile_changes={"expertise": "Basis Data", "language_preference": "Bahasa Indonesia"},
        activity_changes={"quiz": True, "additional_prompt": "pakai SQL"},
    )

    yaml_text = await service.get_agent_context_yaml(instructor_id)

    assert "context_role: supporting" in yaml_text
    assert "academic_source_of_truth: rps" in yaml_text
    assert "expertise: Basis Data" in yaml_text
    assert "additional_prompt: pakai SQL" in yaml_text
    assert "quiz: true" in yaml_text
    assert yaml_text.endswith("\n")


# --- HTTP contract --------------------------------------------------------


@pytest_asyncio.fixture
async def app(db_session) -> AsyncIterator:
    application = create_app()

    async def override_get_db_session():
        yield db_session

    application.dependency_overrides[get_db_session] = override_get_db_session
    yield application
    application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app) -> AsyncIterator[httpx.AsyncClient]:
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
async def instructor_headers(client, user_service) -> dict[str, str]:
    await create_user(user_service, email="dosen@itk.ac.id", role=UserRole.INSTRUCTOR)
    return await login(client, email="dosen@itk.ac.id")


@pytest_asyncio.fixture
async def student_headers(client, user_service) -> dict[str, str]:
    await create_user(user_service, email="mahasiswa@itk.ac.id", role=UserRole.STUDENT)
    return await login(client, email="mahasiswa@itk.ac.id")


def without_updated_at(body: dict) -> dict:
    return {key: value for key, value in body.items() if key != "updated_at"}


@pytest.mark.asyncio
async def test_get_setup_returns_defaults(client, instructor_headers):
    response = await client.get(SETUP_URL, headers=instructor_headers)

    assert response.status_code == 200
    assert without_updated_at(response.json()) == RESPONSE_DEFAULT
    assert datetime.fromisoformat(response.json()["updated_at"])


@pytest.mark.asyncio
async def test_put_then_get_returns_the_same_setup(client, instructor_headers):
    saved = await client.put(SETUP_URL, headers=instructor_headers, json=SETUP_BODY)

    assert saved.status_code == 200
    assert without_updated_at(saved.json()) == SETUP_BODY

    loaded = await client.get(SETUP_URL, headers=instructor_headers)
    assert without_updated_at(loaded.json()) == SETUP_BODY


@pytest.mark.asyncio
async def test_update_is_partial(client, instructor_headers):
    await client.put(SETUP_URL, headers=instructor_headers, json=SETUP_BODY)

    response = await client.put(
        SETUP_URL, headers=instructor_headers, json={"instructor_profile": {"teaching_style": "Ringkas"}}
    )

    body = response.json()
    assert response.status_code == 200
    assert body["instructor_profile"]["teaching_style"] == "Ringkas"
    # Field lain tidak dikirim, jadi tidak berubah.
    assert body["instructor_profile"]["expertise"] == "Rekayasa Perangkat Lunak"
    assert body["additional_prompt"] == "Sertakan contoh SQL."
    assert body["activity_configuration"]["learning_resource"] is True


@pytest.mark.asyncio
async def test_explicit_false_is_applied_while_unsent_flags_are_kept(client, instructor_headers):
    await client.put(SETUP_URL, headers=instructor_headers, json=SETUP_BODY)

    response = await client.put(
        SETUP_URL,
        headers=instructor_headers,
        json={"activity_configuration": {"learning_resource": False}},
    )

    configuration = response.json()["activity_configuration"]
    assert configuration["learning_resource"] is False
    assert configuration["learning_material"] is True
    assert configuration["assignment"] is True


@pytest.mark.asyncio
async def test_empty_prompt_and_empty_body_keep_current_setup(client, instructor_headers):
    await client.put(SETUP_URL, headers=instructor_headers, json=SETUP_BODY)

    unchanged = await client.put(SETUP_URL, headers=instructor_headers, json={})
    cleared = await client.put(
        SETUP_URL, headers=instructor_headers, json={"additional_prompt": ""}
    )

    assert without_updated_at(unchanged.json()) == SETUP_BODY
    assert cleared.json()["additional_prompt"] == ""


@pytest.mark.asyncio
async def test_other_instructor_does_not_see_saved_setup(
    client, user_service, instructor_headers
):
    await client.put(SETUP_URL, headers=instructor_headers, json=SETUP_BODY)
    await create_user(user_service, email="dosen2@itk.ac.id", role=UserRole.INSTRUCTOR)
    other_headers = await login(client, email="dosen2@itk.ac.id")

    response = await client.get(SETUP_URL, headers=other_headers)

    assert response.status_code == 200
    assert without_updated_at(response.json()) == RESPONSE_DEFAULT


@pytest.mark.parametrize("method", ["GET", "PUT"])
@pytest.mark.asyncio
async def test_student_cannot_access_setup(client, student_headers, method):
    response = await client.request(method, SETUP_URL, headers=student_headers, json={})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTHORIZATION_DENIED"


@pytest.mark.parametrize("method", ["GET", "PUT"])
@pytest.mark.asyncio
async def test_setup_requires_authentication(client, method):
    response = await client.request(method, SETUP_URL, json={})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


@pytest.mark.asyncio
async def test_prompt_over_limit_is_rejected_with_field_details(client, instructor_headers):
    response = await client.put(
        SETUP_URL, headers=instructor_headers, json={"additional_prompt": "x" * 2001}
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "INVALID_REQUEST"
    assert error["details"] == [
        {"field": "additional_prompt", "message": "maksimal 2000 karakter"}
    ]


@pytest.mark.asyncio
async def test_configuration_without_active_activity_is_rejected(client, instructor_headers):
    response = await client.put(
        SETUP_URL,
        headers=instructor_headers,
        json={
            "activity_configuration": {
                "learning_material": False,
                "learning_resource": False,
                "assignment": False,
                "quiz": False,
            }
        },
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "INVALID_REQUEST"
    assert [detail["field"] for detail in error["details"]] == ["activity_configuration"]


@pytest.mark.asyncio
async def test_wrong_field_type_is_reported_as_invalid_request(client, instructor_headers):
    response = await client.put(
        SETUP_URL,
        headers=instructor_headers,
        json={"activity_configuration": {"quiz": "bukan boolean"}},
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "INVALID_REQUEST"
    assert [detail["field"] for detail in error["details"]] == ["activity_configuration.quiz"]


@pytest.mark.asyncio
async def test_setup_contract_is_published_in_openapi(app):
    schema = app.openapi()
    operation = schema["paths"][SETUP_URL]["put"]

    assert operation["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/InstructorSetupUpdate"
    )
    assert operation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/InstructorSetupResponse")

    published = schema["components"]["schemas"]["InstructorSetupResponse"]
    assert set(published["properties"]) == {
        "instructor_profile",
        "additional_prompt",
        "activity_configuration",
        "updated_at",
    }
    # Contoh response tetap ada supaya frontend dapat menyalinnya ke mock.
    assert published["example"]

    error_example = operation["responses"]["422"]["content"]["application/json"]["example"]
    assert error_example["error"]["code"] == "INVALID_REQUEST"


def test_domain_error_carries_public_contract():
    error = InstructorSetupError()

    assert error.status_code == 500
    assert error.error_code == "INTERNAL_ERROR"
    assert error.details == []


# --- Seed (BE-10.1) -------------------------------------------------------


@pytest.mark.asyncio
async def test_seed_creates_default_setup_and_keeps_it_idempotent(db_session, service):
    results = await seed_test_accounts(
        db_session,
        passwords={
            INSTRUCTOR_ACCOUNT.username: PASSWORD,
            STUDENT_ACCOUNT.username: PASSWORD,
        },
    )
    instructor = next(result for result in results if result.account is INSTRUCTOR_ACCOUNT)
    assert instructor.action is SeedAction.CREATED

    assert await seed_instructor_setup(db_session) is True
    assert await seed_instructor_setup(db_session) is False

    setup = await service.get_setup(instructor.user_id)
    assert setup.activity.learning_material is True
    assert setup.activity.assignment is False
