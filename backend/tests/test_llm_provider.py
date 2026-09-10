from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from src.services.llm import (
    GeminiProvider,
    LLMProviderError,
    OpenAIProvider,
    get_llm_provider,
)


def test_factory_returns_openai_provider():
    provider = get_llm_provider("openai")
    assert isinstance(provider, OpenAIProvider)


def test_factory_returns_gemini_provider():
    provider = get_llm_provider("gemini")
    assert isinstance(provider, GeminiProvider)


def test_factory_invalid_provider():
    with pytest.raises(LLMProviderError):
        get_llm_provider("invalid_provider")


@pytest.mark.asyncio
async def test_openai_generate_missing_key():
    provider = OpenAIProvider(api_key="")
    with pytest.raises(LLMProviderError, match="OpenAI API key is missing"):
        await provider.generate("Hello")


@pytest.mark.asyncio
async def test_openai_generate_success():
    provider = OpenAIProvider(api_key="mock_key", model="gpt-4o-mini")
    mock_data = {
        "choices": [
            {"message": {"content": "Hello from OpenAI!"}}
        ]
    }
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = mock_data
    mock_res.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_res
        result = await provider.generate("Say hello", system_prompt="Be helpful")
        assert result == "Hello from OpenAI!"


@pytest.mark.asyncio
async def test_gemini_generate_missing_key():
    provider = GeminiProvider(api_key="")
    with pytest.raises(LLMProviderError, match="Gemini API key is missing"):
        await provider.generate("Hello")


@pytest.mark.asyncio
async def test_gemini_generate_success():
    provider = GeminiProvider(api_key="mock_key", model="gemini-1.5-flash")
    mock_data = {
        "candidates": [
            {"content": {"parts": [{"text": "Hello from Gemini!"}]}}
        ]
    }
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = mock_data
    mock_res.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_res
        result = await provider.generate("Say hello")
        assert result == "Hello from Gemini!"
