from __future__ import annotations

from src.services.moodle_adapter_exceptions import (
    MoodleAuthenticationFailedError,
    MoodleOperationFailedError,
    MoodlePermissionDeniedError,
    MoodleTransientError,
    MoodleValidationFailedError,
)
from src.services.moodle_exceptions import (
    MoodleAuthenticationError,
    MoodleError,
    MoodlePermissionError,
)

VALIDATION_ERROR_CODES = frozenset(
    {
        "invalidparameter",
        "invalidrecord",
        "missingparam",
        "shortnametaken",
        "invalidcoursedata",
    }
)


def normalize_moodle_error(error: MoodleError, wsfunction: str) -> MoodleOperationFailedError:
    message = f"Operasi Moodle '{wsfunction}' gagal: {error.message}"
    if isinstance(error, MoodleAuthenticationError):
        error_class = MoodleAuthenticationFailedError
    elif isinstance(error, MoodlePermissionError):
        error_class = MoodlePermissionDeniedError
    elif error.retryable:
        error_class = MoodleTransientError
    elif error.code in VALIDATION_ERROR_CODES:
        error_class = MoodleValidationFailedError
    else:
        error_class = MoodleOperationFailedError
    return error_class(message, original_error=error)