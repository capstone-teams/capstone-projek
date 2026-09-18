from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from src.main import app
from src.middlewares.error_handlers import register_exception_handlers
from src.services.llm import (
    LLMConfigurationError,
    LLMConnectionError,
    LLMProviderError,
    LLMTimeoutError,
)

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Moodle Agentic AI Backend"}


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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
