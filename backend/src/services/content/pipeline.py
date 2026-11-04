from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from pydantic import ValidationError

logger = logging.getLogger(__name__)

MAX_ERROR_CHARS = 2000
MAX_PREVIOUS_OUTPUT_CHARS = 6000
MAX_DETAIL_ITEMS = 5

EmitEvent = Callable[..., Awaitable[None]]
RecordTrace = Callable[..., Awaitable[None]]

DEFAULT_CLOSING = (
    "Perbaiki hanya bagian yang salah agar sesuai schema. "
    "Jangan menambah atau mengarang informasi yang tidak ada pada RPS."
)


async def emit(emit_event: EmitEvent | None, event_type: Any, **data: Any) -> None:
    """Kirim event progres. Kegagalan emit tidak boleh menggagalkan proses."""
    logger.info("event=%s", event_type.value)
    if emit_event is None:
        return
    try:
        await emit_event(event_type=event_type, message=event_type.value, **data)
    except Exception:
        logger.exception("Gagal mengirim event %s", event_type.value)


async def trace(record_trace: RecordTrace | None, **fields: Any) -> None:
    """Catat jejak satu percobaan. Kegagalan pencatatan tidak boleh menggagalkan proses."""
    level = logging.INFO if fields.get("validation") == "success" else logging.WARNING
    logger.log(level, "trace %s", fields)
    if record_trace is None:
        return
    try:
        await record_trace(**fields)
    except Exception:
        logger.exception("Gagal menyimpan trace percobaan %s", fields.get("attempt"))


def explain_validation_error(exc: ValidationError) -> list[str]:
    """Daftar singkat 'lokasi: pesan'. Tanpa nilai input."""
    errors = exc.errors()
    items = [
        f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
        for err in errors[:MAX_DETAIL_ITEMS]
    ]
    extra = len(errors) - MAX_DETAIL_ITEMS
    if extra > 0:
        items.append(f"... dan {extra} kesalahan lain")
    return items



def classify_provider_error(exc: Exception) -> tuple[str, str]:
    """Klasifikasikan error provider tanpa membocorkan informasi sensitif."""

    name = type(exc).__name__.lower()
    message = str(exc).lower()

    if isinstance(exc, TimeoutError) or "timeout" in name:
        return (
            "PROVIDER_TIMEOUT",
            "Layanan model tidak merespons tepat waktu.",
        )

    if "ratelimit" in name or "rate limit" in message:
        return (
            "PROVIDER_RATE_LIMIT",
            "Layanan model sedang membatasi permintaan.",
        )

    if "authentication" in name or "permissiondenied" in name:
        return (
            "PROVIDER_AUTH_ERROR",
            "Autentikasi atau izin akses layanan model gagal.",
        )

    if "badrequest" in name:
        return (
            "PROVIDER_BAD_REQUEST",
            "Permintaan ke layanan model tidak valid.",
        )

    if "connection" in name or "connect" in name:
        return (
            "PROVIDER_CONNECTION_ERROR",
            "Tidak dapat terhubung ke layanan model.",
        )

    if "internalserver" in name or "servererror" in name:
        return (
            "PROVIDER_SERVER_ERROR",
            "Layanan model mengalami gangguan internal.",
        )

    if "apierror" in name:
        return (
            "PROVIDER_API_ERROR",
            "Layanan model mengembalikan kesalahan API.",
        )

    return (
        "PROVIDER_ERROR",
        "Terjadi kesalahan pada layanan model.",
    )


def build_feedback(
    details: list[str],
    raw_text: str | None,
    closing: str = DEFAULT_CLOSING,
) -> str:
    """Pesan perbaikan untuk percobaan berikutnya (${validation_feedback})."""
    lines = ["Output sebelumnya tidak valid terhadap schema:"]
    if details:
        lines.extend(f"- {d}" for d in details)
    else:
        lines.append("- Output bukan JSON yang valid.")
    if raw_text:
        lines += ["", "Output sebelumnya (dipotong):", raw_text[:MAX_PREVIOUS_OUTPUT_CHARS]]
    lines += ["", closing]
    return "\n".join(lines)
