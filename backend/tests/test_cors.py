"""Test CORS untuk integrasi frontend development (BE-06.2).

Frontend Vite berjalan di ``http://localhost:3000``, backend di
``http://localhost:8000``. Browser akan mengirim preflight untuk request login
(header ``Content-Type``/``Authorization``), sehingga middleware harus:

- mengizinkan origin yang terdaftar dan mengembalikan header CORS yang benar;
- menolak preflight dari origin yang tidak terdaftar;
- tetap menyertakan header CORS pada response error (401/422).

Pengujian memakai origin yang di-set langsung pada settings aplikasi supaya
tidak bergantung pada file ``.env`` developer.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.config.settings import settings
from src.main import create_app

ALLOWED_ORIGIN = "http://localhost:3000"
OTHER_ALLOWED_ORIGIN = "http://127.0.0.1:3000"
DISALLOWED_ORIGIN = "http://evil.example"
LOGIN_PATH = "/api/v1/auth/login"


@pytest.fixture
def client(monkeypatch) -> TestClient:
    monkeypatch.setattr(settings, "CORS_ORIGINS", [ALLOWED_ORIGIN, OTHER_ALLOWED_ORIGIN])
    with TestClient(create_app()) as test_client:
        yield test_client


def preflight(
    client: TestClient,
    origin: str,
    *,
    method: str = "POST",
    headers: str = "authorization,content-type",
):
    return client.options(
        LOGIN_PATH,
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": headers,
        },
    )


# ---------------------------------------------------------------------------
# Origin terdaftar
# ---------------------------------------------------------------------------


def test_preflight_from_the_frontend_origin_is_allowed(client):
    response = preflight(client, ALLOWED_ORIGIN)

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert "POST" in response.headers["access-control-allow-methods"]
    assert response.headers["access-control-max-age"] == "600"


def test_preflight_allows_authorization_and_idempotency_headers(client):
    response = preflight(
        client,
        ALLOWED_ORIGIN,
        headers="authorization,content-type,idempotency-key",
    )

    allowed = {
        header.strip().lower()
        for header in response.headers["access-control-allow-headers"].split(",")
    }
    assert {"authorization", "content-type", "idempotency-key"} <= allowed


def test_preflight_for_every_method_used_by_frontend(client):
    for method in ("GET", "POST", "PUT", "PATCH", "DELETE"):
        response = preflight(client, ALLOWED_ORIGIN, method=method)

        assert response.status_code == 200, method
        assert method in response.headers["access-control-allow-methods"]


def test_simple_request_receives_the_cors_header(client):
    response = client.get("/health", headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert "Origin" in response.headers["vary"]


def test_second_configured_origin_is_also_allowed(client):
    response = preflight(client, OTHER_ALLOWED_ORIGIN)

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == OTHER_ALLOWED_ORIGIN


def test_credentials_mode_is_disabled_for_bearer_token_authentication(client):
    """API memakai bearer token di header, bukan cookie; credential mode tidak perlu."""
    response = preflight(client, ALLOWED_ORIGIN)

    assert "access-control-allow-credentials" not in response.headers


# ---------------------------------------------------------------------------
# Origin tidak terdaftar
# ---------------------------------------------------------------------------


def test_preflight_from_an_unregistered_origin_is_rejected(client):
    response = preflight(client, DISALLOWED_ORIGIN)

    assert response.status_code == 400
    assert "disallowed cors origin" in response.text.lower()
    assert "access-control-allow-origin" not in response.headers


def test_simple_request_from_an_unregistered_origin_gets_no_cors_header(client):
    """Server tetap memproses request, tetapi browser memblokirnya tanpa header CORS."""
    response = client.get("/health", headers={"Origin": DISALLOWED_ORIGIN})

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_wildcard_origin_is_not_used(client):
    response = preflight(client, ALLOWED_ORIGIN)

    assert response.headers["access-control-allow-origin"] != "*"


def test_empty_origin_list_rejects_every_preflight(monkeypatch):
    monkeypatch.setattr(settings, "CORS_ORIGINS", [])
    with TestClient(create_app()) as test_client:
        response = preflight(test_client, ALLOWED_ORIGIN)

    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Header CORS pada response authentication (sukses/gagal)
# ---------------------------------------------------------------------------


def test_cors_headers_are_present_on_validation_errors(client):
    response = client.post(
        LOGIN_PATH,
        headers={"Origin": ALLOWED_ORIGIN},
        json={"username": "dosen.demo"},
    )

    assert response.status_code == 422
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN


def test_cors_headers_are_present_on_authentication_errors(client):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Origin": ALLOWED_ORIGIN},
    )

    assert response.status_code == 401
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert response.headers["access-control-expose-headers"] == "WWW-Authenticate"
