from __future__ import annotations

from typing import Any


class MoodleError(Exception):
    """Base class for every error raised by the Moodle client."""

    error_type: str = "moodle_error"
    retryable: bool = False

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        http_status: int | None = None,
        wsfunction: str | None = None,
        retryable: bool | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status = http_status
        self.wsfunction = wsfunction
        if retryable is not None:
            self.retryable = retryable

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation for API responses and events."""
        return {
            "error": self.error_type,
            "message": self.message,
            "code": self.code,
            "wsfunction": self.wsfunction,
            "http_status": self.http_status,
            "retryable": self.retryable,
        }


class MoodleAuthenticationError(MoodleError):
    """Token is invalid, expired, or the Moodle user cannot log in."""

    error_type = "authentication_error"
    retryable = False


class MoodlePermissionError(MoodleError):
    """Token is valid but the function or capability is not allowed."""

    error_type = "permission_error"
    retryable = False


class MoodleConnectionError(MoodleError):
    """Moodle could not be reached (DNS, refused connection, network drop)."""

    error_type = "connection_error"
    retryable = True


class MoodleTimeoutError(MoodleError):
    """Moodle did not respond within the configured timeout."""

    error_type = "timeout"
    retryable = True


class MoodleAPIError(MoodleError):
    """Moodle responded, but the operation failed or the response is unusable."""

    error_type = "api_error"
    retryable = False