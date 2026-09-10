from abc import ABC, abstractmethod
from typing import Any, Optional


class LLMProviderError(Exception):
    pass


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any) -> str:
        pass
