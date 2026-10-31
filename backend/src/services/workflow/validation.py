"""Validasi dan normalisasi atribut workflow (BE-11.1).

Seluruh fungsi di sini murni: tanpa I/O, tanpa database, dan tanpa framework
HTTP, sehingga aturan bentuk workflow dapat diuji tanpa infrastruktur apa pun.
Batas panjang mengikuti tipe kolom pada ``src.models.workflow`` dan
``src.models.workflow_event`` supaya nilai yang lolos validasi domain tidak
ditolak oleh database.
"""

from __future__ import annotations

import json
import re
from datetime import datetime

from src.models.base import ID_LENGTH
from src.models.workflow import WorkflowStatus
from src.services.user.validation import SHORTUUID_ALPHABET
from src.services.workflow.errors import WorkflowValidationError

__all__ = [
    "MAX_EVENT_NAME_LENGTH",
    "MAX_MESSAGE_LENGTH",
    "normalize_event_name",
    "normalize_identifier",
    "normalize_message",
    "normalize_metadata",
    "normalize_moodle_course_id",
    "normalize_status",
    "normalize_timestamp",
]

MAX_EVENT_NAME_LENGTH = 100
MAX_MESSAGE_LENGTH = 2000

# Nama event publik selalu berpola ``WORKFLOW_*`` (design-api §17), sehingga
# client dapat memakai satu parser untuk riwayat HTTP dan frame WebSocket.
_EVENT_NAME_PATTERN = re.compile(r"^WORKFLOW_[A-Z0-9_]+$")


def normalize_identifier(value: object) -> str | None:
    """Validasi identifier ShortUUID yang belum tentu tersedia.

    ``None`` untuk workflow yang belum dipersist, karena identifier dibentuk
    oleh database foundation (BE-02). Identifier yang tidak berbentuk ShortUUID
    ditolak supaya nilai cacat tidak pernah sampai ke query database.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise WorkflowValidationError("id", "harus berupa teks atau None")

    identifier = value.strip()
    if len(identifier) != ID_LENGTH or any(
        char not in SHORTUUID_ALPHABET for char in identifier
    ):
        raise WorkflowValidationError(
            "id", f"bukan ShortUUID {ID_LENGTH} karakter yang valid: {value!r}"
        )
    return identifier


def normalize_status(value: object) -> WorkflowStatus:
    """Pastikan status hanya berisi nilai yang telah didefinisikan."""
    if isinstance(value, WorkflowStatus):
        return value
    if isinstance(value, str):
        try:
            return WorkflowStatus(value.strip().upper())
        except ValueError:
            pass

    valid_values = ", ".join(member.value for member in WorkflowStatus)
    raise WorkflowValidationError(
        "status", f"nilai tidak dikenal: {value!r}; nilai valid: {valid_values}"
    )


def normalize_timestamp(value: object, field: str) -> datetime | None:
    """Timestamp lifecycle harus berupa ``datetime`` atau ``None``."""
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise WorkflowValidationError(field, "harus berupa datetime atau None")
    return value


def normalize_moodle_course_id(value: object) -> int | None:
    """Course target Moodle berupa identifier positif; ``None`` mengosongkannya."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorkflowValidationError(
            "moodle_course_id", "harus berupa bilangan bulat atau None"
        )
    if value < 1:
        raise WorkflowValidationError(
            "moodle_course_id", "harus lebih besar dari 0"
        )
    return value


def normalize_event_name(value: object) -> str:
    """Nama event publik wajib berpola ``WORKFLOW_*`` dan pendek."""
    if not isinstance(value, str):
        raise WorkflowValidationError("event", "harus berupa teks")
    event = value.strip()
    if not _EVENT_NAME_PATTERN.fullmatch(event):
        raise WorkflowValidationError(
            "event", "harus berpola WORKFLOW_<NAMA> dengan huruf besar"
        )
    if len(event) > MAX_EVENT_NAME_LENGTH:
        raise WorkflowValidationError(
            "event", f"maksimal {MAX_EVENT_NAME_LENGTH} karakter"
        )
    return event


def normalize_message(value: object) -> str | None:
    """Pesan event adalah ringkasan aman ditampilkan, bukan detail internal."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise WorkflowValidationError("message", "harus berupa teks atau None")
    message = value.strip()
    if not message:
        return None
    return message[:MAX_MESSAGE_LENGTH]


def normalize_metadata(value: object) -> dict | None:
    """Metadata event harus berupa object JSON (bukan teks/daftar bebas).

    Nilai divalidasi dapat diserialisasi JSON di sini — bukan saat insert —
    supaya metadata yang tidak dapat disimpan gagal sebelum menyentuh database.
    """
    if value is None:
        return None
    if not isinstance(value, dict):
        raise WorkflowValidationError(
            "metadata", "harus berupa object JSON atau None"
        )
    if not value:
        return None
    try:
        json.dumps(value)
    except (TypeError, ValueError) as exc:
        raise WorkflowValidationError(
            "metadata", "harus berisi nilai yang dapat diserialisasi JSON"
        ) from exc
    return value
