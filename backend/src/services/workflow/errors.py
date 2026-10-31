"""Error domain workflow (BE-11.1).

Error domain berada di layer service dan **bukan** ``HTTPException``; pemetaan ke
status HTTP dilakukan oleh ``src/middlewares`` (lihat ``backend/README.md``).
Setiap error membawa kontrak publik yang sama seperti modul domain lain:

- ``error_code`` — kode pada envelope error (design-api §18);
- ``status_code`` — status HTTP yang sesuai (design-api §19);
- ``public_message`` — pesan aman untuk client;
- ``log_message`` — detail untuk log server-side, tidak pernah dikirim ke client.

Detail teknis workflow boleh memuat identifier RPS/workflow, tetapi tidak pernah
credential, API key, maupun isi prompt.
"""

from __future__ import annotations

__all__ = [
    "WorkflowDomainError",
    "WorkflowNotFoundError",
    "WorkflowStateError",
    "WorkflowValidationError",
]


class WorkflowDomainError(Exception):
    """Base error domain workflow."""

    error_code = "INTERNAL_ERROR"
    status_code = 500
    public_message = "Permintaan workflow gagal."

    def __init__(self, log_message: str | None = None) -> None:
        self.log_message = log_message or type(self).__name__
        super().__init__(self.log_message)


class WorkflowNotFoundError(WorkflowDomainError):
    """Workflow tidak ada **atau** bukan milik dosen yang meminta.

    Kedua keadaan menghasilkan error yang sama supaya keberadaan workflow milik
    dosen lain tidak dapat diketahui dari perbedaan response (bandingkan
    design-api §23; pola yang sama dipakai :class:`RPSNotFoundError`).
    """

    error_code = "RESOURCE_NOT_FOUND"
    status_code = 404
    public_message = "Workflow tidak ditemukan."

    def __init__(self, identifier: object) -> None:
        self.identifier = identifier
        super().__init__(f"workflow tidak ditemukan: {identifier}")


class WorkflowValidationError(WorkflowDomainError):
    """Nilai/atribut workflow tidak memenuhi aturan domain (HTTP 422)."""

    error_code = "INVALID_REQUEST"
    status_code = 422
    public_message = "Data workflow tidak valid."

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


class WorkflowStateError(WorkflowDomainError):
    """Status workflow tidak mengizinkan operasi yang diminta (HTTP 409)."""

    error_code = "INVALID_REQUEST"
    status_code = 409
    public_message = "Status workflow tidak mengizinkan operasi ini."

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
