import asyncio
from dataclasses import dataclass
import json
import logging
import time
from typing import Any, Awaitable, Callable, Optional

from src.config.settings import get_settings
from src.prompts.loader import render_prompt
from src.services.llm.base import (
    BaseLLMProvider,
    LLMInvalidOutputError,
    LLMResponse,
)
from src.services.llm.factory import get_llm_provider
from src.services.llm.retry import retry_with_backoff

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PromptExecutionMetadata:
    prompt_name: str
    prompt_version: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    duration_ms: float
    attempts: int


@dataclass(frozen=True)
class PromptExecutionResult:
    data: dict[str, Any]
    raw_content: str
    metadata: PromptExecutionMetadata

    @property
    def parsed_content(self) -> dict[str, Any]:
        return self.data


class LLMService:
    """Service-layer entry point for LLM access.

    Agent and controller code must call the LLM through this class instead of
    talking to a provider directly or reading credentials from settings, so
    that provider selection stays a configuration concern and credentials stay
    inside the service layer.
    """

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        self._provider = provider if provider is not None else get_llm_provider()

    @property
    def provider_name(self) -> str:
        return self._provider.provider_name

    @property
    def model(self) -> str:
        return self._provider.model

    def is_configured(self) -> bool:
        return self._provider.is_configured()

    async def check_connectivity(self) -> str:
        return await self._provider.check_connectivity()

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any) -> str:
        return await self._provider.generate(prompt, system_prompt=system_prompt, **kwargs)

    async def generate_response(
        self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any
    ) -> LLMResponse:
        return await self._provider.generate_response(prompt, system_prompt=system_prompt, **kwargs)

    async def execute_prompt(
        self,
        prompt_name: str,
        version: str,
        variables: dict[str, Any],
        output_schema: dict[str, Any],
        system_prompt: Optional[str] = None,
        max_retries: Optional[int] = None,
        backoff_factor: Optional[float] = None,
        min_wait: Optional[float] = None,
        max_wait: Optional[float] = None,
        sleep_fn: Optional[Callable[[float], Awaitable[None]]] = None,
        **kwargs: Any,
    ) -> PromptExecutionResult:
        """Menjalankan prompt ke provider LLM dengan structured output dan retry backoff.

        Alur:
        1. Render prompt menggunakan template loader.
        2. Format structured output JSON Schema.
        3. Panggil provider LLM dengan retry backoff pada error sementara.
        4. Parsing output JSON tanpa retry bila output tidak valid.
        5. Catat log ringkas aman (hanya metadata).
        """
        settings = get_settings()

        # 1. Siapkan variabel render dan output_schema
        render_vars = dict(variables)
        if "output_schema" not in render_vars or render_vars["output_schema"] is None:
            render_vars["output_schema"] = json.dumps(output_schema, indent=2, ensure_ascii=False)
        elif isinstance(render_vars["output_schema"], (dict, list)):
            render_vars["output_schema"] = json.dumps(render_vars["output_schema"], indent=2, ensure_ascii=False)

        prompt_text = render_prompt(prompt_name, version, render_vars)

        # 2. Format structured output payload untuk OpenAI
        call_kwargs = dict(kwargs)
        if "response_format" not in call_kwargs and output_schema:
            if isinstance(output_schema, dict) and output_schema.get("type") in ("json_object", "json_schema"):
                call_kwargs["response_format"] = output_schema
            else:
                call_kwargs["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": f"{prompt_name}_{version}_response",
                        "strict": True,
                        "schema": output_schema,
                    },
                }

        effective_max_retries = max_retries if max_retries is not None else settings.llm_max_retries
        effective_backoff_factor = (
            backoff_factor if backoff_factor is not None else settings.llm_retry_backoff_factor
        )
        effective_min_wait = min_wait if min_wait is not None else settings.llm_retry_min_wait
        effective_max_wait = max_wait if max_wait is not None else settings.llm_retry_max_wait

        async def _call_provider() -> LLMResponse:
            return await self._provider.generate_response(
                prompt_text,
                system_prompt=system_prompt,
                **call_kwargs,
            )

        start_time = time.perf_counter()
        response, attempts = await retry_with_backoff(
            _call_provider,
            max_retries=effective_max_retries,
            backoff_factor=effective_backoff_factor,
            min_wait=effective_min_wait,
            max_wait=effective_max_wait,
            sleep_fn=sleep_fn or asyncio.sleep,
        )
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        # 3. Parsing output JSON - jangan di-retry jika JSON salah (tanggung jawab BE-09.2)
        try:
            parsed_data = json.loads(response.content)
            if not isinstance(parsed_data, dict):
                parsed_data = {"data": parsed_data}
        except (json.JSONDecodeError, TypeError, ValueError) as err:
            logger.error(
                "Gagal melakukan parse JSON dari output LLM (prompt: %s/%s, model: %s)",
                prompt_name,
                version,
                response.model or self.model,
            )
            raise LLMInvalidOutputError("Format output dari layanan LLM bukan JSON yang valid.") from err

        # 4. Logging yang aman: hanya nama/versi prompt, model, token, durasi, percobaan
        # Dilarang mencetak API key, prompt, variabel, raw_content, atau str(exc)
        logger.info(
            "Eksekusi prompt '%s/%s' berhasil (model: %s, tokens: %d in / %d out / %d total, durasi: %.2f ms, percobaan: %d)",
            prompt_name,
            version,
            response.model or self.model,
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
            response.usage.total_tokens,
            duration_ms,
            attempts,
        )

        metadata = PromptExecutionMetadata(
            prompt_name=prompt_name,
            prompt_version=version,
            model=response.model or self.model,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            duration_ms=round(duration_ms, 2),
            attempts=attempts,
        )

        return PromptExecutionResult(
            data=parsed_data,
            raw_content=response.content,
            metadata=metadata,
        )


def get_llm_service(provider_name: Optional[str] = None) -> LLMService:
    """Build an `LLMService` bound to the configured provider."""
    return LLMService(get_llm_provider(provider_name))

