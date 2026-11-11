"""Error domain Moodle verification (BE-21.2).

Turunan :class:`~src.services.execution.errors.ExecutionDomainError`, sehingga
dipetakan ke envelope error yang sama oleh handler yang sudah terdaftar
(``src/middlewares/error_handlers.py``). Penolakan prasyarat memakai
``INVALID_REQUEST`` dengan kode alasan pada ``details`` (``field`` = ``reason``),
sama seperti eksekusi.
"""

from __future__ import annotations

from src.services.execution.errors import ExecutionDomainError

__all__ = [
    "NO_EXECUTION_TO_VERIFY",
    "VERIFICATION_REASON_CODES",
    "VerificationNotFoundError",
    "VerificationPreconditionError",
]

#: Workflow belum memiliki eksekusi yang selesai untuk diverifikasi.
NO_EXECUTION_TO_VERIFY = "NO_EXECUTION_TO_VERIFY"

VERIFICATION_REASON_CODES = frozenset({NO_EXECUTION_TO_VERIFY})

_REASON_MESSAGES = {
    NO_EXECUTION_TO_VERIFY: "Belum ada eksekusi ke Moodle yang dapat diverifikasi.",
}


class VerificationNotFoundError(ExecutionDomainError):
    """Hasil verifikasi tidak ada **atau** bukan milik workflow dosen peminta."""

    error_code = "RESOURCE_NOT_FOUND"
    status_code = 404
    public_message = "Hasil verifikasi tidak ditemukan."

    def __init__(self, identifier: object) -> None:
        self.identifier = identifier
        super().__init__(f"hasil verifikasi tidak ditemukan: {identifier}")


class VerificationPreconditionError(ExecutionDomainError):
    """Prasyarat verifikasi tidak terpenuhi (HTTP 409, kode alasan stabil)."""

    error_code = "INVALID_REQUEST"
    status_code = 409

    def __init__(self, reason: str, *, log_message: str | None = None) -> None:
        if reason not in VERIFICATION_REASON_CODES:
            raise ValueError(f"kode alasan verifikasi tidak dikenal: {reason}")
        self.reason = reason
        self.public_message = _REASON_MESSAGES[reason]
        self.details = [{"field": "reason", "message": reason}]
        super().__init__(log_message or f"prasyarat verifikasi gagal: {reason}")