from typing import Dict, Optional, Type

from src.config.settings import LLM_PROVIDER_ALIASES, get_settings
from src.services.llm.base import BaseLLMProvider, LLMProviderError
from src.services.llm.gemini_provider import GeminiProvider
from src.services.llm.openai_provider import OpenAIProvider

# Registry of supported providers. Adding a provider means adding one entry
# here; agent logic keeps depending on BaseLLMProvider only.
PROVIDER_REGISTRY: Dict[str, Type[BaseLLMProvider]] = {
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
}


def available_providers() -> list:
    return sorted(PROVIDER_REGISTRY)


def normalize_provider_name(provider_name: str) -> str:
    """Lowercase a provider name and resolve its known aliases."""
    name = (provider_name or "").strip().lower()
    return LLM_PROVIDER_ALIASES.get(name, name)


def get_llm_provider(provider_name: Optional[str] = None) -> BaseLLMProvider:
    """Build the configured provider (or the one named explicitly)."""
    name = normalize_provider_name(provider_name) if provider_name else get_settings().llm_provider
    provider_class = PROVIDER_REGISTRY.get(name)
    if provider_class is None:
        raise LLMProviderError(
            f"Unsupported LLM provider: '{name}'. Available providers: {', '.join(available_providers())}"
        )
    return provider_class()
