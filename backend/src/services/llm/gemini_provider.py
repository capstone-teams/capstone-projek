from typing import Any, Optional
import httpx

from src.config.settings import settings
from src.services.llm.base import BaseLLMProvider, LLMProviderError


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key if api_key is not None else settings.LLM_API_KEY
        self.model = model if model is not None else settings.LLM_MODEL or "gemini-1.5-flash"

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any) -> str:
        if not self.api_key or self.api_key in ("your_llm_api_key_here", ""):
            raise LLMProviderError("Gemini API key is missing")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"System Instruction: {system_prompt}"}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {"contents": contents, **kwargs}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(f"Gemini provider error: {str(e)}") from e
