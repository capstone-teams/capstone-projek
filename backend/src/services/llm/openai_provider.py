from typing import Any, Optional
import httpx

from src.config.settings import settings
from src.services.llm.base import BaseLLMProvider, LLMProviderError


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key if api_key is not None else settings.LLM_API_KEY
        self.model = model if model is not None else settings.LLM_MODEL or "gpt-4o-mini"
        self.api_url = "https://api.openai.com/v1/chat/completions"

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any) -> str:
        if not self.api_key or self.api_key in ("your_llm_api_key_here", ""):
            raise LLMProviderError("OpenAI API key is missing")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            **kwargs,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.api_url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(f"OpenAI provider error: {str(e)}") from e
