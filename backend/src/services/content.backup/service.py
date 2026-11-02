from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from enum import StrEnum

from pydantic import ValidationError

from src.config import settings
from src.schemas.content import GeneratedLearningMaterial, WeekContext
from src.services.content.pipeline import (
    MAX_ERROR_CHARS,
    EmitEvent,
    RecordTrace,
    build_feedback,
    classify_provider_error,
    emit,
    explain_validation_error,
    trace,
)
from src.services.content.schema import CONTENT_OUTPUT_SCHEMA
from src.services.llm import LLMService, OpenAIProvider

logger = logging.getLogger(__name__)

PROMPT_NAME = "content_generation"
PROMPT_VERSION = "v1"

FEEDBACK_CLOSING = "Perbaiki hanya bagian yang salah agar sesuai schema."


class ContentEvent(StrEnum):
    GENERATION_STARTED = "Memulai pembuatan materi"
    CONTEXT_BUILT = "Konteks minggu disiapkan"
    LLM_CALLING = "Mengirim ke model"
    LLM_RESPONDED = "Respons model diterima"
    VALIDATING = "Memvalidasi hasil"
    RETRY_FIX = "Memperbaiki hasil"
    GENERATION_COMPLETED = "Pembuatan materi selesai"
    GENERATION_FAILED = "Pembuatan materi gagal"


class ContentGenerationError(Exception):
    code = "LLM_GENERATION_FAILED"

    def __init__(
        self,
        message: str,
        *,
        reason_code: str | None = None,
        details: list[str] | None = None,
        attempts: int = 0,
    ) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.details = details or []
        self.attempts = attempts


async def generate_week_content(
    ctx: WeekContext,
    max_fix_attempts: int | None = None,
    emit_event: EmitEvent | None = None,
    record_trace: RecordTrace | None = None,
    additional_prompt: str = "",
) -> GeneratedLearningMaterial:
    """Buat materi pembelajaran satu minggu dan validasi hasilnya.

    `ctx` dibangun dari database oleh pemanggil. Retry hanya untuk output tidak
    valid (bukan JSON atau tidak sesuai schema). Error provider langsung
    dilaporkan tanpa retry.
    """
    if max_fix_attempts is None:
        max_fix_attempts = settings.content_generation_max_fix_attempts
    if max_fix_attempts < 0:
        raise ValueError("max_fix_attempts tidak boleh negatif")

    total = max_fix_attempts + 1
    prompt_id = f"{PROMPT_NAME}/{PROMPT_VERSION}"

    await emit(emit_event, ContentEvent.GENERATION_STARTED, week=ctx.week)
    week_context = json.dumps(ctx.to_prompt_dict(), ensure_ascii=False, indent=2)
    await emit(emit_event, ContentEvent.CONTEXT_BUILT, week=ctx.week)

    provider = OpenAIProvider()
    service = LLMService(provider)

    feedback = ""
    last_code: str | None = None
    last_details: list[str] = []

    for attempt in range(1, total + 1):
        started = time.perf_counter()

        def elapsed_ms() -> float:
            return round((time.perf_counter() - started) * 1000, 2)

        await emit(emit_event, ContentEvent.LLM_CALLING, week=ctx.week, attempt=attempt)

        # 1) Panggilan LLM. Error provider tidak di-retry.
        try:
            result = await service.execute_prompt(
                prompt_name=PROMPT_NAME,
                version=PROMPT_VERSION,
                variables={
                    "week_context": week_context,
                    "additional_prompt": additional_prompt,
                    "validation_feedback": feedback,
                },
                output_schema=CONTENT_OUTPUT_SCHEMA,
            )
        except Exception as exc:
            code, message = classify_provider_error(exc)
            await trace(
                record_trace,
                attempt=attempt, prompt=prompt_id, model=None,
                tokens_input=None, tokens_output=None, duration_ms=elapsed_ms(),
                validation="provider_error", reason_code=code,
                error=str(exc)[:MAX_ERROR_CHARS],
            )
            await emit(
                emit_event, ContentEvent.GENERATION_FAILED,
                week=ctx.week, attempt=attempt, reason_code=code, details=[],
            )
            raise ContentGenerationError(
                message, reason_code=code, attempts=attempt
            ) from exc

        model = getattr(provider, "model", None)
        meta = getattr(result, "metadata", None)
        tokens_in = getattr(meta, "prompt_tokens", None)
        tokens_out = getattr(meta, "completion_tokens", None)

        await emit(
            emit_event, ContentEvent.LLM_RESPONDED, week=ctx.week, attempt=attempt,
            tokens_input=tokens_in, tokens_output=tokens_out, duration_ms=elapsed_ms(),
        )

        # 2) Validasi output.
        await emit(emit_event, ContentEvent.VALIDATING, week=ctx.week, attempt=attempt)

        raw_text: str | None = None
        error_text = ""
        details: list[str] = []
        try:
            raw_output = result.data
            if isinstance(raw_output, str):
                raw_text = raw_output
                raw_output = json.loads(raw_output)
            else:
                raw_text = json.dumps(raw_output, ensure_ascii=False, default=str)
            material = GeneratedLearningMaterial.model_validate(raw_output)
        except json.JSONDecodeError as exc:
            code = "OUTPUT_NOT_JSON"
            error_text = str(exc)
        except ValidationError as exc:
            code = "SCHEMA_VALIDATION_FAILED"
            details = explain_validation_error(exc)
            error_text = str(exc)
        else:
            await trace(
                record_trace,
                attempt=attempt, prompt=prompt_id, model=model,
                tokens_input=tokens_in, tokens_output=tokens_out,
                duration_ms=elapsed_ms(), validation="success",
                reason_code=None, error=None,
            )
            await emit(
                emit_event, ContentEvent.GENERATION_COMPLETED,
                week=ctx.week, attempt=attempt,
            )
            return material

        # 3) Validasi gagal: catat, lalu retry bila masih ada jatah.
        last_code, last_details = code, details
        await trace(
            record_trace,
            attempt=attempt, prompt=prompt_id, model=model,
            tokens_input=tokens_in, tokens_output=tokens_out,
            duration_ms=elapsed_ms(), validation="failed",
            reason_code=code, error=error_text[:MAX_ERROR_CHARS],
        )

        if attempt < total:
            feedback = build_feedback(details, raw_text, closing=FEEDBACK_CLOSING)
            await emit(
                emit_event, ContentEvent.RETRY_FIX,
                week=ctx.week, attempt=attempt, reason_code=code, details=details,
            )

    failure_message = (
        f"Pembuatan materi minggu {ctx.week} gagal setelah {total} percobaan."
    )
    await emit(
        emit_event, ContentEvent.GENERATION_FAILED,
        week=ctx.week, attempt=total, reason_code=last_code, details=last_details,
    )
    raise ContentGenerationError(
        failure_message, reason_code=last_code, details=last_details, attempts=total
    )


@dataclass
class WeekResult:
    ctx: WeekContext
    material: GeneratedLearningMaterial | None = None
    error: ContentGenerationError | None = None


async def generate_contents(
    contexts: list[WeekContext],
    *,
    concurrency: int = 1,
    **kwargs,  # max_fix_attempts, emit_event, record_trace, additional_prompt
) -> list[WeekResult]:
    """Buat materi untuk banyak minggu. Satu minggu gagal tidak menghentikan yang lain."""
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def run(ctx: WeekContext) -> WeekResult:
        async with semaphore:
            try:
                return WeekResult(ctx, material=await generate_week_content(ctx, **kwargs))
            except ContentGenerationError as exc:
                return WeekResult(ctx, error=exc)

    return await asyncio.gather(*(run(c) for c in contexts))
