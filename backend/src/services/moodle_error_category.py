from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.services.moodle_adapter_exceptions import MoodleOperationFailedError
from src.services.moodle_exceptions import (
    MoodleAPIError,
    MoodleAuthenticationError,
    MoodleConnectionError,
    MoodlePermissionError,
    MoodleTimeoutError,
)

VALIDATION_ERROR_CODES = frozenset(
    {
        "invalidparameter",
        "invalid_parameter_exception",
        "shortnametaken",
        "invalidcourseid",
        "unknowncategory",
    }
)

TIMEOUT_STATUS_CODE = 504


class MoodleErrorCategory(str, Enum):
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    VALIDATION = "validation"
    TRANSIENT = "transient"
    EXECUTION = "execution"


_STATUS_CODES = {
    MoodleErrorCategory.AUTHENTICATION: 502,
    MoodleErrorCategory.PERMISSION: 502,
    MoodleErrorCategory.VALIDATION: 422,
    MoodleErrorCategory.TRANSIENT: 502,
    MoodleErrorCategory.EXECUTION: 502,
}

_PUBLIC_MESSAGES = {
    MoodleErrorCategory.AUTHENTICATION: "Backend tidak dapat melakukan autentikasi ke Moodle.",
    MoodleErrorCategory.PERMISSION: "Akun integrasi Moodle tidak memiliki izin untuk operasi ini.",
    MoodleErrorCategory.VALIDATION: "Moodle menolak data yang dikirim.",
    MoodleErrorCategory.TRANSIENT: "Moodle sementara tidak dapat dijangkau. Coba lagi beberapa saat.",
    MoodleErrorCategory.EXECUTION: "Operasi di Moodle gagal.",
}


@dataclass(frozen=True)
class NormalizedMoodleError:
    category: MoodleErrorCategory
    status_code: int
    message: str
    moodle_code: str | None
    retryable: bool


def normalize_moodle_error(exc: Exception) -> NormalizedMoodleError:
    root = _root_error(exc)
    category = _categorize(root)
    status_code = (
        TIMEOUT_STATUS_CODE if isinstance(root, MoodleTimeoutError) else _STATUS_CODES[category]
    )
    return NormalizedMoodleError(
        category=category,
        status_code=status_code,
        message=_PUBLIC_MESSAGES[category],
        moodle_code=getattr(root, "code", None),
        retryable=bool(getattr(root, "retryable", False)),
    )


def _root_error(exc: Exception) -> Exception:
    if isinstance(exc, MoodleOperationFailedError) and exc.original_error is not None:
        return exc.original_error
    return exc


def _categorize(root: Exception) -> MoodleErrorCategory:
    if isinstance(root, MoodleAuthenticationError):
        return MoodleErrorCategory.AUTHENTICATION
    if isinstance(root, MoodlePermissionError):
        return MoodleErrorCategory.PERMISSION
    if isinstance(root, (MoodleTimeoutError, MoodleConnectionError)) or getattr(
        root, "retryable", False
    ):
        return MoodleErrorCategory.TRANSIENT
    if isinstance(root, MoodleAPIError) and root.code in VALIDATION_ERROR_CODES:
        return MoodleErrorCategory.VALIDATION
    return MoodleErrorCategory.EXECUTION