"""Test kontrak API yang diterbitkan pada OpenAPI (BE-06.4 & BE-11.3).

Kontrak Sprint 2 harus dapat dipakai frontend sebagai dasar mock, jadi yang
diuji di sini adalah janji dokumennya:

1. Setiap endpoint kontrak muncul pada ``openapi.json`` beserta contoh response.
2. Nilai ``role`` yang ditampilkan adalah enum kanonik backend.
3. Bentuk hasil analisis memakai RPS Structured Data (BE-05.3), bukan schema
   duplikat.
4. Format event workflow tersedia di OpenAPI untuk client WebSocket.
5. Endpoint yang sudah diimplementasikan memakai otorisasinya sendiri.
6. ``design-api.md`` menyebut setiap endpoint kontrak, sehingga dokumen dan
   OpenAPI tidak dapat menyimpang tanpa terlihat.

Sejak BE-11.3 tidak ada lagi stub ``501``: endpoint workflow yang dulu hanya
kontrak sudah diimplementasikan pada :mod:`src.routes.workflows`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.services.user.enums import UserRole

client = TestClient(app)

DESIGN_API = Path(__file__).resolve().parent.parent.parent / "docs" / "02. design" / "design-api.md"

# Endpoint kontrak (path, method) beserta schema response yang dijanjikan.
CONTRACT_ENDPOINTS = {
    ("/api/v1/rps", "get"): "RPSListResponse",
    ("/api/v1/rps/{rps_id}/analysis", "get"): "RPSAnalysisResponse",
    ("/api/v1/rps/{rps_id}/reanalyze", "post"): "RPSReanalyzeResponse",
    ("/api/v1/workflows", "get"): "WorkflowListResponse",
    ("/api/v1/workflows/{workflow_id}", "get"): "WorkflowResponse",
    ("/api/v1/workflows/{workflow_id}/events", "get"): "WorkflowEventListResponse",
    ("/api/v1/workflows/{workflow_id}/moodle-target", "put"): "WorkflowResponse",
}

RPS_ID = "kP3nQ7vRtYx2bM8sLdWfZa"
WORKFLOW_ID = "q7RtYx2bM8sLdWfZaKp3nQ"


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

    assert status == [
        "UPLOADED",
        "PROCESSING",
        "PROCESSED",
        "ANALYZING",
        "ANALYZED",
        "FAILED",
    ]
    assert all(value == value.upper() for value in status)


def test_only_the_lifecycle_workflow_statuses_are_published(openapi):
    """Status tahap internal tidak bocor ke kontrak (design-api §16/§20)."""
    status = openapi["components"]["schemas"]["WorkflowStatus"]["enum"]

    assert status == ["QUEUED", "RUNNING", "COMPLETED", "FAILED"]
    assert "ANALYZING_RPS" not in status


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


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/api/v1/rps"),
        ("get", f"/api/v1/rps/{RPS_ID}"),
        ("post", f"/api/v1/rps/{RPS_ID}/process"),
        ("get", "/api/v1/instructors/me/setup"),
        ("put", "/api/v1/instructors/me/setup"),
        ("get", "/api/v1/workflows"),
        ("get", f"/api/v1/workflows/{WORKFLOW_ID}"),
        ("get", f"/api/v1/workflows/{WORKFLOW_ID}/events"),
        ("put", f"/api/v1/workflows/{WORKFLOW_ID}/moodle-target"),
    ],
)
def test_implemented_endpoints_require_authentication(method, path):
    """Endpoint yang sudah diimplementasikan memakai otorisasinya sendiri."""
    response = getattr(client, method)(path)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_the_design_document_mentions_every_contracted_endpoint():
    """Dokumen dan OpenAPI menyebut endpoint yang sama."""
    document = DESIGN_API.read_text(encoding="utf-8")

    for path, _ in CONTRACT_ENDPOINTS:
        assert path in document, f"{path} belum didokumentasikan pada design-api.md"
