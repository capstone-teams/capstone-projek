"""Error domain review konten (BE-19.2).

Pola kontrak publiknya sama dengan modul domain lain: ``error_code`` pada
envelope error (design-api §18), ``status_code`` HTTP, ``public_message`` yang
aman dikirim ke client, dan ``log_message`` untuk log server-side.
"""

from __future__ import annotations

__all__ = [
    "ContentDomainError",
    "ContentGenerationFailedError",
    "ContentNotFoundError",
    "ContentStateError",
    "ContentValidationError",
]


class ContentDomainError(Exception):
    """Base error domain konten hasil generation."""

    error_code = "INTERNAL_ERROR"
    status_code = 500
    public_message = "Permintaan konten gagal."

    def __init__(self, log_message: str | None = None) -> None:
        self.log_message = log_message or type(self).__name__
        super().__init__(self.log_message)


class ContentNotFoundError(ContentDomainError):
    """Konten tidak ada, atau workflow induknya bukan milik peminta."""

    error_code = "RESOURCE_NOT_FOUND"
    status_code = 404
    public_message = "Konten tidak ditemukan."

    def __init__(self, identifier: object) -> None:
        self.identifier = identifier
        super().__init__(f"konten {identifier} tidak ditemukan")


class ContentValidationError(ContentDomainError):
    """Nilai input tidak memenuhi aturan review (HTTP 422)."""

    error_code = "INVALID_REQUEST"
    status_code = 422
    public_message = "Data konten tidak valid."

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


class ContentGenerationFailedError(ContentDomainError):
    """Seluruh konten pada satu run gagal dihasilkan setelah batas retry."""

    error_code = "LLM_GENERATION_FAILED"
    status_code = 500
    public_message = "Konten gagal dihasilkan. Coba generate ulang."

    def __init__(self, log_message: str) -> None:
        super().__init__(log_message)


class ContentStateError(ContentDomainError):
    """Status konten tidak mengizinkan keputusan yang diminta (HTTP 409)."""

    error_code = "INVALID_REQUEST"
    status_code = 409
    public_message = "Status konten tidak mengizinkan operasi ini."

    def __init__(self, message: str, *, public_message: str | None = None) -> None:
        self.message = message
        if public_message is not None:
            self.public_message = public_message
        super().__init__(message)
