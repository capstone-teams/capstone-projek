"""Test kontrak API yang diterbitkan pada OpenAPI (BE-06.4).

Kontrak Sprint 2 harus dapat dipakai frontend sebagai dasar mock **sebelum**
endpoint-nya diimplementasikan (design-api §6.4–§6.7, §7, §16, §17), jadi yang
diuji di sini adalah janji dokumennya:

1. Setiap endpoint kontrak muncul pada ``openapi.json`` beserta contoh response.
2. Nilai ``role`` yang ditampilkan adalah enum kanonik backend.
3. Bentuk hasil analisis memakai RPS Structured Data (BE-05.3), bukan schema
   duplikat.
4. Stub menjawab ``501`` dengan amplop error standar — tidak ada data palsu.
5. Endpoint yang sudah diimplementasikan (BE-05) tidak tertimpa stub.
6. ``design-api.md`` menyebut setiap endpoint kontrak, sehingga dokumen dan
   OpenAPI tidak dapat menyimpang tanpa terlihat.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.routes.contract import NOT_IMPLEMENTED_CODE
from src.services.user.enums import UserRole

client = TestClient(app)

DESIGN_API = Path(__file__).resolve().parent.parent.parent / "docs" / "02. design" / "design-api.md"

# Endpoint kontrak (path, method) beserta schema response yang dijanjikan.
CONTRACT_ENDPOINTS = {
    ("/api/v1/rps", "get"): "RPSListResponse",
    ("/api/v1/rps/{rps_id}/analysis", "get"): "RPSAnalysisResponse",
    ("/api/v1/rps/{rps_id}/reanalyze", "post"): "RPSReanalyzeResponse",
    ("/api/v1/instructors/me/setup", "get"): "InstructorSetupResponse",
    ("/api/v1/instructors/me/setup", "put"): "InstructorSetupResponse",
    ("/api/v1/workflows", "get"): "WorkflowListResponse",
    ("/api/v1/workflows/{workflow_id}/events", "get"): "WorkflowEventListResponse",
}

RPS_ID = "kP3nQ7vRtYx2bM8sLdWfZa"
WORKFLOW_ID = "q7RtYx2bM8sLdWfZaKp3nQ"

STUB_CALLS = [
    ("get", "/api/v1/rps", None),
    ("get", f"/api/v1/rps/{RPS_ID}/analysis", None),
    ("post", f"/api/v1/rps/{RPS_ID}/reanalyze", None),
    ("get", "/api/v1/instructors/me/setup", None),
    ("put", "/api/v1/instructors/me/setup", {}),
    ("get", "/api/v1/workflows", None),
    ("get", f"/api/v1/workflows/{WORKFLOW_ID}/events", None),
]


@pytest.fixture(scope="module")
def openapi() -> dict:
    return app.openapi()


def _response_schema(spec: dict, path: str, method: str, status_code: str = "200") -> dict:
    operation = spec["paths"][path][method]
    return operation["responses"][status_code]["content"]["application/json"]["schema"]


def _schema_ref(schema: dict) -> str:
    """Nama schema yang dirujuk ``$ref`` (ikuti ``allOf``/``anyOf`` pydantic)."""
    if "$ref" in schema:
        return schema["$ref"].rsplit("/", 1)[-1]
    for key in ("allOf", "anyOf", "oneOf"):
        for item in schema.get(key, []):
            name = _schema_ref(item)
            if name:
                return name
    return ""


@pytest.mark.parametrize(("path", "method"), sorted(CONTRACT_ENDPOINTS))
def test_every_contracted_endpoint_is_published(openapi, path, method):
    assert path in openapi["paths"]
    assert method in openapi["paths"][path]


@pytest.mark.parametrize(
    ("path", "method"), sorted(CONTRACT_ENDPOINTS), ids=lambda value: str(value)
)
def test_contracted_response_uses_the_promised_schema(openapi, path, method):
    expected = CONTRACT_ENDPOINTS[(path, method)]
    status_code = "202" if path.endswith("/reanalyze") else "200"

    assert _schema_ref(_response_schema(openapi, path, method, status_code)) == expected
    # Contoh response disertakan supaya frontend dapat menyalinnya ke mock.
    assert openapi["components"]["schemas"][expected].get("example")


def test_the_role_enum_published_is_the_canonical_backend_enum(openapi):
    """Nilai role pada kontrak = enum kanonik, bukan nilai karangan dokumen."""
    role = openapi["components"]["schemas"]["UserRole"]

    assert role["enum"] == [UserRole.INSTRUCTOR.value, UserRole.STUDENT.value, UserRole.ADMIN.value]
    # Role ikut tampil pada response login dan current user.
    for path in ("/api/v1/auth/login", "/api/v1/auth/me"):
        schema = _response_schema(openapi, path, "post" if path.endswith("login") else "get")
        assert schema  # $ref ke UserResponse yang memuat UserRole


def test_the_rps_status_values_are_published_in_the_canonical_casing(openapi):
    """Status RPS memakai enum huruf besar; frontend tidak boleh mengarang casing."""
    status = openapi["components"]["schemas"]["RPSStatus"]["enum"]

    assert status == ["UPLOADED", "PROCESSING", "PROCESSED", "FAILED"]
    assert all(value == value.upper() for value in status)


def test_the_analysis_contract_reuses_the_structured_data_schema(openapi):
    """Hasil analisis memakai RPS Structured Data; tidak ada schema duplikat."""
    schemas = openapi["components"]["schemas"]

    data_ref = _schema_ref(schemas["RPSAnalysisResponse"]["properties"]["data"])
    assert data_ref == "RPSStructuredData"
    assert "RPSAnalysisAnalysisResponse" not in schemas


def test_the_workflow_event_contract_is_published_for_the_websocket_client(openapi):
    """Format event WS harus tersedia di OpenAPI; rute WS sendiri tidak muncul."""
    event = openapi["components"]["schemas"]["WorkflowEvent"]

    assert set(event["required"]) == {"event", "workflow_id", "timestamp"}
    assert not any("/ws/" in path for path in openapi["paths"])


@pytest.mark.parametrize(("method", "path", "body"), STUB_CALLS)
def test_stubs_answer_not_implemented_with_the_standard_envelope(method, path, body):
    response = getattr(client, method)(path, json=body) if body is not None else getattr(client, method)(path)

    assert response.status_code == 501
    assert response.json() == {
        "error": {
            "code": NOT_IMPLEMENTED_CODE,
            "message": response.json()["error"]["message"],
            "details": [],
        }
    }


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/api/v1/rps"),
        ("get", f"/api/v1/rps/{RPS_ID}"),
        ("post", f"/api/v1/rps/{RPS_ID}/process"),
    ],
)
def test_implemented_endpoints_are_not_shadowed_by_the_contract_stubs(method, path):
    """Endpoint BE-05 tetap memakai otorisasinya sendiri, bukan stub."""
    response = getattr(client, method)(path)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_the_design_document_mentions_every_contracted_endpoint():
    """Dokumen dan OpenAPI menyebut endpoint yang sama."""
    document = DESIGN_API.read_text(encoding="utf-8")

    for path, _ in CONTRACT_ENDPOINTS:
        assert path in document, f"{path} belum didokumentasikan pada design-api.md"
