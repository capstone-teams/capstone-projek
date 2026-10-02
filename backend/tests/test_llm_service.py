from pathlib import Path
from typing import Any, Optional

import asyncio
import re

import pytest
from fastapi.testclient import TestClient

from src.config.settings import Settings, get_settings
from src.main import app
from src.services.llm import (
    BaseLLMProvider,
    GeminiProvider,
    LLMService,
    OpenAIProvider,
    get_llm_service,
)
from src.services.llm.base import CONNECTIVITY_PROMPT

ENV_EXAMPLE_PATH = Path(__file__).parent.parent / ".env.example"

# Credential-ish setting names that must never reach the frontend.
CREDENTIAL_SUFFIXES = ("API_KEY", "SECRET_KEY", "TOKEN", "PASSWORD")

# Modules allowed to read credentials: the settings definition itself, the
# provider implementations that turn them into provider requests, and the
# authentication token signer, which legitimately owns the JWT secret. Agent,
# tool and controller code must go through the service layer instead.
CREDENTIAL_OWNERS = {
    "src/config/settings.py",
    "src/services/llm/openai_provider.py",
    "src/services/llm/gemini_provider.py",
    "src/services/auth/tokens.py",
}

# Credential *reads* to look for in the modules above: attribute access such as
# `settings.LLM_API_KEY` and environment lookups such as
# `os.environ["OPENAI_API_KEY"]`.
CREDENTIAL_ACCESS_PATTERNS = (
    re.compile(r"\.\s*[A-Za-z0-9_]*(?:API_KEY|SECRET_KEY|TOKEN|PASSWORD)\b"),
    re.compile(
        r"(?:environ\[|environ\.get\(|getenv\()\s*[\"'][A-Za-z0-9_]*(?:API_KEY|SECRET_KEY|TOKEN|PASSWORD)"
    ),
)


class FakeProvider(BaseLLMProvider):
    """Minimal provider used to observe what the service layer passes through."""

    provider_name = "fake"
    model = "fake-model"

    def __init__(self, configured: bool = True):
        self._configured = configured
        self.calls = []

    def is_configured(self) -> bool:
        return self._configured

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any) -> str:
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt, "kwargs": kwargs})
        return "fake-response"


@pytest.mark.asyncio
async def test_service_layer_passes_prompt_and_system_prompt():
    provider = FakeProvider()
    service = LLMService(provider)

    result = await service.generate("Hello", system_prompt="Be helpful", temperature=0.2)

    assert result == "fake-response"
    assert provider.calls == [
        {"prompt": "Hello", "system_prompt": "Be helpful", "kwargs": {"temperature": 0.2}}
    ]


def test_service_layer_runs_the_connectivity_check_through_the_provider():
    provider = FakeProvider()

    assert asyncio.run(LLMService(provider).check_connectivity()) == "fake-response"
    assert provider.calls == [{"prompt": CONNECTIVITY_PROMPT, "system_prompt": None, "kwargs": {}}]


def test_service_layer_reports_provider_metadata():
    service = LLMService(FakeProvider())

    assert service.provider_name == "fake"
    assert service.model == "fake-model"
    assert service.is_configured() is True


def test_service_layer_detects_unconfigured_provider():
    assert LLMService(FakeProvider(configured=False)).is_configured() is False


def test_service_layer_hides_the_credential():
    service = LLMService(OpenAIProvider(api_key="sk-secret-value"))

    public_attributes = {name: getattr(service, name) for name in dir(service) if not name.startswith("_")}

    assert "sk-secret-value" not in repr(public_attributes)
    assert not hasattr(service, "api_key")


def test_provider_selection_is_driven_by_configuration(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    get_settings.cache_clear()
    try:
        assert get_llm_service().provider_name == "gemini"
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        get_settings.cache_clear()
        assert get_llm_service().provider_name == "openai"
    finally:
        get_settings.cache_clear()


def test_service_layer_exposes_the_same_interface_for_every_provider():
    for provider_name in ("openai", "gemini"):
        service = get_llm_service(provider_name)
        assert isinstance(service._provider, BaseLLMProvider)
        assert service.provider_name == provider_name


def test_provider_specific_credential_takes_precedence():
    settings = Settings(
        _env_file=str(ENV_EXAMPLE_PATH),
        LLM_API_KEY="shared-key",
        OPENAI_API_KEY="openai-key",
        GEMINI_API_KEY="gemini-key",
    )

    assert settings.llm_api_key_for("openai") == "openai-key"
    assert settings.llm_api_key_for("gemini") == "gemini-key"


def test_credential_falls_back_to_the_shared_key_for_the_active_provider():
    settings = Settings(
        _env_file=str(ENV_EXAMPLE_PATH),
        LLM_PROVIDER="openai",
        LLM_API_KEY="shared-key",
        OPENAI_API_KEY="",
        GEMINI_API_KEY="",
    )

    assert settings.llm_api_key_for("openai") == "shared-key"


def test_shared_credential_is_never_reused_for_the_other_provider():
    settings = Settings(
        _env_file=str(ENV_EXAMPLE_PATH),
        LLM_PROVIDER="openai",
        LLM_API_KEY="sk-openai-shared-key",
        OPENAI_API_KEY="",
        GEMINI_API_KEY="",
    )

    assert settings.llm_api_key_for("gemini") == ""


def test_model_is_configurable_per_provider():
    settings = Settings(
        _env_file=str(ENV_EXAMPLE_PATH),
        LLM_MODEL="shared-model",
        OPENAI_MODEL="openai-candidate-model",
        GEMINI_MODEL="gemini-candidate-model",
    )

    assert settings.llm_model_for("openai") == "openai-candidate-model"
    assert settings.llm_model_for("gemini") == "gemini-candidate-model"


def test_model_falls_back_to_the_shared_model_for_the_active_provider():
    settings = Settings(
        _env_file=str(ENV_EXAMPLE_PATH),
        LLM_PROVIDER="gemini",
        LLM_MODEL="gemini-model-under-evaluation",
        OPENAI_MODEL="",
        GEMINI_MODEL="",
    )

    assert settings.llm_model_for("gemini") == "gemini-model-under-evaluation"


def test_shared_model_is_never_reused_for_the_other_provider():
    settings = Settings(
        _env_file=str(ENV_EXAMPLE_PATH),
        LLM_PROVIDER="openai",
        LLM_MODEL="gpt-4o-mini",
        OPENAI_MODEL="",
        GEMINI_MODEL="",
    )

    assert settings.llm_model_for("gemini") == ""


def test_no_module_outside_the_provider_layer_reads_credentials():
    """AC: agent code must not reach LLM credentials directly."""
    src_dir = Path(__file__).parent.parent / "src"
    offenders = {}

    for path in src_dir.rglob("*.py"):
        module_path = path.relative_to(src_dir.parent).as_posix()
        if module_path in CREDENTIAL_OWNERS:
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if any(pattern.search(line) for pattern in CREDENTIAL_ACCESS_PATTERNS):
                offenders.setdefault(module_path, []).append(line_number)

    assert offenders == {}


def test_api_responses_never_expose_credentials():
    settings = get_settings()
    secrets = [
        str(getattr(settings, name))
        for name in Settings.model_fields
        if name.endswith(CREDENTIAL_SUFFIXES)
    ]
    secrets = [secret for secret in secrets if secret]

    client = TestClient(app)
    bodies = [client.get("/").text, client.get("/health").text, client.get("/openapi.json").text]

    for body in bodies:
        assert "api_key" not in body.lower()
        for secret in secrets:
            assert secret not in body
