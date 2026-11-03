from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from enum import StrEnum

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.schemas.content import (
    GeneratedLearningMaterial,
    WeekContext,
    WeeklyContentContext,
)
from src.services.content.repository import ContentGenerationRepository
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
from sqlalchemy.exc import SQLAlchemyError
from src.models.course_plan import CoursePlan

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


@dataclass
class WeekResult:
    ctx: WeekContext
    material: GeneratedLearningMaterial | None = None
    error: ContentGenerationError | None = None


def _build_week_contexts(
    plan: CoursePlan,
    weeks: list[CoursePlanWeek],
) -> list[WeekContext]:

    if not weeks:
        raise ContentGenerationError(
            "Course plan belum memiliki course plan weeks."
        )

    contexts = []

    for week in weeks:
        meta = week.metadata_ or {}

        contexts.append(
            WeekContext(
                course_plan_id=plan.id,
                course_plan_week_id=week.id,
                week_number=week.week_number,
                week_data=WeeklyContentContext(
                    week_number=week.week_number,
                    week_type=meta.get("week_type", "regular"),
                    title=week.title,
                    learning_outcomes=week.learning_outcomes,
                    topics=(week.topics or {}).get("items", []),
                    methods=(week.methods or {}).get("items", []),
                    assessment=week.assessment,
                ),
            )
        )

    return contexts


async def _generate_week_content(
    ctx: WeekContext,
    *,
    max_fix_attempts: int | None = None,
    emit_event: EmitEvent | None = None,
    record_trace: RecordTrace | None = None,
    additional_prompt: str = "",
) -> GeneratedLearningMaterial:

    if max_fix_attempts is None:
        max_fix_attempts = settings.content_generation_max_fix_attempts

    if max_fix_attempts < 0:
        raise ValueError("max_fix_attempts tidak boleh negatif")

    total = max_fix_attempts + 1
    prompt_id = f"{PROMPT_NAME}/{PROMPT_VERSION}"

    await emit(
        emit_event,
        ContentEvent.GENERATION_STARTED,
        week=ctx.week,
    )

    week_context = json.dumps(
        ctx.to_prompt_dict(),
        ensure_ascii=False,
        indent=2,
    )

    await emit(
        emit_event,
        ContentEvent.CONTEXT_BUILT,
        week=ctx.week,
    )

    provider = OpenAIProvider()
    service = LLMService(provider)

    feedback = ""
    last_code: str | None = None
    last_details: list[str] = []

    for attempt in range(1, total + 1):
        started = time.perf_counter()

        def elapsed_ms() -> float:
            return round((time.perf_counter() - started) * 1000, 2)

        await emit(
            emit_event,
            ContentEvent.LLM_CALLING,
            week=ctx.week,
            attempt=attempt,
        )

        try:
            result = await service.execute_prompt(
                prompt_name=PROMPT_NAME,
                version=PROMPT_VERSION,
                variables={
                    "week_context": json.dumps(
                        ctx.to_prompt_dict(),
                        ensure_ascii=False,
                        indent=2,
                    ),
                    "instructor_profile": "Belum tersedia",
                    "additional_prompt": additional_prompt or "Tidak ada instruksi tambahan.",
                    "validation_feedback": feedback,
                },
                output_schema=CONTENT_OUTPUT_SCHEMA,
            )

        except Exception as exc:
            code, message = classify_provider_error(exc)

            await trace(
                record_trace,
                attempt=attempt,
                prompt=prompt_id,
                model=None,
                tokens_input=None,
                tokens_output=None,
                duration_ms=elapsed_ms(),
                validation="provider_error",
                reason_code=code,
                error=str(exc)[:MAX_ERROR_CHARS],
            )

            await emit(
                emit_event,
                ContentEvent.GENERATION_FAILED,
                week=ctx.week,
                attempt=attempt,
                reason_code=code,
                details=[],
            )

            raise ContentGenerationError(
                message,
                reason_code=code,
                attempts=attempt,
            ) from exc

        model = getattr(provider, "model", None)
        meta = getattr(result, "metadata", None)
        tokens_in = getattr(meta, "prompt_tokens", None)
        tokens_out = getattr(meta, "completion_tokens", None)

        await emit(
            emit_event,
            ContentEvent.LLM_RESPONDED,
            week=ctx.week,
            attempt=attempt,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            duration_ms=elapsed_ms(),
        )

        await emit(
            emit_event,
            ContentEvent.VALIDATING,
            week=ctx.week,
            attempt=attempt,
        )

        raw_text: str | None = None
        error_text = ""
        details: list[str] = []

        try:
            raw_output = result.data

            if isinstance(raw_output, str):
                raw_text = raw_output
                raw_output = json.loads(raw_output)
            else:
                raw_text = json.dumps(
                    raw_output,
                    ensure_ascii=False,
                    default=str,
                )

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
                attempt=attempt,
                prompt=prompt_id,
                model=model,
                tokens_input=tokens_in,
                tokens_output=tokens_out,
                duration_ms=elapsed_ms(),
                validation="success",
                reason_code=None,
                error=None,
            )

            await emit(
                emit_event,
                ContentEvent.GENERATION_COMPLETED,
                week=ctx.week,
                attempt=attempt,
            )

            return material

        last_code = code
        last_details = details

        await trace(
            record_trace,
            attempt=attempt,
            prompt=prompt_id,
            model=model,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            duration_ms=elapsed_ms(),
            validation="failed",
            reason_code=code,
            error=error_text[:MAX_ERROR_CHARS],
        )

        if attempt < total:
            feedback = build_feedback(
                details,
                raw_text,
                closing=FEEDBACK_CLOSING,
            )

            await emit(
                emit_event,
                ContentEvent.RETRY_FIX,
                week=ctx.week,
                attempt=attempt,
                reason_code=code,
                details=details,
            )

    failure_message = (
        f"Pembuatan materi minggu {ctx.week} gagal "
        f"setelah {total} percobaan."
    )

    await emit(
        emit_event,
        ContentEvent.GENERATION_FAILED,
        week=ctx.week,
        attempt=total,
        reason_code=last_code,
        details=last_details,
    )

    raise ContentGenerationError(
        failure_message,
        reason_code=last_code,
        details=last_details,
        attempts=total,
    )


async def generate_contents(
    db: AsyncSession,
    course_plan_id: str,
    *,
    week_numbers: list[int] | None = None,
    concurrency: int = 1,
    max_fix_attempts: int | None = None,
    emit_event: EmitEvent | None = None,
    record_trace: RecordTrace | None = None,
    additional_prompt: str = "",
    save: bool = True,
) -> list[WeekResult]:

    if concurrency < 1:
        raise ValueError("concurrency minimal 1")

    print("COURSE PLAN ID:", course_plan_id)

    data = await ContentGenerationRepository.get_context(
        db,
        course_plan_id,
    )

    if data is None:
        raise ContentGenerationError(
            "Course plan tidak ditemukan."
        )

    plan, weeks = data

    contexts = _build_week_contexts(plan, weeks)

    contexts = [
        ctx
        for ctx in contexts
        if ctx.week_data.week_type.lower() == "regular"
    ]

    if week_numbers is not None:
        if not week_numbers:
            raise ValueError("week_numbers tidak boleh kosong.")

        if any(week < 1 for week in week_numbers):
            raise ValueError("Nomor minggu harus lebih besar dari 0.")

        if len(week_numbers) != len(set(week_numbers)):
            raise ValueError("Nomor minggu tidak boleh duplikat.")

        available_weeks = {
            ctx.week_number for ctx in contexts
        }

        invalid_weeks = set(week_numbers) - available_weeks

        if invalid_weeks:
            raise ValueError(
                f"Minggu tidak tersedia atau bukan minggu reguler: "
                f"{sorted(invalid_weeks)}"
            )

        selected_weeks = set(week_numbers)

        contexts = [
            ctx
            for ctx in contexts
            if ctx.week_number in selected_weeks
        ]

    if not contexts:
        raise ValueError(
            "Tidak ada minggu pembelajaran yang tersedia."
        )

    semaphore = asyncio.Semaphore(concurrency)

    async def run(ctx: WeekContext) -> WeekResult:
        async with semaphore:
            try:
                material = await _generate_week_content(
                    ctx,
                    max_fix_attempts=max_fix_attempts,
                    emit_event=emit_event,
                    record_trace=record_trace,
                    additional_prompt=additional_prompt,
                )

                return WeekResult(
                    ctx=ctx,
                    material=material,
                )

            except ContentGenerationError as exc:
                logger.exception(
                    "Content generation failed for week %s",
                    ctx.week,
                )

                return WeekResult(
                    ctx=ctx,
                    error=exc,
                )

    results = await asyncio.gather(
        *(run(ctx) for ctx in contexts)
    )

    if save:
        for r in results:
            if r.material is None:
                continue

            try:
                m = r.material
                markdown = "# TODO: markdown belum dirender"
                
                content_data = m.content_data.model_dump(mode="json")
                content_type = m.content_type.value

                existing = await ContentGenerationRepository.get_by_week_id(
                    db,
                    r.ctx.course_plan_week_id,
                )

                if (
                    existing is not None
                    and existing.status == ContentStatus.APPROVED
                ):
                    r.material = None
                    r.error = ContentGenerationError(
                        "Konten sudah APPROVED, tidak bisa ditimpa.",
                        reason_code="ALREADY_APPROVED",
                    )
                    continue

                elif existing is None:
                    await ContentGenerationRepository.create(
                        db,
                        course_plan_week_id=r.ctx.course_plan_week_id,
                        title=m.title,
                        content_type=content_type,
                        content_data=content_data,
                        content_markdown=markdown,
                    )

                else:
                    await ContentGenerationRepository.update_content(
                        db,
                        existing,
                        title=m.title,
                        content_type=content_type,
                        content_data=content_data,
                        content_markdown=markdown,
                    )

                await db.commit()

            except SQLAlchemyError:
                await db.rollback()

                logger.exception(
                    "Gagal menyimpan minggu %s",
                    r.ctx.week,
                )

                r.material = None
                r.error = ContentGenerationError(
                    "Gagal menyimpan konten ke database.",
                    reason_code="DB_SAVE_FAILED",
                )

    return results


async def generate_week_content(
    db: AsyncSession,
    course_plan_week_id: str,
    week_number: int,
    *,
    max_fix_attempts: int | None = None,
    emit_event: EmitEvent | None = None,
    record_trace: RecordTrace | None = None,
    additional_prompt: str = "",
) -> GeneratedLearningMaterial:

    result = await db.execute(
        select(CoursePlan, CoursePlanWeek)
        .join(
            CoursePlanWeek,
            CoursePlanWeek.course_plan_id == CoursePlan.id,
        )
        .where(
            CoursePlanWeek.id == course_plan_week_id
        )
    )

    row = result.first()

    if row is None:
        raise ContentGenerationError(
            f"Course plan week tidak ditemukan: {course_plan_week_id}"
        )

    plan = row[0]

    weeks_result = await db.execute(
        select(CoursePlanWeek)
        .where(
            CoursePlanWeek.course_plan_id == plan.id
        )
    )

    weeks = weeks_result.scalars().all()

    contexts = _build_week_contexts(plan, weeks)

    ctx = next(
        (
            context
            for context in contexts
            if context.week_number == week_number
            and context.course_plan_week_id == course_plan_week_id
        ),
        None,
    )

    if ctx is None:
        raise ContentGenerationError(
            f"Week {week_number} tidak ditemukan."
        )

    week_type = ctx.week_data.week_type.lower()

    if week_type != "regular":
        raise ContentGenerationError(
            f"Week {week_number} bukan minggu pembelajaran reguler."
        )

    return await _generate_week_content(
        ctx,
        max_fix_attempts=max_fix_attempts,
        emit_event=emit_event,
        record_trace=record_trace,
        additional_prompt=additional_prompt,
    )
