"""Real end-to-end check against an actual LLM.

Unlike the rest of the suite this script performs real network calls, so it is
opt-in and never runs as part of `pytest`. Use it to confirm the provider
configuration actually produces a model response (not just that a connection
was accepted).

Usage (from the `backend/` directory):

    uv run python -m scripts.check_llm_connectivity
    uv run python -m scripts.check_llm_connectivity gemini

Real scenario with a local Ollama runtime (no cloud credential needed):

    LLM_PROVIDER=openai \
    OPENAI_BASE_URL=http://localhost:11434/v1 \
    OPENAI_API_KEY=ollama \
    OPENAI_MODEL=qwen2.5:7b \
    uv run python -m scripts.check_llm_connectivity

Real scenario with the cloud providers: fill `LLM_API_KEY` (or the
provider-specific key) in `backend/.env` and run the command above.
"""

import asyncio
import sys

from src.services.llm import LLMProviderError, get_llm_service

MAX_RESPONSE_PREVIEW = 500


async def main(provider_name: str | None = None) -> int:
    service = get_llm_service(provider_name)
    print(f"provider : {service.provider_name}")
    print(f"model    : {service.model}")

    if not service.is_configured():
        print("status   : NOT CONFIGURED - set the provider credential in your .env first")
        return 1

    try:
        response = await service.check_connectivity()
    except LLMProviderError as exc:
        print(f"status   : FAILED - {exc}")
        return 1

    preview = response.strip().replace("\n", " ")
    if len(preview) > MAX_RESPONSE_PREVIEW:
        preview = preview[:MAX_RESPONSE_PREVIEW] + "..."
    print("status   : OK - model replied")
    print(f"response : {preview!r}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else None)))
