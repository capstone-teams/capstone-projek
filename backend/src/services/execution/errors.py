"""Error domain eksekusi Moodle (BE-17.1).

Error domain berada di layer service dan bukan ``HTTPException``; pemetaan ke
status HTTP dilakukan ``src/middlewares``. Setiap error membawa kontrak publik
yang sama seperti modul domain lain:

- ``error_code`` — kode pada envelope error (design-api §18);
- ``status_code`` — status HTTP yang sesuai;
- ``public_message`` — pesan aman untuk client;
- ``log_message`` — detail untuk log server-side, tidak pernah dikirim ke client.

Penolakan prasyarat memakai ``INVALID_REQUEST`` dengan **kode alasan** pada
``details`` (``field`` = ``reason``), sesuai issue BE-17.1/BE-17.2. Pesan Moodle
mentah tidak pernah diteruskan ke client.
"""

from __future__ import annotations

__all__ = [
    "EXECUTION_IN_PROGRESS",
    "ExecutionDomainError",
    "ExecutionFailedError",
    "ExecutionNotFoundError",
    "ExecutionPreconditionError",
    "ExecutionStateError",
    "MOODLE_TARGET_NOT_SET",
    "MOODLE_UNAVAILABLE",
    "PLAN_NOT_APPROVED",
    "REASON_CODES",
]

#: Kode alasan penolakan prasyarat eksekusi (issue BE-17.1).
PLAN_NOT_APPROVED = "PLAN_NOT_APPROVED"
MOODLE_TARGET_NOT_SET = "MOODLE_TARGET_NOT_SET"
MOODLE_UNAVAILABLE = "MOODLE_UNAVAILABLE"
EXECUTION_IN_PROGRESS = "EXECUTION_IN_PROGRESS"

REASON_CODES = frozenset(
    {
        PLAN_NOT_APPROVED,
        MOODLE_TARGET_NOT_SET,
        MOODLE_UNAVAILABLE,
        EXECUTION_IN_PROGRESS,
    }
)

_REASON_MESSAGES = {
    PLAN_NOT_APPROVED: "Course plan terbaru belum disetujui.",
    MOODLE_TARGET_NOT_SET: "Course target Moodle belum dipilih.",
    MOODLE_UNAVAILABLE: "Moodle tidak dapat dihubungi saat ini.",
    EXECUTION_IN_PROGRESS: (
        "Workflow ini sedang menjalankan proses lain; tunggu hingga selesai."
    ),
}


class ExecutionDomainError(Exception):
    """Base error domain eksekusi."""

    error_code = "INTERNAL_ERROR"
    status_code = 500
    public_message = "Permintaan eksekusi gagal."

    def __init__(self, log_message: str | None = None) -> None:
        self.log_message = log_message or type(self).__name__
        super().__init__(self.log_message)


class ExecutionNotFoundError(ExecutionDomainError):
    """Eksekusi tidak ada **atau** bukan milik workflow dosen peminta."""

    error_code = "RESOURCE_NOT_FOUND"
    status_code = 404
    public_message = "Eksekusi tidak ditemukan."

    def __init__(self, identifier: object) -> None:
        self.identifier = identifier
        super().__init__(f"eksekusi tidak ditemukan: {identifier}")


class ExecutionPreconditionError(ExecutionDomainError):
    """Prasyarat eksekusi tidak terpenuhi (HTTP 409, kode alasan stabil)."""

    error_code = "INVALID_REQUEST"
    status_code = 409

    def __init__(self, reason: str, *, log_message: str | None = None) -> None:
        if reason not in REASON_CODES:
            raise ValueError(f"kode alasan eksekusi tidak dikenal: {reason}")
        self.reason = reason
        self.public_message = _REASON_MESSAGES[reason]
        #: ``details`` pada envelope error: kode alasan yang dipakai frontend.
        self.details = [{"field": "reason", "message": reason}]
        super().__init__(log_message or f"prasyarat eksekusi gagal: {reason}")


class ExecutionStateError(ExecutionDomainError):
    """Status eksekusi tidak mengizinkan operasi yang diminta (HTTP 409)."""

    error_code = "INVALID_REQUEST"
    status_code = 409
    public_message = "Status eksekusi tidak mengizinkan operasi ini."

    def __init__(self, message: str, *, public_message: str | None = None) -> None:
        self.message = message
        if public_message is not None:
            self.public_message = public_message
        super().__init__(message)


class ExecutionFailedError(ExecutionDomainError):
    """Run eksekusi selesai dengan setidaknya satu operasi gagal.

    Dilempar setelah hasil dan ringkasan disimpan, sehingga orkestrator dapat
    menandai workflow ``FAILED`` (DL-012) dengan pesan publik yang jelas.
    """

    error_code = "INVALID_REQUEST"
    status_code = 409

    def __init__(self, message: str) -> None:
        self.message = message
        self.public_message = "Eksekusi ke Moodle gagal; periksa operasi yang gagal."
        super().__init__(message)
