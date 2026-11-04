"""RPS Analysis Service (BE-09.2).

Mengirim YAML RPS ke LLM (via BE-07.2) dengan structured output, memvalidasi
hasilnya dengan RPSStructuredData (BE-05.3), dan mengulang percobaan bila
validasi gagal. Setiap tahap melaporkan event progres (BE-11) dan setiap
percobaan dicatat sebagai trace.

CATATAN INTEGRASI (sesuaikan dengan proyek):
- path import `settings` (property `rps_analysis_max_fix_attempts`)
- signature `LLMService.execute_prompt` dan atribut `result.*`
- signature `emit_event` (BE-11) dan `record_trace` (penyimpanan trace)
- template prompt `rps_analysis/v1` harus memiliki placeholder
  `${validation_feedback}` agar retry benar-benar membawa pesan error.
"""

from __future__ import annotations

import json
import logging
import time
from enum import StrEnum
from typing import Any, Awaitable, Callable

import yaml
from pydantic import ValidationError

from src.config import settings  # sesuaikan path
from src.schemas.rps_structured import RPSStructuredData
from src.services.analysis.schema import RPS_OUTPUT_SCHEMA
from src.services.llm import LLMService, OpenAIProvider

logger = logging.getLogger(__name__)

PROMPT_NAME = "rps_analysis"
PROMPT_VERSION = "v1"

MAX_ERROR_CHARS = 2000
MAX_PREVIOUS_OUTPUT_CHARS = 6000
MAX_DETAIL_ITEMS = 5

EmitEvent = Callable[..., Awaitable[None]]
RecordTrace = Callable[..., Awaitable[None]]


class RPSEvent(StrEnum):
    """Tahap analisis RPS. Nilainya sudah berupa teks manusiawi."""

    ANALYSIS_STARTED = "Memulai analisis"
    YAML_PARSING = "Membaca struktur YAML"
    YAML_PARSED = "YAML terbaca"
    LLM_CALLING = "Mengirim ke model"
    LLM_RESPONDED = "Respons model diterima"
    VALIDATING = "Memvalidasi hasil"
    RETRY_FIX = "Memperbaiki hasil"
    ANALYSIS_COMPLETED = "Analisis selesai"
    ANALYSIS_FAILED = "Analisis gagal"


class RPSAnalysisError(Exception):
    """Analisis RPS gagal setelah seluruh percobaan atau karena error provider."""

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


# --------------------------------------------------------------------------
# Helper: event, trace, konfigurasi
# --------------------------------------------------------------------------


def _default_max_fix_attempts() -> int:
    # Nilai bawaan (2) berada di config.py: DEFAULT_RPS_ANALYSIS_MAX_FIX_ATTEMPTS.
    return settings.rps_analysis_max_fix_attempts


async def _emit(
    emit_event: EmitEvent | None,
    event_type: RPSEvent,
    message: str,
    **data: Any,
) -> None:
    """Kirim event progres. Kegagalan emit tidak boleh menggagalkan analisis."""
    logger.info("RPS analysis event=%s message=%s", event_type.value, message)
    if emit_event is None:
        return
    try:
        await emit_event(event_type=event_type, message=message, **data)
    except Exception:
        logger.exception("Gagal mengirim event %s", event_type.value)


async def _trace(record_trace: RecordTrace | None, **fields: Any) -> None:
    """Catat jejak satu percobaan. Kegagalan pencatatan tidak boleh menggagalkan analisis."""
    level = logging.INFO if fields.get("validation") == "success" else logging.WARNING
    logger.log(level, "RPS analysis trace %s", fields)
    if record_trace is None:
        return
    try:
        await record_trace(**fields)
    except Exception:
        logger.exception("Gagal menyimpan trace percobaan %s", fields.get("attempt"))


# --------------------------------------------------------------------------
# Helper: YAML
# --------------------------------------------------------------------------


def _summarize_yaml(rps_yaml: str) -> str:
    """Parse YAML dan buat ringkasan struktur. Murni kode, tanpa LLM."""
    try:
        data = yaml.safe_load(rps_yaml)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        lokasi = f" (baris {mark.line + 1}, kolom {mark.column + 1})" if mark else ""
        raise ValueError(f"Struktur YAML tidak valid{lokasi}.") from exc

    if not isinstance(data, dict):
        raise ValueError("Struktur YAML tidak valid: isi harus berupa pasangan key-value.")

    weeks = sum(
        len(item.get("weeks") or [])
        for item in (data.get("weekly_plan") or [])
        if isinstance(item, dict)
    )
    return (
        f"{weeks} minggu, {len(data.get('cpmk') or [])} CPMK, "
        f"{len(data.get('assessments') or [])} komponen penilaian"
    )


# --------------------------------------------------------------------------
# Helper: klasifikasi kegagalan
# --------------------------------------------------------------------------


def _explain_validation_error(exc: ValidationError) -> list[str]:
    """Daftar singkat 'lokasi: pesan'. Tanpa nilai input agar isi dokumen tidak bocor."""
    errors = exc.errors()
    items = [
        f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
        for err in errors[:MAX_DETAIL_ITEMS]
    ]
    extra = len(errors) - MAX_DETAIL_ITEMS
    if extra > 0:
        items.append(f"... dan {extra} kesalahan lain")
    return items


def _classify_provider_error(exc: Exception) -> tuple[str, str]:
    name = type(exc).__name__.lower()
    if isinstance(exc, TimeoutError) or "timeout" in name:
        return "PROVIDER_TIMEOUT", "Layanan model tidak merespons tepat waktu."
    if "ratelimit" in name:
        return "PROVIDER_RATE_LIMIT", "Layanan model sedang membatasi permintaan."
    return "PROVIDER_ERROR", "Terjadi kesalahan pada layanan model."


def _build_feedback(details: list[str], raw_text: str | None) -> str:
    """Pesan perbaikan untuk percobaan berikutnya (placeholder ${validation_feedback})."""
    lines = ["Output sebelumnya tidak valid terhadap schema:"]
    if details:
        lines.extend(f"- {d}" for d in details)
    else:
        lines.append("- Output bukan JSON yang valid.")
    if raw_text:
        lines.append("")
        lines.append("Output sebelumnya (dipotong):")
        lines.append(raw_text[:MAX_PREVIOUS_OUTPUT_CHARS])
    lines.append("")
    lines.append(
        "Perbaiki hanya bagian yang salah agar sesuai schema. "
        "Jangan menambah atau mengarang informasi yang tidak ada pada RPS."
    )
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Service utama
# --------------------------------------------------------------------------


async def analyze_rps(
    rps_yaml: str,
    max_fix_attempts: int | None = None,
    emit_event: EmitEvent | None = None,
    record_trace: RecordTrace | None = None,
    additional_prompt: str = "",
) -> RPSStructuredData:
    """Analisis RPS YAML dengan LLM dan validasi hasilnya.

    max_fix_attempts: jumlah retry tambahan setelah percobaan pertama
    (2 berarti maksimal 3 percobaan). Jika None, dibaca dari konfigurasi
    RPS_ANALYSIS_MAX_FIX_ATTEMPTS.

    Retry hanya untuk output tidak valid (bukan JSON / tidak sesuai schema).
    Error provider (timeout, rate limit, dsb.) langsung dilaporkan sebagai
    RPSAnalysisError tanpa retry.
    """
    if not rps_yaml or not rps_yaml.strip():
        raise ValueError("rps_yaml tidak boleh kosong")

    if max_fix_attempts is None:
        max_fix_attempts = _default_max_fix_attempts()
    if max_fix_attempts < 0:
        raise ValueError("max_fix_attempts tidak boleh negatif")

    total = max_fix_attempts + 1

    await _emit(emit_event, RPSEvent.ANALYSIS_STARTED, "Memulai analisis RPS")

    await _emit(
        emit_event,
        RPSEvent.YAML_PARSING,
        "Membaca dan memeriksa struktur YAML",
    )
    try:
        summary = _summarize_yaml(rps_yaml)
    except ValueError as exc:
        await _emit(
            emit_event,
            RPSEvent.ANALYSIS_FAILED,
            str(exc),
            reason_code="YAML_INVALID",
            details=[],
        )
        raise
    await _emit(emit_event, RPSEvent.YAML_PARSED, f"YAML terbaca: {summary}")

    provider = OpenAIProvider()
    service = LLMService(provider)

    feedback = ""
    last_code: str | None = None
    last_details: list[str] = []

    for attempt in range(1, total + 1):
        started = time.perf_counter()

        def elapsed_ms() -> float:
            return round((time.perf_counter() - started) * 1000, 2)

        await _emit(
            emit_event,
            RPSEvent.LLM_CALLING,
            f"Mengirim RPS ke model (percobaan {attempt}/{total})",
            attempt=attempt,
        )

        # 1) Panggilan LLM. Error provider tidak di-retry.
        try:
            result = await service.execute_prompt(
                prompt_name=PROMPT_NAME,
                version=PROMPT_VERSION,
                variables={
                    "rps_yaml": rps_yaml,
                    "additional_prompt": additional_prompt,
                    "validation_feedback": feedback,
                },
                output_schema=RPS_OUTPUT_SCHEMA,
            )
        except Exception as exc:
            code, message = _classify_provider_error(exc)
            await _trace(
                record_trace,
                attempt=attempt,
                prompt=f"{PROMPT_NAME}/{PROMPT_VERSION}",
                model=None,
                tokens_input=None,
                tokens_output=None,
                duration_ms=elapsed_ms(),
                validation="provider_error",
                reason_code=code,
                error=str(exc)[:MAX_ERROR_CHARS],
            )
            await _emit(
                emit_event,
                RPSEvent.ANALYSIS_FAILED,
                message,
                attempt=attempt,
                reason_code=code,
                details=[],
            )
            raise RPSAnalysisError(
                message, reason_code=code, attempts=attempt
            ) from exc

        model = getattr(provider, "model", None)
        tokens_in = getattr(getattr(result, "metadata", None), "prompt_tokens", None)
        tokens_out = getattr(getattr(result, "metadata", None), "completion_tokens", None)

        await _emit(
            emit_event,
            RPSEvent.LLM_RESPONDED,
            "Respons model diterima",
            attempt=attempt,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            duration_ms=elapsed_ms(),
        )

        # 2) Validasi output.
        await _emit(
            emit_event,
            RPSEvent.VALIDATING,
            "Memvalidasi hasil terhadap schema",
            attempt=attempt,
        )

        raw_text: str | None = None
        error_text = ""
        try:
            raw_output = result.data
            if isinstance(raw_output, str):
                raw_text = raw_output
                raw_output = json.loads(raw_output)
            else:
                raw_text = json.dumps(raw_output, ensure_ascii=False, default=str)
            rps_data = RPSStructuredData.model_validate(raw_output)
        except json.JSONDecodeError as exc:
            code = "OUTPUT_NOT_JSON"
            message = "Model mengembalikan format yang tidak dapat dibaca."
            details: list[str] = []
            error_text = str(exc)
        except ValidationError as exc:
            code = "SCHEMA_VALIDATION_FAILED"
            message = "Hasil model tidak sesuai schema."
            details = _explain_validation_error(exc)
            error_text = str(exc)
        else:
            await _trace(
                record_trace,
                attempt=attempt,
                prompt=f"{PROMPT_NAME}/{PROMPT_VERSION}",
                model=model,
                tokens_input=tokens_in,
                tokens_output=tokens_out,
                duration_ms=elapsed_ms(),
                validation="success",
                reason_code=None,
                error=None,
            )
            await _emit(
                emit_event,
                RPSEvent.ANALYSIS_COMPLETED,
                "Analisis selesai",
                attempt=attempt,
            )
            return rps_data

        # 3) Validasi gagal: catat, lalu retry bila masih ada jatah.
        last_code, last_details = code, details
        await _trace(
            record_trace,
            attempt=attempt,
            prompt=f"{PROMPT_NAME}/{PROMPT_VERSION}",
            model=model,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            duration_ms=elapsed_ms(),
            validation="failed",
            reason_code=code,
            error=error_text[:MAX_ERROR_CHARS],
        )

        if attempt < total:
            feedback = _build_feedback(details, raw_text)
            await _emit(
                emit_event,
                RPSEvent.RETRY_FIX,
                f"{message} Memperbaiki (percobaan {attempt}/{total}).",
                attempt=attempt,
                reason_code=code,
                details=details,
            )

    failure_message = f"Analisis RPS gagal setelah {total} percobaan."
    await _emit(
        emit_event,
        RPSEvent.ANALYSIS_FAILED,
        failure_message,
        attempt=total,
        reason_code=last_code,
        details=last_details,
    )
    raise RPSAnalysisError(
        failure_message,
        reason_code=last_code,
        details=last_details,
        attempts=total,
    )
