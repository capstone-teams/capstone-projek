from abc import ABC, abstractmethod
from typing import Any, Optional

import httpx

# Timeout for a single provider HTTP call, in seconds.
DEFAULT_TIMEOUT_SECONDS = 30.0

# Value shipped in .env.example. Treated as "not configured" so an unfilled
# template never reaches a provider with a bogus credential.
PLACEHOLDER_API_KEY = "your_llm_api_key_here"

# Prompt used by `check_connectivity()`: cheap, and its answer is easy to eyeball.
CONNECTIVITY_PROMPT = "Reply with the single word: pong"


class LLMProviderError(Exception):
    """Base error for LLM provider failures.

    Carries the public contract used by the API layer: `error_code` follows the
    API error format (design-api.md) and `status_code` maps the failure to an
    HTTP status. `public_message` is safe to return to a client; the exception
    message itself is for server-side logging only and never contains
    credentials.
    """

    error_code = "LLM_GENERATION_FAILED"
    status_code = 502
    public_message = "LLM provider request failed."


class LLMConfigurationError(LLMProviderError):
    """The provider is missing or has invalid credentials."""

    error_code = "INTERNAL_ERROR"
    status_code = 500
    public_message = "LLM provider is not configured."


class LLMConnectionError(LLMProviderError):
    """The provider could not be reached or is failing on its side."""

    public_message = "LLM provider is unreachable."


class LLMTimeoutError(LLMConnectionError):
    """The provider did not answer within the configured timeout."""

    status_code = 504
    public_message = "LLM provider request timed out."


class BaseLLMProvider(ABC):
    """Common interface every LLM provider must implement.

    Agent code depends on this interface (through the service layer) so that
    switching between OpenAI and Gemini only requires a configuration change.
    """

    provider_name: str = "unknown"
    model: str = ""

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any) -> str:
        """Generate a completion for `prompt` and return the raw text."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Whether a usable credential is available for this provider."""

    async def check_connectivity(self) -> str:
        """Basic connectivity test: one real round trip to the provider.

        Returns the provider's actual reply, so a caller can confirm the model
        really answered instead of only seeing that a connection was accepted.
        Raises an `LLMProviderError` subclass when the provider is unreachable
        or not configured.
        """
        return await self.generate(CONNECTIVITY_PROMPT)


def _status_error(provider_name: str, exc: httpx.HTTPStatusError) -> LLMProviderError:
    """Map an HTTP error status to a typed provider error.

    Only the status code is kept: upstream response bodies and request URLs can
    echo a credential back, so they are never propagated.
    """
    status = exc.response.status_code
    if status in (401, 403):
        return LLMConfigurationError(f"{provider_name} provider rejected the credential (HTTP {status})")
    if status >= 500:
        return LLMConnectionError(f"{provider_name} provider request failed (HTTP {status})")
    return LLMProviderError(f"{provider_name} provider request failed (HTTP {status})")


async def post_json(
    url: str,
    payload: dict,
    headers: Optional[dict] = None,
    *,
    provider_name: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    """POST a JSON payload to a provider and normalize transport failures.

    Every raised error is typeless about credentials: the provider URL (which
    may carry an API key) and the upstream response body are deliberately left
    out of the message.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers or {})
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        raise LLMTimeoutError(f"{provider_name} provider timed out") from None
    except httpx.HTTPStatusError as exc:
        raise _status_error(provider_name, exc) from None
    except httpx.HTTPError as exc:
        raise LLMConnectionError(f"{provider_name} provider is unreachable ({type(exc).__name__})") from None
    except ValueError:
        raise LLMProviderError(f"{provider_name} provider returned an invalid JSON response") from None
