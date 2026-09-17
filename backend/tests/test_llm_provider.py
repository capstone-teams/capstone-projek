from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.services.llm import (
    BaseLLMProvider,
    GeminiProvider,
    LLMConfigurationError,
    LLMConnectionError,
    LLMProviderError,
    LLMTimeoutError,
    OpenAIProvider,
    available_providers,
    get_llm_provider,
)
from src.services.llm.base import PLACEHOLDER_API_KEY
from src.services.llm.gemini_provider import DEFAULT_MODEL as GEMINI_DEFAULT_MODEL


def mock_response(payload: dict) -> MagicMock:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = payload
    response.raise_for_status = lambda: None
    return response


def mock_status_error(status: int, body: dict | None = None) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://provider.example/v1/generate")
    response = httpx.Response(status, request=request, json=body or {})
    return httpx.HTTPStatusError(f"HTTP {status}", request=request, response=response)


def test_factory_returns_openai_provider():
    provider = get_llm_provider("openai")
    assert isinstance(provider, OpenAIProvider)


def test_factory_returns_gemini_provider():
    provider = get_llm_provider("gemini")
    assert isinstance(provider, GeminiProvider)


def test_factory_invalid_provider():
    with pytest.raises(LLMProviderError):
        get_llm_provider("invalid_provider")


def test_factory_accepts_known_aliases():
    assert isinstance(get_llm_provider("google"), GeminiProvider)
    assert isinstance(get_llm_provider("OpenAI"), OpenAIProvider)


def test_every_registered_provider_implements_the_same_interface():
    """Switching provider must stay a configuration concern for agent code."""
    assert available_providers() == ["gemini", "openai"]

    for provider_name in available_providers():
        provider = get_llm_provider(provider_name)
        assert isinstance(provider, BaseLLMProvider)
        assert provider.provider_name == provider_name
        assert provider.model


def test_placeholder_key_is_treated_as_not_configured():
    assert OpenAIProvider(api_key=PLACEHOLDER_API_KEY).is_configured() is False
    assert GeminiProvider(api_key=PLACEHOLDER_API_KEY).is_configured() is False


def test_provider_specific_credentials_are_used(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "openai-provider-key")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-provider-key")

    from src.config.settings import get_settings

    get_settings.cache_clear()
    try:
        assert OpenAIProvider().is_configured() is True
        assert GeminiProvider().is_configured() is True
        assert OpenAIProvider(api_key="").is_configured() is False
    finally:
        get_settings.cache_clear()


def test_provider_uses_its_provisional_model_when_none_is_configured(monkeypatch):
    """The model is not final: until the AIR-008 evaluation, each provider keeps
    a provisional default that configuration can replace at any time."""
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("GEMINI_MODEL", "")

    from src.config.settings import get_settings

    get_settings.cache_clear()
    try:
        assert GeminiProvider().model == GEMINI_DEFAULT_MODEL
    finally:
        get_settings.cache_clear()


def test_configured_model_replaces_the_provisional_default(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-candidate-model")

    from src.config.settings import get_settings

    get_settings.cache_clear()
    try:
        assert GeminiProvider().model == "gemini-candidate-model"
    finally:
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_openai_generate_missing_key():
    provider = OpenAIProvider(api_key="")
    with pytest.raises(LLMProviderError, match="OpenAI API key is missing"):
        await provider.generate("Hello")


@pytest.mark.asyncio
async def test_openai_generate_success():
    provider = OpenAIProvider(api_key="mock_key", model="gpt-4o-mini")
    mock_data = {"choices": [{"message": {"content": "Hello from OpenAI!"}}]}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response(mock_data)
        result = await provider.generate("Say hello", system_prompt="Be helpful")
        assert result == "Hello from OpenAI!"


@pytest.mark.asyncio
async def test_openai_request_uses_the_configured_credential_and_model():
    provider = OpenAIProvider(api_key="openai-key-123", model="openai-candidate-model")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response({"choices": [{"message": {"content": "hi"}}]})
        await provider.generate("Say hello", system_prompt="Be helpful")

    request = mock_post.await_args
    assert request.args[0] == "https://api.openai.com/v1/chat/completions"
    assert request.kwargs["headers"]["Authorization"] == "Bearer openai-key-123"
    assert request.kwargs["json"]["model"] == "openai-candidate-model"
    assert request.kwargs["json"]["messages"] == [
        {"role": "system", "content": "Be helpful"},
        {"role": "user", "content": "Say hello"},
    ]


@pytest.mark.asyncio
async def test_gemini_generate_missing_key():
    provider = GeminiProvider(api_key="")
    with pytest.raises(LLMProviderError, match="Gemini API key is missing"):
        await provider.generate("Hello")


@pytest.mark.asyncio
async def test_gemini_generate_success():
    provider = GeminiProvider(api_key="mock_key", model="gemini-1.5-flash")
    mock_data = {"candidates": [{"content": {"parts": [{"text": "Hello from Gemini!"}]}}]}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response(mock_data)
        result = await provider.generate("Say hello")
        assert result == "Hello from Gemini!"


@pytest.mark.asyncio
async def test_gemini_request_keeps_the_credential_out_of_the_url():
    provider = GeminiProvider(api_key="gemini-key-456", model="gemini-candidate-model")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response(
            {"candidates": [{"content": {"parts": [{"text": "hi"}]}}]}
        )
        await provider.generate("Say hello", system_prompt="Be helpful")

    request = mock_post.await_args
    assert request.args[0].endswith("/models/gemini-candidate-model:generateContent")
    assert "gemini-key-456" not in request.args[0]
    assert request.kwargs["headers"]["x-goog-api-key"] == "gemini-key-456"
    assert request.kwargs["json"]["systemInstruction"] == {"parts": [{"text": "Be helpful"}]}


@pytest.mark.asyncio
async def test_check_connectivity_returns_the_model_reply():
    provider = OpenAIProvider(api_key="mock_key")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response({"choices": [{"message": {"content": "pong"}}]})
        assert await provider.check_connectivity() == "pong"


@pytest.mark.asyncio
async def test_check_connectivity_fails_on_an_unconfigured_provider():
    with pytest.raises(LLMConfigurationError):
        await OpenAIProvider(api_key="").check_connectivity()


@pytest.mark.asyncio
async def test_authentication_failure_maps_to_a_configuration_error():
    provider = OpenAIProvider(api_key="mock_key")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = mock_status_error(401)
        with pytest.raises(LLMConfigurationError):
            await provider.generate("Hello")


@pytest.mark.asyncio
async def test_server_failure_maps_to_a_connection_error():
    provider = OpenAIProvider(api_key="mock_key")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = mock_status_error(503)
        with pytest.raises(LLMConnectionError):
            await provider.generate("Hello")


@pytest.mark.asyncio
async def test_timeout_maps_to_a_timeout_error():
    provider = GeminiProvider(api_key="mock_key")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ReadTimeout("too slow", request=httpx.Request("POST", "https://provider.example"))
        with pytest.raises(LLMTimeoutError):
            await provider.generate("Hello")


@pytest.mark.asyncio
async def test_transport_failure_maps_to_a_connection_error():
    provider = GeminiProvider(api_key="mock_key")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ConnectError("dns", request=httpx.Request("POST", "https://provider.example"))
        with pytest.raises(LLMConnectionError):
            await provider.generate("Hello")


@pytest.mark.asyncio
async def test_unexpected_payload_maps_to_a_provider_error():
    provider = OpenAIProvider(api_key="mock_key")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response({"unexpected": "payload"})
        with pytest.raises(LLMProviderError, match="unexpected response"):
            await provider.generate("Hello")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "provider,api_key",
    [
        (OpenAIProvider, "openai-secret-key"),
        (GeminiProvider, "gemini-secret-key"),
    ],
    ids=["openai", "gemini"],
)
async def test_provider_errors_never_leak_the_credential(provider, api_key):
    client = provider(api_key=api_key)
    leaked_body = {"error": {"message": f"Incorrect API key provided: {api_key}"}}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = mock_status_error(401, leaked_body)
        with pytest.raises(LLMProviderError) as excinfo:
            await client.generate("Hello")

    assert api_key not in str(excinfo.value)
