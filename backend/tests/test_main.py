import ast
from pathlib import Path

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from src.config.settings import settings
from src.main import app, create_app
from src.middlewares.error_handlers import register_exception_handlers
from src.routes import API_V1_PREFIX, api_router
from src.services.llm import (
    LLMConfigurationError,
    LLMConnectionError,
    LLMProviderError,
    LLMTimeoutError,
)

client = TestClient(app)

MAIN_PATH = Path(__file__).resolve().parent.parent / "src" / "main.py"

HTTP_METHOD_DECORATORS = {
    "get",
    "post",
    "put",
    "patch",
    "delete",
    "head",
    "options",
    "trace",
}

FORBIDDEN_IMPORTS = {"sqlalchemy", "src.models", "src.services"}


def parse_main_module() -> ast.Module:
    return ast.parse(MAIN_PATH.read_text(encoding="utf-8"))


def collect_route_decorators(tree: ast.Module) -> list[str]:
    """Ambil nama HTTP method dari decorator route pada seluruh function."""
    methods = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            target = decorator.func if isinstance(decorator, ast.Call) else decorator
            if isinstance(target, ast.Attribute) and target.attr in HTTP_METHOD_DECORATORS:
                methods.append(target.attr)
    return methods


def collect_imported_modules(tree: ast.Module) -> set[str]:
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Moodle Agentic AI Backend"}


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_app_returns_new_instance():
    assert isinstance(create_app(), FastAPI)
    assert create_app() is not app


def test_app_metadata_comes_from_settings():
    assert app.title == settings.APP_NAME
    assert app.debug == settings.DEBUG


def test_health_endpoints_are_exposed():
    assert {"/", "/health"}.issubset(app.openapi()["paths"])


def test_api_v1_prefix_follows_api_specification():
    assert API_V1_PREFIX == "/api/v1"
    assert api_router.prefix == API_V1_PREFIX


def test_feature_router_is_registered_through_the_aggregator():
    probe_router = APIRouter()

    @probe_router.get("/probe")
    async def probe_endpoint() -> dict[str, bool]:
        return {"probe": True}

    api_router.include_router(probe_router)
    try:
        with TestClient(create_app()) as probe_client:
            response = probe_client.get(f"{API_V1_PREFIX}/probe")
    finally:
        api_router.routes.pop()

    assert response.status_code == 200
    assert response.json() == {"probe": True}


def test_startup_runs_without_business_logic():
    with TestClient(app) as lifespan_client:
        assert lifespan_client.get("/health").status_code == 200


def test_entry_point_defines_no_individual_route():
    route_methods = collect_route_decorators(parse_main_module())
    assert route_methods == [], f"route individual tidak boleh ada di main.py: {route_methods}"


def test_entry_point_does_not_import_data_layer():
    imported = collect_imported_modules(parse_main_module())
    assert not (FORBIDDEN_IMPORTS & imported)


def test_llm_provider_errors_are_handled_by_the_application():
    assert LLMProviderError in app.exception_handlers


@pytest.mark.parametrize(
    "error_class,expected_status,expected_code",
    [
        (LLMConfigurationError, 500, "INTERNAL_ERROR"),
        (LLMConnectionError, 502, "LLM_GENERATION_FAILED"),
        (LLMTimeoutError, 504, "LLM_GENERATION_FAILED"),
        (LLMProviderError, 502, "LLM_GENERATION_FAILED"),
    ],
    ids=["not-configured", "unreachable", "timeout", "provider-failure"],
)
def test_llm_errors_return_the_standard_error_format(error_class, expected_status, expected_code):
    error = error_class("provider detail that must stay server-side")

    probe = FastAPI()
    register_exception_handlers(probe)

    @probe.get("/boom")
    async def boom():
        raise error

    response = TestClient(probe, raise_server_exceptions=False).get("/boom")

    assert response.status_code == expected_status
    assert response.json() == {
        "error": {
            "code": expected_code,
            "message": error.public_message,
            "details": [],
        }
    }


def test_llm_error_response_does_not_expose_provider_details():
    error = LLMConfigurationError("Gemini API key is missing")

    probe = FastAPI()
    register_exception_handlers(probe)

    @probe.get("/boom")
    async def boom():
        raise error

    response = TestClient(probe, raise_server_exceptions=False).get("/boom")

    assert "Gemini API key is missing" not in response.text
