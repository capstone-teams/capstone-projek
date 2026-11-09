from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.course_plan import CoursePlan
from src.models.course_plan_week import CoursePlanWeek
from src.schemas.content import (
    REGISTRY,
    WeekContext,
    WeeklyContentContext,
    to_row,
)
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
from src.services.content.repository import ContentGenerationRepository
from src.services.content.schema import get_output_schema
from src.services.llm import LLMService, OpenAIProvider

logger = logging.getLogger(__name__)


PROMPT_NAME = "learning_material"
PROMPT_VERSION = "v1"

FEEDBACK_CLOSING = "Perbaiki hanya bagian yang salah agar sesuai schema."


# ==========================================
# JENIS KONTEN PER WEEK TYPE
# ==========================================
@dataclass(frozen=True)
class GenerationSpec:
    key: str  # kunci REGISTRY di src.schemas.content
    prompt_name: str  # nama prompt di prompts/<nama>/<versi>
    label: str  # dipakai untuk pesan error


GENERATION_SPECS: dict[str, GenerationSpec] = {
    "LEARNING_MATERIAL": GenerationSpec("LEARNING_MATERIAL", PROMPT_NAME, "materi"),
    "RESOURCE": GenerationSpec("RESOURCE", "learning_resource", "sumber belajar"),
    "QUIZ": GenerationSpec("QUIZ", "quiz", "kuis"),
    "ASSIGNMENT": GenerationSpec("ASSIGNMENT", "assignment", "tugas"),
}

# week_type (huruf kecil) -> jenis konten yang dibuat
WEEK_TYPE_CONTENT_TYPES: dict[str, tuple[str, ...]] = {
    "regular": ("LEARNING_MATERIAL",),
    "quiz": ("QUIZ",),
    "kuis": ("QUIZ",),
    "assignment": ("ASSIGNMENT",),
    "tugas": ("ASSIGNMENT",),
}


# Jenis konten yang TIDAK dibuat otomatis, tapi boleh diminta lewat content_types.
WEEK_TYPE_OPTIONAL_CONTENT_TYPES: dict[str, tuple[str, ...]] = {
    "regular": ("RESOURCE", "ASSIGNMENT", "QUIZ"),
}


def _content_types_for(
    ctx: WeekContext,
    include_assignment: bool = False,
) -> tuple[str, ...]:
    """Jenis konten yang dibuat secara default untuk week type ini.

    include_assignment=True (opsi dosen) menambahkan ASSIGNMENT di minggu yang
    menghasilkan materi.
    """
    types = WEEK_TYPE_CONTENT_TYPES.get(ctx.week_data.week_type.lower(), ())
    if include_assignment and "LEARNING_MATERIAL" in types and "ASSIGNMENT" not in types:
        types += ("ASSIGNMENT",)
    return types


def _available_content_types_for(ctx: WeekContext) -> tuple[str, ...]:
    """Default + opsional (yang hanya dibuat bila diminta eksplisit)."""
    week_type = ctx.week_data.week_type.lower()
    types = _content_types_for(ctx)
    extra = tuple(
        t for t in WEEK_TYPE_OPTIONAL_CONTENT_TYPES.get(week_type, ()) if t not in types
    )
    return types + extra


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
    # Hasil generasi (model Output sesuai jenis konten). Nama `material` dipertahankan.
    material: BaseModel | None = None
    error: ContentGenerationError | None = None
    content_type: str = "LEARNING_MATERIAL"


QUIZ_WEEK_TYPES = {"quiz", "kuis"}


def _is_empty_week(week: WeeklyContentContext) -> bool:
    return not week.topics and not week.learning_outcomes


def _has_content_basis(ctx: WeekContext, key: str) -> bool:
    """Ada bahan untuk membuat konten? Kuis boleh memakai minggu-minggu sebelumnya."""
    if not _is_empty_week(ctx.week_data):
        return True
    return key == "QUIZ" and bool(ctx.covered_weeks)


def _as_items(value) -> list:
    """topics / methods di DB bisa berupa {"items": [...]} atau langsung list."""
    if isinstance(value, dict):
        items = value.get("items", [])
        return list(items) if isinstance(items, (list, tuple)) else []
    if isinstance(value, (list, tuple)):
        return list(value)
    return []


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
        meta = week.metadata_ if isinstance(week.metadata_, dict) else {}

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
                    topics=_as_items(week.topics),
                    methods=_as_items(week.methods),
                    assessment=week.assessment,
                ),
            )
        )

    # Minggu kuis (atau minggu reguler yang kosong) mencakup minggu-minggu sebelumnya
    # sejak kuis terakhir.
    buffer: list[WeeklyContentContext] = []

    for ctx in sorted(contexts, key=lambda c: c.week_number):
        week_type = ctx.week_data.week_type.lower()

        if week_type in QUIZ_WEEK_TYPES or (
            week_type == "regular" and _is_empty_week(ctx.week_data)
        ):
            ctx.covered_weeks = list(buffer)
            buffer = []
        elif week_type == "regular":
            buffer.append(ctx.week_data)

    return contexts


async def list_weeks(db: AsyncSession, course_plan_id: str) -> list[WeekContext]:
    """Daftar minggu (urut) beserta tipenya; berguna untuk memeriksa data course plan."""
    data = await ContentGenerationRepository.get_context(db, course_plan_id)

    if data is None:
        raise ContentGenerationError("Course plan tidak ditemukan.")

    plan, weeks = data

    return sorted(_build_week_contexts(plan, weeks), key=lambda c: c.week_number)


async def _generate_week_content(
    ctx: WeekContext,
    *,
    content_type: str = "LEARNING_MATERIAL",
    max_fix_attempts: int | None = None,
    emit_event: EmitEvent | None = None,
    record_trace: RecordTrace | None = None,
    additional_prompt: str = "",
    previous_version: str = "",
    revision_notes: str = "",
    learning_resources: str = "",
) -> BaseModel:

    spec = GENERATION_SPECS[content_type]
    output_model = REGISTRY[spec.key].output_model
    output_schema = get_output_schema(spec.key)

    if max_fix_attempts is None:
        max_fix_attempts = settings.content_generation_max_fix_attempts

    if max_fix_attempts < 0:
        raise ValueError("max_fix_attempts tidak boleh negatif")

    total = max_fix_attempts + 1
    prompt_id = f"{spec.prompt_name}/{PROMPT_VERSION}"

    # Tanpa topics / Sub-CPMK model hanya bisa mengembalikan data kosong: jangan buang token.
    if not _has_content_basis(ctx, spec.key):
        details = [
            "Topics dan Sub-CPMK minggu ini kosong"
            + (", dan tidak ada minggu sebelumnya yang bisa dicakup." if spec.key == "QUIZ" else "."),
            "Jika ini minggu kuis, tandai week_type = quiz atau pilih jenis konten kuis secara manual.",
            "Jika bukan, lengkapi topics dan learning_outcomes minggu ini.",
        ]

        await emit(
            emit_event,
            ContentEvent.GENERATION_FAILED,
            week=ctx.week,
            reason_code="EMPTY_WEEK_CONTEXT",
            details=details,
            content_type=spec.key,
        )

        raise ContentGenerationError(
            f"Minggu {ctx.week} tidak memiliki bahan untuk membuat {spec.label}.",
            reason_code="EMPTY_WEEK_CONTEXT",
            details=details,
        )

    await emit(
        emit_event,
        ContentEvent.GENERATION_STARTED,
        week=ctx.week,
        content_type=spec.key,
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
        content_type=spec.key,
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
            content_type=spec.key,
        )

        try:
            result = await service.execute_prompt(
                prompt_name=spec.prompt_name,
                version=PROMPT_VERSION,
                variables={
                    "week_context": week_context,
                    "instructor_profile": "Belum tersedia",
                    "additional_prompt": additional_prompt or "Tidak ada instruksi tambahan.",
                    "previous_version": previous_version,
                    "revision_notes": revision_notes,
                    "learning_resources": learning_resources or NO_RESOURCES_TEXT,
                    "validation_feedback": feedback,
                },
                output_schema=output_schema,
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
                content_type=spec.key,
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
            content_type=spec.key,
        )

        await emit(
            emit_event,
            ContentEvent.VALIDATING,
            week=ctx.week,
            attempt=attempt,
            content_type=spec.key,
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

            material = output_model.model_validate(raw_output)

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
                content_type=spec.key,
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
                content_type=spec.key,
            )

    failure_message = (
        f"Pembuatan {spec.label} minggu {ctx.week} gagal "
        f"setelah {total} percobaan."
    )

    await emit(
        emit_event,
        ContentEvent.GENERATION_FAILED,
        week=ctx.week,
        attempt=total,
        reason_code=last_code,
        details=last_details,
        content_type=spec.key,
    )

    raise ContentGenerationError(
        failure_message,
        reason_code=last_code,
        details=last_details,
        attempts=total,
    )


NO_RESOURCES_TEXT = "Tidak ada sumber belajar yang tersedia."


def _learning_resources_text(title: str, data: dict | None) -> str:
    """Resource sebagai teks untuk prompt materi (daftar, siap bila nanti lebih dari satu)."""
    body = {
        k: v for k, v in (data or {}).items() if k not in ("traceability", "sub_cpmk_codes")
    }
    return json.dumps([{"title": title, **body}], ensure_ascii=False, indent=2)


def _status_value(obj) -> str:
    """Nilai status sebagai string, berlaku untuk ContentStatus maupun ActivityStatus."""
    status = obj.status
    return getattr(status, "value", status)


async def _save_result(db: AsyncSession, r: WeekResult) -> None:
    """Simpan satu hasil generasi ke tabel contents atau activities sesuai jenisnya."""
    key = r.content_type
    row = to_row(key, r.material, r.ctx)
    week_id = r.ctx.course_plan_week_id

    if REGISTRY[key].table == "contents":
        existing = await ContentGenerationRepository.get_by_week_id(db, week_id, key)

        if existing is not None and _status_value(existing) == "APPROVED":
            raise ContentGenerationError(
                "Konten sudah APPROVED, tidak bisa ditimpa.",
                reason_code="ALREADY_APPROVED",
            )

        fields = {
            "title": row["title"],
            "content_type": row["content_type"],
            "content_data": row["content_data"],
            "content_markdown": row["content_markdown"],
        }

        if existing is None:
            await ContentGenerationRepository.create(
                db,
                course_plan_week_id=week_id,
                **fields,
            )
        else:
            await ContentGenerationRepository.update_content(
                db,
                existing,
                **fields,
            )
        return

    existing = await ContentGenerationRepository.get_activity_by_week_id(
        db,
        week_id,
        key,
    )

    if existing is not None and _status_value(existing) == "APPROVED":
        raise ContentGenerationError(
            "Konten sudah APPROVED, tidak bisa ditimpa.",
            reason_code="ALREADY_APPROVED",
        )

    if existing is None:
        await ContentGenerationRepository.create_activity(
            db,
            course_plan_week_id=week_id,
            type=row["type"],
            title=row["title"],
            activity_data=row["activity_data"],
        )
    else:
        await ContentGenerationRepository.update_activity(
            db,
            existing,
            title=row["title"],
            activity_data=row["activity_data"],
        )


async def generate_contents(
    db: AsyncSession,
    course_plan_id: str,
    *,
    week_numbers: list[int] | None = None,
    content_types: list[str] | None = None,
    concurrency: int = 1,
    max_fix_attempts: int | None = None,
    emit_event: EmitEvent | None = None,
    record_trace: RecordTrace | None = None,
    additional_prompt: str = "",
    previous_version: str = "",
    revision_notes: str = "",
    include_assignment: bool = False,
    include_resources: bool = True,
    save: bool = True,
) -> list[WeekResult]:

    if concurrency < 1:
        raise ValueError("concurrency minimal 1")

    if content_types is not None:
        unknown = set(content_types) - set(GENERATION_SPECS)
        if unknown:
            raise ValueError(f"Jenis konten tidak dikenal: {sorted(unknown)}")

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

    # Hanya minggu dengan week_type yang punya jenis konten (regular, quiz, assignment).
    contexts = [ctx for ctx in contexts if _content_types_for(ctx)]

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
                f"Minggu tidak tersedia atau tipenya tidak mendukung pembuatan konten: "
                f"{sorted(invalid_weeks)}"
            )

        selected_weeks = set(week_numbers)

        contexts = [
            ctx
            for ctx in contexts
            if ctx.week_number in selected_weeks
        ]

    groups: list[tuple[WeekContext, list[str]]] = []

    for ctx in contexts:
        keys = list(
            _content_types_for(ctx, include_assignment)
            if content_types is None
            else [k for k in _available_content_types_for(ctx) if k in content_types]
        )

        # Materi memanggil prompt resource: resource dibuat dulu, hasilnya jadi bahan materi.
        if (
            content_types is None
            and include_resources
            and "LEARNING_MATERIAL" in keys
            and "RESOURCE" not in keys
        ):
            keys.insert(0, "RESOURCE")

        if keys:
            groups.append((ctx, keys))

    if not groups:
        raise ValueError(
            "Tidak ada minggu pembelajaran yang tersedia."
        )

    # Resource yang sudah tersimpan dipakai bila resource tidak dibuat ulang di proses ini
    # (mis. retry materi saja) atau pembuatannya gagal. Dibaca di sini, sebelum proses
    # paralel, karena satu AsyncSession tidak boleh dipakai bersamaan.
    saved_resources: dict[str, str] = {}

    for ctx, keys in groups:
        if "LEARNING_MATERIAL" not in keys:
            continue

        saved = await ContentGenerationRepository.get_by_week_id(
            db,
            ctx.course_plan_week_id,
            "RESOURCE",
        )

        if saved is not None:
            saved_resources[ctx.course_plan_week_id] = _learning_resources_text(
                saved.title,
                saved.content_data,
            )

    semaphore = asyncio.Semaphore(concurrency)

    async def run(
        ctx: WeekContext,
        key: str,
        learning_resources: str = "",
    ) -> WeekResult:
        async with semaphore:
            try:
                material = await _generate_week_content(
                    ctx,
                    content_type=key,
                    max_fix_attempts=max_fix_attempts,
                    emit_event=emit_event,
                    record_trace=record_trace,
                    additional_prompt=additional_prompt,
                    previous_version=previous_version,
                    revision_notes=revision_notes,
                    learning_resources=learning_resources,
                )

                return WeekResult(
                    ctx=ctx,
                    material=material,
                    content_type=key,
                )

            except ContentGenerationError as exc:
                logger.exception(
                    "Content generation failed for week %s (%s)",
                    ctx.week,
                    key,
                )

                return WeekResult(
                    ctx=ctx,
                    error=exc,
                    content_type=key,
                )

    async def run_group(ctx: WeekContext, keys: list[str]) -> list[WeekResult]:
        out: list[WeekResult] = []
        resources_text = saved_resources.get(ctx.course_plan_week_id, "")
        rest = list(keys)

        if "RESOURCE" in rest and "LEARNING_MATERIAL" in rest:
            rest.remove("RESOURCE")
            resource_result = await run(ctx, "RESOURCE")
            out.append(resource_result)

            if resource_result.material is not None:
                resources_text = _learning_resources_text(
                    resource_result.material.title,
                    resource_result.material.model_dump(
                        mode="json",
                        exclude={"title", "sub_cpmk_codes"},
                    ),
                )
            # gagal: materi tetap dibuat, memakai resource tersimpan (bila ada)

        out += await asyncio.gather(
            *(
                run(ctx, k, resources_text if k == "LEARNING_MATERIAL" else "")
                for k in rest
            )
        )
        return out

    grouped = await asyncio.gather(
        *(run_group(ctx, keys) for ctx, keys in groups)
    )
    results = [r for group in grouped for r in group]

    if save:
        for r in results:
            if r.material is None:
                continue

            try:
                await _save_result(db, r)
                await db.commit()

            except ContentGenerationError as exc:
                r.material = None
                r.error = exc

            except SQLAlchemyError:
                await db.rollback()

                logger.exception(
                    "Gagal menyimpan minggu %s (%s)",
                    r.ctx.week,
                    r.content_type,
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
    content_type: str | None = None,
    max_fix_attempts: int | None = None,
    emit_event: EmitEvent | None = None,
    record_trace: RecordTrace | None = None,
    additional_prompt: str = "",
) -> BaseModel:

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

    allowed = _available_content_types_for(ctx)

    if not allowed:
        raise ContentGenerationError(
            f"Week {week_number} bertipe '{ctx.week_data.week_type}' "
            f"dan tidak mendukung pembuatan konten."
        )

    if content_type is None:
        content_type = _content_types_for(ctx)[0]
    elif content_type not in allowed:
        raise ContentGenerationError(
            f"Week {week_number} bertipe '{ctx.week_data.week_type}' "
            f"dan tidak bisa menghasilkan {content_type}."
        )

    return await _generate_week_content(
        ctx,
        content_type=content_type,
        max_fix_attempts=max_fix_attempts,
        emit_event=emit_event,
        record_trace=record_trace,
        additional_prompt=additional_prompt,
    )
