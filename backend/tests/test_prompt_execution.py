import asyncio
import logging
from typing import Any, List, Optional

import pytest

from src.prompts.loader import PromptRenderError
from src.services.llm import (
    BaseLLMProvider,
    LLMConfigurationError,
    LLMConnectionError,
    LLMInvalidOutputError,
    LLMProviderError,
    LLMRateLimitError,
    LLMResponse,
    LLMRetryExhaustedError,
    LLMService,
    LLMTimeoutError,
    LLMUsage,
    calculate_backoff,
)

SAMPLE_VARIABLES = {
    "rps_yaml": "mata_kuliah:\n  kode: IF101\n  nama: Algoritma",
    "instructor_context_yaml": "nama: Dr. Budi\nkeahlian: Basis Data",
    "additional_prompt": "Gunakan contoh nyata.",
    "task_instruction": "Hasilkan outline minggu 1.",
}

SAMPLE_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string"},
        "topic": {"type": "string"},
    },
    "required": ["status", "topic"],
}


class MockProvider(BaseLLMProvider):
    provider_name = "mock"
    model = "mock-model"

    def __init__(self, responses: Optional[List[Any]] = None):
        self._responses = list(responses) if responses is not None else []
        self.calls: List[dict] = []
        self._configured = True

    def is_configured(self) -> bool:
        return self._configured

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any) -> str:
        resp = await self.generate_response(prompt, system_prompt=system_prompt, **kwargs)
        return resp.content

    async def generate_response(
        self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any
    ) -> LLMResponse:
        self.calls.append({
            "prompt": prompt,
            "system_prompt": system_prompt,
            "kwargs": kwargs,
        })
        if not self._responses:
            return LLMResponse(
                content='{"status": "success", "topic": "Algoritma Dasar"}',
                usage=LLMUsage(prompt_tokens=40, completion_tokens=20, total_tokens=60),
                model=self.model,
            )
        current = self._responses.pop(0)
        if isinstance(current, Exception):
            raise current
        return current


@pytest.fixture
def no_delay_sleep():
    """Sleep helper mock untuk menghindari jeda nyata saat pengujian retry."""
    recorded_sleeps: List[float] = []

    async def _mock_sleep(duration: float):
        recorded_sleeps.append(duration)

    return _mock_sleep, recorded_sleeps


# ------------------ 1. Happy Path & Acceptance Unit Test ------------------


@pytest.mark.asyncio
async def test_execute_prompt_success_with_metadata():
    provider = MockProvider([
        LLMResponse(
            content='{"status": "success", "topic": "Algoritma"}',
            usage=LLMUsage(prompt_tokens=50, completion_tokens=25, total_tokens=75),
            model="mock-gpt",
        )
    ])
    service = LLMService(provider)

    result = await service.execute_prompt(
        prompt_name="default",
        version="v1",
        variables=SAMPLE_VARIABLES,
        output_schema=SAMPLE_SCHEMA,
    )

    # Output ter-parse
    assert result.data == {"status": "success", "topic": "Algoritma"}
    assert result.parsed_content == {"status": "success", "topic": "Algoritma"}
    assert result.raw_content == '{"status": "success", "topic": "Algoritma"}'

    # Metadata pemanggilan tercatat lengkap
    meta = result.metadata
    assert meta.prompt_name == "default"
    assert meta.prompt_version == "v1"
    assert meta.model == "mock-gpt"
    assert meta.prompt_tokens == 50
    assert meta.completion_tokens == 25
    assert meta.total_tokens == 75
    assert meta.attempts == 1
    assert meta.duration_ms >= 0.0

    # Provider menerima response_format structured output
    assert len(provider.calls) == 1
    call_kwargs = provider.calls[0]["kwargs"]
    assert "response_format" in call_kwargs
    rf = call_kwargs["response_format"]
    assert rf["type"] == "json_schema"
    assert rf["json_schema"]["schema"] == SAMPLE_SCHEMA


# ------------------ 2. Retry Sukses di Percobaan ke-2 ------------------


@pytest.mark.asyncio
async def test_retry_succeeds_on_second_attempt(no_delay_sleep):
    mock_sleep, recorded_sleeps = no_delay_sleep
    provider = MockProvider([
        LLMRateLimitError("Rate limit exceeded"),  # Percobaan 1 gagal (429)
        LLMResponse(                               # Percobaan 2 sukses
            content='{"status": "success", "topic": "Retry Berhasil"}',
            usage=LLMUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20),
            model="mock-gpt",
        ),
    ])
    service = LLMService(provider)

    result = await service.execute_prompt(
        prompt_name="default",
        version="v1",
        variables=SAMPLE_VARIABLES,
        output_schema=SAMPLE_SCHEMA,
        max_retries=3,
        sleep_fn=mock_sleep,
    )

    assert result.data["status"] == "success"
    assert result.metadata.attempts == 2
    assert len(provider.calls) == 2
    assert len(recorded_sleeps) == 1
    assert recorded_sleeps[0] > 0


# ------------------ 3. Retry Habis (Bahasa Indonesia Jelas) ------------------


@pytest.mark.asyncio
async def test_retry_exhausted_raises_indonesian_error(no_delay_sleep):
    mock_sleep, recorded_sleeps = no_delay_sleep
    provider = MockProvider([
        LLMTimeoutError("Timeout 1"),
        LLMTimeoutError("Timeout 2"),
        LLMTimeoutError("Timeout 3"),
    ])
    service = LLMService(provider)

    with pytest.raises(LLMRetryExhaustedError) as exc_info:
        await service.execute_prompt(
            prompt_name="default",
            version="v1",
            variables=SAMPLE_VARIABLES,
            output_schema=SAMPLE_SCHEMA,
            max_retries=3,
            sleep_fn=mock_sleep,
        )

    assert len(provider.calls) == 3
    assert len(recorded_sleeps) == 2
    # Pesan kesalahan bahasa Indonesia yang jelas dan sederhana
    err_msg = str(exc_info.value)
    assert "Gagal terhubung ke layanan LLM setelah 3 kali percobaan" in err_msg


# ------------------ 4. Error Permanen Tidak Di-retry ------------------


@pytest.mark.parametrize(
    "permanent_error",
    [
        LLMConfigurationError("API key missing or rejected"),
        LLMProviderError("Bad request HTTP 400"),
    ],
)
@pytest.mark.asyncio
async def test_permanent_error_not_retried(no_delay_sleep, permanent_error):
    mock_sleep, recorded_sleeps = no_delay_sleep
    provider = MockProvider([permanent_error])
    service = LLMService(provider)

    with pytest.raises(type(permanent_error)):
        await service.execute_prompt(
            prompt_name="default",
            version="v1",
            variables=SAMPLE_VARIABLES,
            output_schema=SAMPLE_SCHEMA,
            max_retries=3,
            sleep_fn=mock_sleep,
        )

    # Provider hanya dipanggil 1 kali; tidak ada backoff/sleep
    assert len(provider.calls) == 1
    assert len(recorded_sleeps) == 0


# ------------------ 5. Backoff Naik Eksponensial ------------------


def test_backoff_increases_exponentially():
    # Tanpa jitter untuk menguji nilai eksponensial deterministik
    w1 = calculate_backoff(attempt=1, base_factor=2.0, min_wait=0.5, max_wait=10.0, jitter=False)
    w2 = calculate_backoff(attempt=2, base_factor=2.0, min_wait=0.5, max_wait=10.0, jitter=False)
    w3 = calculate_backoff(attempt=3, base_factor=2.0, min_wait=0.5, max_wait=10.0, jitter=False)
    w4 = calculate_backoff(attempt=4, base_factor=2.0, min_wait=0.5, max_wait=10.0, jitter=False)

    assert w1 == 0.5   # 0.5 * 2^0
    assert w2 == 1.0   # 0.5 * 2^1
    assert w3 == 2.0   # 0.5 * 2^2
    assert w4 == 4.0   # 0.5 * 2^3

    # Maksimal dibatasi oleh max_wait
    w_capped = calculate_backoff(attempt=10, base_factor=2.0, min_wait=0.5, max_wait=5.0, jitter=False)
    assert w_capped == 5.0

    # Dengan jitter: selalu lebih besar atau sama dengan nilai dasar delay
    w_jitter = calculate_backoff(attempt=2, base_factor=2.0, min_wait=1.0, max_wait=10.0, jitter=True)
    assert w_jitter >= 2.0


# ------------------ 6. Log Tidak Memuat Prompt / Raw Content / Secret ------------------


@pytest.mark.asyncio
async def test_log_does_not_contain_prompt_or_raw_content(caplog, no_delay_sleep):
    mock_sleep, _ = no_delay_sleep
    secret_marker = "SENSITIVE_SECRET_TOKEN_XYZ_12345"
    secret_content = "RAW_MODEL_OUTPUT_SECRET_CONTENT_98765"

    custom_variables = {
        **SAMPLE_VARIABLES,
        "additional_prompt": f"Instruksi rahasia: {secret_marker}",
    }

    provider = MockProvider([
        LLMRateLimitError("Provider 429 detail"),
        LLMResponse(
            content=f'{{"status": "success", "topic": "{secret_content}"}}',
            usage=LLMUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20),
            model="mock-gpt",
        ),
    ])
    service = LLMService(provider)

    with caplog.at_level(logging.DEBUG):
        await service.execute_prompt(
            prompt_name="default",
            version="v1",
            variables=custom_variables,
            output_schema=SAMPLE_SCHEMA,
            max_retries=2,
            sleep_fn=mock_sleep,
        )

    logged_text = caplog.text

    # Pastikan teks log memuat informasi operasional yang sah
    assert "default/v1" in logged_text
    assert "mock-gpt" in logged_text

    # Dilarang mencetak variabel, potongan prompt, raw_content, maupun detail provider exception
    assert secret_marker not in logged_text
    assert secret_content not in logged_text
    assert "Provider 429 detail" not in logged_text


# ------------------ 7. JSON Salah Tidak Di-retry (BE-09.2 Concern) ------------------


@pytest.mark.asyncio
async def test_invalid_json_output_does_not_retry(no_delay_sleep):
    mock_sleep, recorded_sleeps = no_delay_sleep
    provider = MockProvider([
        LLMResponse(
            content="Bukan JSON yang valid {status: missing_quote",
            usage=LLMUsage(10, 10, 20),
            model="mock-gpt",
        )
    ])
    service = LLMService(provider)

    with pytest.raises(LLMInvalidOutputError) as exc_info:
        await service.execute_prompt(
            prompt_name="default",
            version="v1",
            variables=SAMPLE_VARIABLES,
            output_schema=SAMPLE_SCHEMA,
            max_retries=3,
            sleep_fn=mock_sleep,
        )

    # Provider hanya dipanggil 1 kali; tidak di-retry
    assert len(provider.calls) == 1
    assert len(recorded_sleeps) == 0
    assert "bukan JSON yang valid" in str(exc_info.value)
