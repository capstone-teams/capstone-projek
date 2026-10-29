from typing import Any, Dict, Optional

from src.config.settings import get_settings
from src.services.llm.base import (
    DEFAULT_TIMEOUT_SECONDS,
    PLACEHOLDER_API_KEY,
    BaseLLMProvider,
    LLMConfigurationError,
    LLMProviderError,
    LLMResponse,
    LLMUsage,
    post_json,
)

# Provisional default model. The final model is NOT decided yet: PRD AIR-008
# requires a model evaluation first, so this only keeps the provider usable out
# of the box and stays overridable through OPENAI_MODEL / LLM_MODEL.
DEFAULT_MODEL = "gpt-4o-mini"

# Official OpenAI API. Overridable through OPENAI_BASE_URL so the same provider
# can talk to any OpenAI-compatible endpoint, e.g. a local Ollama runtime
# (http://localhost:11434/v1) used for offline development and model evaluation.
DEFAULT_BASE_URL = "https://api.openai.com/v1"


class OpenAIProvider(BaseLLMProvider):
    provider_name = "openai"
    label = "OpenAI"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        config = get_settings()
        # The credential is private: callers (and agent code) never read it back.
        self._api_key = config.llm_api_key_for(self.provider_name) if api_key is None else api_key
        self.model = model or config.llm_model_for(self.provider_name) or DEFAULT_MODEL
        resolved_base_url = base_url if base_url is not None else config.OPENAI_BASE_URL
        self.api_url = f"{(resolved_base_url or DEFAULT_BASE_URL).rstrip('/')}/chat/completions"
        self.timeout = (
            timeout
            if timeout is not None
            else config.llm_timeout_for(self.provider_name)
        )

    def is_configured(self) -> bool:
        return bool(self._api_key) and self._api_key != PLACEHOLDER_API_KEY

    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        if not self.is_configured():
            raise LLMConfigurationError(f"{self.label} API key is missing")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": self.model, "messages": messages, **kwargs}

        data = await post_json(
            self.api_url,
            payload,
            headers,
            provider_name=self.provider_name,
            timeout=self.timeout,
        )
        content = self._extract_text(data)
        usage = self._extract_usage(data)
        model_name = data.get("model") or self.model
        return LLMResponse(content=content, usage=usage, model=model_name)

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any) -> str:
        response = await self.generate_response(prompt, system_prompt=system_prompt, **kwargs)
        return response.content

    @staticmethod
    def _extract_text(data: Dict[str, Any]) -> str:
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise LLMProviderError("OpenAI provider returned an unexpected response") from None

    @staticmethod
    def _extract_usage(data: Dict[str, Any]) -> LLMUsage:
        raw_usage = data.get("usage") or {}
        return LLMUsage(
            prompt_tokens=int(raw_usage.get("prompt_tokens") or 0),
            completion_tokens=int(raw_usage.get("completion_tokens") or 0),
            total_tokens=int(raw_usage.get("total_tokens") or 0),
        )
