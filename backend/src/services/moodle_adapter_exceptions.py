from __future__ import annotations


class MoodleIntegrationError(Exception):
    pass


class MoodleEntityNotFoundError(MoodleIntegrationError):
    pass


class MoodleOperationFailedError(MoodleIntegrationError):
    def __init__(self, message: str, *, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error


class MoodleCapabilityUnavailableError(MoodleIntegrationError):
    def __init__(self, operation: str):
        super().__init__(
            f"Operasi '{operation}' belum tersedia pada Moodle yang terhubung "
            "(lihat moodle-integration-contract.md)."
        )
        self.operation = operation