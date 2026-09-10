from typing import Optional

from src.config.settings import settings
from src.services.llm.base import BaseLLMProvider, LLMProviderError
from src.services.llm.gemini_provider import GeminiProvider
from src.services.llm.openai_provider import OpenAIProvider


def get_llm_provider(provider_name: Optional[str] = None) -> BaseLLMProvider:
    name = (provider_name or settings.LLM_PROVIDER).lower()
    if name == "openai":
        return OpenAIProvider()
    elif name in ("gemini", "google"):
        return GeminiProvider()
    else:
        raise LLMProviderError(f"Unsupported LLM provider: '{name}'")
