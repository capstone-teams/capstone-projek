from __future__ import annotations


class MoodleIntegrationError(Exception):
    pass


class MoodleEntityNotFoundError(MoodleIntegrationError):
    pass


class MoodleOperationFailedError(MoodleIntegrationError):
    def __init__(self, message: str, *, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error