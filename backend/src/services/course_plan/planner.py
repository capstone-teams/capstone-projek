"""Course Planning Service: kontrak dan adapter LLM (BE-14.3).

Orkestrator tidak memanggil model secara langsung. Ia meminta satu perencanaan
lewat :class:`CoursePlanner`, menerima ``CoursePlanOutput`` yang sudah lolos
validasi skema, lalu menyimpannya sebagai versi baru (BE-14.1) setelah validasi
akademik (``validation.validate_plan``).

Pemisahan ini adalah titik integrasi BE-15.3: implementasi penuh Course
Planning Service (prompt, validasi akademik, retry dengan temuan) dapat
menggantikan :class:`LLMCoursePlanner` tanpa mengubah orkestrator, endpoint,
maupun penyimpanan. Adapter di sini sengaja minimal: satu prompt
``course_planning/v1`` dengan structured output dan retry schema.

Mode regenerasi memakai konteks yang sama ditambah versi sebelumnya, catatan
penolakan terakhir, dan instruksi dosen — sehingga agent memperbaiki rencana
yang ada, bukan menyusun dari nol (issue BE-14.3).

Retry tidak hanya untuk output yang salah schema: aturan akademik
(:func:`~src.services.course_plan.validation.validate_plan`) ikut diperiksa di
sini dan temuannya dikirim balik ke model, karena prompt sudah mewajibkan
cakupan Sub-CPMK dan minggu RPS. Tanpa itu model hanya punya satu kesempatan
memenuhi aturan yang tidak dapat ia periksa sendiri, sehingga rencana dapat
tersimpan tidak dapat disetujui meskipun penyedia berhasil.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from pydantic import ValidationError

from src.config.settings import get_settings
from src.schemas.course_plan import CoursePlanOutput
from src.services.course_plan.errors import CoursePlanGenerationError
from src.services.course_plan.validation import validate_plan
from src.services.llm import LLMService
from src.services.llm.base import LLMInvalidOutputError, LLMProviderError
from src.services.llm.structured_output import make_openai_strict_schema

__all__ = [
    "COURSE_PLAN_PROMPT_VERSION",
    "CoursePlanner",
    "LLMCoursePlanner",
    "PlanningEvent",
    "PlanningRequest",
    "PlannedCoursePlan",
    "get_course_planner",
]

logger = logging.getLogger(__name__)

PROMPT_NAME = "course_planning"
PROMPT_VERSION = "v1"
COURSE_PLAN_PROMPT_VERSION = f"{PROMPT_NAME}/{PROMPT_VERSION}"

#: Jumlah temuan validasi yang dikirim balik ke model pada percobaan ulang.
MAX_FEEDBACK_ITEMS = 5


class PlanningEvent(StrEnum):
    """Event internal perencanaan; orkestrator memetakannya ke WorkflowEvent."""

    LLM_CALLING = "LLM_CALLING"
    LLM_RESPONDED = "LLM_RESPONDED"
    VALIDATING = "VALIDATING"
    RETRY_FIX = "RETRY_FIX"
    PLANNING_COMPLETED = "PLANNING_COMPLETED"
    PLANNING_FAILED = "PLANNING_FAILED"


EmitPlanningEvent = Callable[..., Awaitable[None]]


@dataclass(frozen=True, kw_only=True)
class PlanningRequest:
    """Konteks yang dikirim ke Course Planning Service.

    ``previous_plan``, ``revision_notes``, dan ``instruction`` kosong pada
    generasi pertama. ``instructor_context`` sudah membawa
    ``activity_configuration`` (BE-10.3), dan ``rps_structured`` adalah RPS
    Structured Data (BE-08.1) — satu-satunya sumber fakta akademik.
    """

    rps_structured: dict = field(default_factory=dict)
    instructor_context: dict = field(default_factory=dict)
    activity_configuration: dict = field(default_factory=dict)
    previous_plan: dict | None = None
    revision_notes: str | None = None
    instruction: str | None = None


@dataclass(frozen=True, kw_only=True)
class PlannedCoursePlan:
    """Hasil satu perencanaan yang siap divalidasi dan disimpan."""

    output: CoursePlanOutput
    prompt_version: str = COURSE_PLAN_PROMPT_VERSION
    model_name: str | None = None
    attempts: int = 1


class CoursePlanner(Protocol):
    """Kontrak Course Planning Service yang dipakai orkestrator."""

    async def generate(
        self,
        request: PlanningRequest,
        *,
        emit_event: EmitPlanningEvent | None = None,
    ) -> PlannedCoursePlan: ...


class LLMCoursePlanner:
    """Adapter LLM minimal untuk course planning (lihat catatan modul)."""

    def __init__(
        self,
        *,
        service: LLMService | None = None,
        max_fix_attempts: int | None = None,
    ) -> None:
        self._service = service or LLMService()
        attempts = (
            get_settings().COURSE_PLANNING_MAX_FIX_ATTEMPTS
            if max_fix_attempts is None
            else max_fix_attempts
        )
        if attempts < 0:
            raise ValueError("max_fix_attempts tidak boleh negatif")
        self._max_fix_attempts = attempts
        self._output_schema = make_openai_strict_schema(
            CoursePlanOutput.model_json_schema()
        )

    async def generate(
        self,
        request: PlanningRequest,
        *,
        emit_event: EmitPlanningEvent | None = None,
    ) -> PlannedCoursePlan:
        total = self._max_fix_attempts + 1
        feedback = "Tidak ada temuan validasi."

        for attempt in range(1, total + 1):
            await _emit(
                emit_event,
                PlanningEvent.LLM_CALLING,
                "Menyusun rencana pembelajaran.",
                attempt=attempt,
            )

            try:
                result = await self._service.execute_prompt(
                    prompt_name=PROMPT_NAME,
                    version=PROMPT_VERSION,
                    variables=_prompt_variables(request, feedback),
                    output_schema=self._output_schema,
                )
            except LLMInvalidOutputError as exc:
                # Output bukan JSON adalah kegagalan schema: masih dapat
                # diperbaiki dengan percobaan berikutnya, bukan kegagalan
                # penyedia yang tidak dapat dipulihkan.
                feedback = f"Output bukan JSON yang valid: {exc}"
                if attempt < total:
                    await _emit(
                        emit_event,
                        PlanningEvent.RETRY_FIX,
                        "Output bukan JSON; memperbaiki.",
                        attempt=attempt,
                        reason_code="OUTPUT_NOT_JSON",
                        details=[feedback],
                    )
                    continue
                await _emit(
                    emit_event,
                    PlanningEvent.PLANNING_FAILED,
                    "Output model bukan JSON.",
                    attempt=attempt,
                    reason_code="OUTPUT_NOT_JSON",
                )
                raise CoursePlanGenerationError(
                    f"output bukan JSON setelah {total} percobaan"
                ) from exc
            except LLMProviderError as exc:
                await _emit(
                    emit_event,
                    PlanningEvent.PLANNING_FAILED,
                    "Penyedia model gagal menyusun rencana.",
                    attempt=attempt,
                    reason_code="LLM_PROVIDER_ERROR",
                )
                raise CoursePlanGenerationError(
                    f"provider gagal pada percobaan {attempt}: {exc}"
                ) from exc

            await _emit(
                emit_event,
                PlanningEvent.LLM_RESPONDED,
                "Respons model diterima.",
                attempt=attempt,
            )
            await _emit(
                emit_event,
                PlanningEvent.VALIDATING,
                "Memvalidasi struktur course plan.",
                attempt=attempt,
            )

            try:
                raw = result.data
                if isinstance(raw, str):
                    raw = json.loads(raw)
                output = CoursePlanOutput.model_validate(raw)
            except (ValidationError, json.JSONDecodeError, TypeError) as exc:
                detail = _validation_feedback(exc)
                if attempt < total:
                    feedback = detail
                    await _emit(
                        emit_event,
                        PlanningEvent.RETRY_FIX,
                        "Hasil tidak sesuai schema; memperbaiki.",
                        attempt=attempt,
                        reason_code="SCHEMA_VALIDATION_FAILED",
                        details=detail.splitlines(),
                    )
                    continue

                await _emit(
                    emit_event,
                    PlanningEvent.PLANNING_FAILED,
                    "Hasil model tidak sesuai schema.",
                    attempt=attempt,
                    reason_code="SCHEMA_VALIDATION_FAILED",
                )
                raise CoursePlanGenerationError(
                    f"output tidak valid setelah {total} percobaan: {detail}"
                ) from exc

            # Aturan akademik (cakupan Sub-CPMK, minggu RPS, minggu ujian,
            # aktivitas) tidak dapat diperiksa model sendiri. Beri kesempatan
            # perbaikan selama jatah percobaan masih ada; pada percobaan
            # terakhir rencana tetap dikembalikan agar dosen dapat melihat
            # temuannya dan meminta regenerasi (BE-14.2).
            issues = validate_plan(
                output,
                rps_structured=request.rps_structured,
                activity_configuration=request.activity_configuration,
            )["issues"]
            if issues and attempt < total:
                feedback = _issue_feedback(issues)
                await _emit(
                    emit_event,
                    PlanningEvent.RETRY_FIX,
                    "Rencana belum memenuhi aturan akademik; memperbaiki.",
                    attempt=attempt,
                    reason_code="VALIDATION_FAILED",
                    details=feedback.splitlines(),
                )
                continue

            await _emit(
                emit_event,
                PlanningEvent.PLANNING_COMPLETED,
                "Course plan tersusun.",
                attempt=attempt,
            )
            return PlannedCoursePlan(
                output=output,
                prompt_version=COURSE_PLAN_PROMPT_VERSION,
                model_name=self._service.model,
                attempts=attempt,
            )

        # Loop selalu kembali atau melempar; baris ini hanya jaring pengaman.
        raise CoursePlanGenerationError("perencanaan tidak menghasilkan output")


def get_course_planner() -> CoursePlanner:
    """Planner bawaan; dapat diganti pengujian/dependency override."""
    return LLMCoursePlanner()


def _prompt_variables(request: PlanningRequest, feedback: str) -> dict[str, str]:
    """Siapkan variabel template prompt (semua nilai berupa teks)."""

    def dump(value: object) -> str:
        return json.dumps(value, ensure_ascii=False, indent=2)

    return {
        "rps_structured": dump(request.rps_structured),
        "instructor_context": dump(request.instructor_context),
        "activity_configuration": dump(request.activity_configuration),
        "previous_plan": (
            dump(request.previous_plan)
            if request.previous_plan
            else "Tidak ada versi sebelumnya."
        ),
        "revision_notes": request.revision_notes or "Tidak ada catatan penolakan.",
        "instruction": request.instruction or "Tidak ada instruksi tambahan.",
        "validation_feedback": feedback,
    }


def _issue_feedback(issues: list[dict]) -> str:
    """Ringkas temuan validasi akademik menjadi umpan balik untuk model."""
    lines = [
        f"- {issue['code']}: {issue['message']}" for issue in issues[:MAX_FEEDBACK_ITEMS]
    ]
    extra = len(issues) - MAX_FEEDBACK_ITEMS
    if extra > 0:
        lines.append(f"... dan {extra} temuan lain")
    return "Perbaiki rencana agar memenuhi aturan berikut:\n" + "\n".join(lines)


def _validation_feedback(exc: Exception) -> str:
    """Ringkas kegagalan schema menjadi umpan balik singkat untuk model."""
    if isinstance(exc, ValidationError):
        lines = [
            f"- {'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()[:MAX_FEEDBACK_ITEMS]
        ]
        return "Perbaiki field berikut agar sesuai schema:\n" + "\n".join(lines)
    return f"Output bukan JSON yang valid: {exc}"


async def _emit(
    emit_event: EmitPlanningEvent | None,
    event: PlanningEvent,
    message: str,
    **data: object,
) -> None:
    """Terbitkan event bila pemanggil menyediakannya; kegagalan event ditelan.

    Kegagalan pencatatan event tidak boleh menggagalkan perencanaan yang sedang
    berjalan — sama seperti kontrak emitter pada service analisis RPS.
    """
    if emit_event is None:
        return
    try:
        await emit_event(event=event.value, message=message, **data)
    except Exception:  # noqa: BLE001 - pencatatan event tidak boleh mematikan tahap
        logger.warning("gagal menerbitkan event perencanaan %s", event.value)
