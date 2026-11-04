"""Test dokumentasi OpenAPI authentication (BE-06.1).

Tujuan pengujian ini bukan menjalankan authentication (sudah diuji pada
``test_auth_routes.py``), melainkan memastikan kontrak yang dibaca frontend dari
OpenAPI benar-benar lengkap: contoh request, response sukses, response gagal,
header challenge, security scheme, dan format error design-api §18.

Dokumentasi yang diuji di sini tersedia pada environment development melalui:

- ``GET /docs`` — Swagger UI;
- ``GET /redoc`` — ReDoc;
- ``GET /openapi.json`` — dokumen OpenAPI mentah.

Tidak ada server database yang dibutuhkan: pengujian hanya membaca dokumen
OpenAPI dan response yang gagal sebelum handler menyentuh database.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.main import app, create_app
from src.routes.auth import AUTHENTICATION_FAILED_EXAMPLE, VALIDATION_FAILED_EXAMPLE
from src.schemas.auth import EXAMPLE_ACCESS_TOKEN

LOGIN_PATH = "/api/v1/auth/login"
ME_PATH = "/api/v1/auth/me"


@pytest.fixture(scope="module")
def openapi() -> dict:
    return create_app().openapi()


@pytest.fixture(scope="module")
def login_operation(openapi: dict) -> dict:
    return openapi["paths"][LOGIN_PATH]["post"]


@pytest.fixture(scope="module")
def me_operation(openapi: dict) -> dict:
    return openapi["paths"][ME_PATH]["get"]


def response_schema_ref(operation: dict, status_code: str) -> str:
    return operation["responses"][status_code]["content"]["application/json"]["schema"]["$ref"]


# ---------------------------------------------------------------------------
# Ketersediaan dokumentasi di environment development
# ---------------------------------------------------------------------------


def test_swagger_ui_is_available_in_development():
    response = TestClient(app).get("/docs")

    assert response.status_code == 200
    assert "Swagger UI" in response.text


def test_redoc_is_available_in_development():
    response = TestClient(app).get("/redoc")

    assert response.status_code == 200
    assert "ReDoc" in response.text


def test_openapi_document_is_available_in_development():
    response = TestClient(app).get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"]


def test_both_authentication_endpoints_are_documented(openapi):
    assert set(openapi["paths"][LOGIN_PATH]) == {"post"}
    assert set(openapi["paths"][ME_PATH]) == {"get"}
    assert openapi["paths"][LOGIN_PATH]["post"]["tags"] == ["Authentication"]
    assert openapi["paths"][ME_PATH]["get"]["tags"] == ["Authentication"]


# ---------------------------------------------------------------------------
# POST /api/v1/auth/login
# ---------------------------------------------------------------------------


def test_login_has_a_human_readable_summary_and_description(login_operation):
    assert "login" in login_operation["summary"].lower()
    assert "username atau email" in login_operation["description"].lower()
    assert "401" in login_operation["description"]


def test_login_has_runnable_identifier_examples(login_operation):
    examples = login_operation["requestBody"]["content"]["application/json"]["examples"]

    assert set(examples) == {"email", "username"}
    assert examples["email"]["value"]["username"] == "dosen.demo@itk.ac.id"
    assert examples["username"]["value"]["username"] == "dosen.demo"
    assert all(item["value"]["password"] for item in examples.values())


def test_login_documents_success_response_and_token(login_operation, openapi):
    assert response_schema_ref(login_operation, "200").endswith("/LoginResponse")

    login_response = openapi["components"]["schemas"]["LoginResponse"]
    access_token = login_response["properties"]["access_token"]

    assert "Authorization: Bearer" in access_token["description"]
    assert "ACCESS_TOKEN_EXPIRE_MINUTES" in access_token["description"]
    assert "exp" in access_token["description"]
    assert login_response["example"]["access_token"] == EXAMPLE_ACCESS_TOKEN


def test_login_documents_authentication_failure(login_operation):
    failure = login_operation["responses"]["401"]

    assert response_schema_ref(login_operation, "401").endswith("/ErrorResponse")
    assert failure["headers"]["WWW-Authenticate"]["schema"]["example"] == "Bearer"
    assert failure["content"]["application/json"]["example"] == AUTHENTICATION_FAILED_EXAMPLE
    assert "password" in failure["description"].lower()


def test_login_documents_validation_failure(login_operation):
    failure = login_operation["responses"]["422"]

    assert response_schema_ref(login_operation, "422").endswith("/ErrorResponse")
    assert failure["content"]["application/json"]["example"] == VALIDATION_FAILED_EXAMPLE


# ---------------------------------------------------------------------------
# GET /api/v1/auth/me
# ---------------------------------------------------------------------------


def test_me_requires_bearer_authentication(me_operation):
    assert me_operation["security"] == [{"HTTPBearer": []}]


def test_me_documents_success_identity_fields(me_operation, openapi):
    assert response_schema_ref(me_operation, "200").endswith("/CurrentUserResponse")

    schema = openapi["components"]["schemas"]["CurrentUserResponse"]
    assert set(schema["required"]) == {
        "id",
        "username",
        "firstname",
        "lastname",
        "email",
        "role",
    }
    assert schema["example"]["role"] == "INSTRUCTOR"


def test_me_documents_expired_or_missing_token(me_operation):
    failure = me_operation["responses"]["401"]

    assert response_schema_ref(me_operation, "401").endswith("/ErrorResponse")
    assert failure["content"]["application/json"]["example"] == AUTHENTICATION_FAILED_EXAMPLE
    assert "kedaluwarsa" in failure["description"]


# ---------------------------------------------------------------------------
# Error format design-api §18
# ---------------------------------------------------------------------------


def test_error_response_schema_follows_the_standard_envelope(openapi):
    error_response = openapi["components"]["schemas"]["ErrorResponse"]
    error_envelope = openapi["components"]["schemas"]["ErrorEnvelope"]

    assert error_response["required"] == ["error"]
    assert set(error_envelope["required"]) == {"code", "message"}
    assert error_envelope["properties"]["details"]["items"]["$ref"].endswith("/ErrorDetail")


def test_all_documented_422_responses_use_the_standard_envelope(openapi):
    """Dokumentasi 422 tidak boleh kembali memakai HTTPValidationError default."""
    refs = [
        operation["responses"]["422"]["content"]["application/json"]["schema"]["$ref"]
        for path_item in openapi["paths"].values()
        for operation in path_item.values()
        if isinstance(operation, dict) and "422" in operation.get("responses", {})
    ]

    assert refs
    assert all(ref.endswith("/ErrorResponse") for ref in refs)


def test_role_values_in_documentation_match_the_backend_enum(openapi):
    role_schema = openapi["components"]["schemas"]["UserRole"]

    assert role_schema["enum"] == ["INSTRUCTOR", "STUDENT", "ADMIN"]


def test_invalid_login_payload_returns_the_standard_error_format():
    client = TestClient(create_app(), raise_server_exceptions=False)

    response = client.post(LOGIN_PATH, json={"username": "dosen.demo"})

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "VALIDATION_FAILED",
            "message": "Data request tidak valid.",
            "details": [{"field": "password", "message": "Field required"}],
        }
    }


def test_validation_error_never_echoes_the_submitted_password():
    secret = "RahasiaYangTidakBolehBocor" * 5
    client = TestClient(create_app(), raise_server_exceptions=False)

    response = client.post(LOGIN_PATH, json={"username": "dosen.demo", "password": secret})

    assert response.status_code == 422
    assert secret not in response.text
    assert "Rahasia" not in response.text
    # Hanya lokasi dan pesan validasi yang boleh tampil.
    assert set(response.json()["error"]["details"][0]) == {"field", "message"}


def test_missing_authentication_returns_the_documented_error_body():
    client = TestClient(create_app(), raise_server_exceptions=False)

    response = client.get(ME_PATH)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == AUTHENTICATION_FAILED_EXAMPLE
