from typing import Any, Optional

from src.services.llm.base import BaseLLMProvider
from src.services.llm.factory import get_llm_provider


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


def get_llm_service(provider_name: Optional[str] = None) -> LLMService:
    """Build an `LLMService` bound to the configured provider."""
    return LLMService(get_llm_provider(provider_name))
