import asyncio
import logging
import random
from typing import Awaitable, Callable, TypeVar

from src.services.llm.base import (
    LLMConnectionError,
    LLMRateLimitError,
    LLMRetryExhaustedError,
    LLMTimeoutError,
)

T = TypeVar("T")
logger = logging.getLogger(__name__)

# Error provider yang bersifat sementara (transient) dan layak di-retry:
# 429 (rate limit), timeout, connection error, dan 5xx server error.
# Error 400, 401, 403 (LLMConfigurationError / LLMProviderError status 400) TIDAK di-retry.
RETRYABLE_EXCEPTIONS = (
    LLMRateLimitError,
    LLMTimeoutError,
    LLMConnectionError,
)


def calculate_backoff(
    attempt: int,
    base_factor: float = 2.0,
    min_wait: float = 0.5,
    max_wait: float = 10.0,
    jitter: bool = True,
) -> float:
    """Hitung backoff eksponensial dengan jitter opsional.

    Formula: min(max_wait, min_wait * (base_factor ** (attempt - 1))) + jitter
    """
    exponent = max(0, attempt - 1)
    delay = min(max_wait, min_wait * (base_factor ** exponent))
    if jitter:
        # Jitter acak berskala hingga 10% dari delay atau rentang 0.05s
        jitter_amount = random.uniform(0.0, max(0.05, 0.1 * delay))
        return delay + jitter_amount
    return delay


async def retry_with_backoff(
    func: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    min_wait: float = 0.5,
    max_wait: float = 10.0,
    sleep_fn: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> tuple[T, int]:
    """Menjalankan fungsi asynchronous dengan mekanisme retry dan exponential backoff.

    Hanya mengulang pada kesalahan provider sementara (429, timeout, koneksi/5xx).
    Error permanen (400, 401, 403) langsung di-raise tanpa retry.
    Log tidak pernah memuat string exception dari provider (str(exc)) demi keamanan.

    Mengembalikan tuple (hasil, total_percobaan).
    """
    for attempt in range(1, max_retries + 1):
        try:
            result = await func()
            return result, attempt
        except RETRYABLE_EXCEPTIONS as exc:
            if attempt >= max_retries:
                # Log kegagalan setelah seluruh retry habis tanpa mencetak str(exc)
                logger.error(
                    "Retry pemanggilan LLM habis setelah %d percobaan (tipe_error: %s)",
                    attempt,
                    type(exc).__name__,
                )
                raise LLMRetryExhaustedError(
                    f"Gagal terhubung ke layanan LLM setelah {attempt} kali percobaan. Silakan coba beberapa saat lagi."
                ) from None

            wait_time = calculate_backoff(
                attempt,
                base_factor=backoff_factor,
                min_wait=min_wait,
                max_wait=max_wait,
                jitter=True,
            )
            # Log percobaan yang gagal tanpa str(exc)
            logger.warning(
                "Percobaan ke-%d gagal karena %s. Menunggu %.2f detik sebelum mencoba kembali...",
                attempt,
                type(exc).__name__,
                wait_time,
            )
            await sleep_fn(wait_time)
        except Exception:
            # Error permanen atau non-provider error (misal 400, 401, 403, JSON error)
            # Langsung diteruskan tanpa retry
            raise

    raise LLMRetryExhaustedError(
        "Gagal terhubung ke layanan LLM setelah beberapa kali percobaan."
    )
