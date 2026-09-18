from typing import Any, Dict, Optional

from src.config.settings import get_settings
from src.services.llm.base import (
    PLACEHOLDER_API_KEY,
    BaseLLMProvider,
    LLMConfigurationError,
    LLMProviderError,
    post_json,
)

# Provisional default model. The final model is NOT decided yet: PRD AIR-008
# requires a model evaluation first, so this only keeps the provider usable out
# of the box and stays overridable through GEMINI_MODEL / LLM_MODEL.
# Verified against the live API; older names (gemini-1.5-flash, gemini-2.5-flash)
# are retired for new keys and answer HTTP 404, so check availability before
# pinning a model here.
DEFAULT_MODEL = "gemini-3.6-flash"

API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider(BaseLLMProvider):
    provider_name = "gemini"
    label = "Gemini"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        config = get_settings()
        # The credential is private: callers (and agent code) never read it back.
        self._api_key = config.llm_api_key_for(self.provider_name) if api_key is None else api_key
        self.model = model or config.llm_model_for(self.provider_name) or DEFAULT_MODEL

    def is_configured(self) -> bool:
        return bool(self._api_key) and self._api_key != PLACEHOLDER_API_KEY

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any) -> str:
        if not self.is_configured():
            raise LLMConfigurationError(f"{self.label} API key is missing")

        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        payload: Dict[str, Any] = {"contents": contents, **kwargs}
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        # The key travels in a header, never in the URL: a query string would end
        # up in logs and in transport error messages.
        headers = {"x-goog-api-key": self._api_key, "Content-Type": "application/json"}
        url = f"{API_BASE_URL}/{self.model}:generateContent"

        data = await post_json(url, payload, headers, provider_name=self.provider_name)
        return self._extract_text(data)

    @staticmethod
    def _extract_text(data: Dict[str, Any]) -> str:
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError):
            block_reason = (data.get("promptFeedback") or {}).get("blockReason")
            if block_reason:
                raise LLMProviderError(f"Gemini provider blocked the request ({block_reason})") from None
            raise LLMProviderError("Gemini provider returned an unexpected response") from None
