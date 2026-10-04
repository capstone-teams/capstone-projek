from __future__ import annotations

import enum
from typing import Any


class MoodleErrorCategory(str, enum.Enum):
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    VALIDATION = "validation"
    TRANSIENT = "transient"
    EXECUTION = "execution"


class MoodleIntegrationError(Exception):
    pass


class MoodleEntityNotFoundError(MoodleIntegrationError):
    pass


class MoodleOperationFailedError(MoodleIntegrationError):
    category = MoodleErrorCategory.EXECUTION
    retryable = False

    def __init__(self, message: str, *, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error

    @property
    def code(self) -> str | None:
        return getattr(self.original_error, "code", None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.category.value,
            "message": str(self),
            "code": self.code,
            "retryable": self.retryable,
        }


class MoodleAuthenticationFailedError(MoodleOperationFailedError):
    category = MoodleErrorCategory.AUTHENTICATION


class MoodlePermissionDeniedError(MoodleOperationFailedError):
    category = MoodleErrorCategory.PERMISSION


class MoodleValidationFailedError(MoodleOperationFailedError):
    category = MoodleErrorCategory.VALIDATION


class MoodleTransientError(MoodleOperationFailedError):
    category = MoodleErrorCategory.TRANSIENT
    retryable = True


class MoodleCapabilityUnavailableError(MoodleIntegrationError):
    def __init__(self, operation: str):
        super().__init__(
            f"Operasi '{operation}' belum tersedia pada Moodle yang terhubung "
            "(lihat moodle-integration-contract.md)."
        )
        self.operation = operation