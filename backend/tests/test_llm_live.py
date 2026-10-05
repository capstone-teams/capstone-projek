"""Real end-to-end test: these tests talk to an actual LLM provider.

Opt-in only, so the default suite stays offline and deterministic:

    LLM_LIVE_TEST=1 uv run pytest tests/test_llm_live.py -v -s

They need a reachable provider: either real cloud credentials in `.env`, or a
local OpenAI-compatible runtime such as Ollama (the runtime named in the
project charter):

    LLM_LIVE_TEST=1 \
    LLM_PROVIDER=openai \
    OPENAI_BASE_URL=http://localhost:11434/v1 \
    OPENAI_API_KEY=ollama \
    OPENAI_MODEL=qwen2.5:7b \
    uv run pytest tests/test_llm_live.py -v -s

A test skips itself when the selected provider has no credential configured, so
the file stays collectible in an environment without any keys.
"""

import os

import pytest

from src.services.llm import get_llm_service

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        os.getenv("LLM_LIVE_TEST") != "1",
        reason="opt-in live LLM test: set LLM_LIVE_TEST=1 and configure a provider",
    ),
]


def configured_service():
    service = get_llm_service()
    if not service.is_configured():
        pytest.skip(f"{service.provider_name} has no credential configured")
    return service


async def test_provider_really_returns_a_completion():
    service = configured_service()

    response = await service.check_connectivity()

    print(f"\n[{service.provider_name}/{service.model}] {response!r}")
    assert isinstance(response, str)
    assert response.strip(), "provider returned an empty completion"


async def test_provider_answers_an_indonesian_prompt():
    """Generated LMS content is Indonesian, so answering in Bahasa Indonesia is
    part of the real scenario (PRD AIR-008 model evaluation)."""
    service = configured_service()

    response = await service.generate("Jawab hanya dengan satu kata dalam Bahasa Indonesia: halo")

    print(f"\n[{service.provider_name}/{service.model}] {response!r}")
    assert response.strip()
