"""Error domain course plan (BE-14.1).

Error domain berada di layer service dan bukan ``HTTPException``; pemetaan ke
status HTTP dilakukan ``src/middlewares`` (lihat ``backend/README.md``). Setiap
error membawa kontrak publik yang sama seperti modul domain lain:

- ``error_code`` — kode pada envelope error (design-api §18);
- ``status_code`` — status HTTP yang sesuai (design-api §19);
- ``public_message`` — pesan aman untuk client;
- ``log_message`` — detail untuk log server-side, tidak pernah dikirim ke client.

Detail teknis tidak pernah memuat isi prompt, credential, maupun keluaran mentah
model.
"""

from __future__ import annotations

__all__ = [
    "CoursePlanDomainError",
    "CoursePlanGenerationError",
    "CoursePlanNotFoundError",
    "CoursePlanStateError",
    "CoursePlanValidationError",
]


class CoursePlanDomainError(Exception):
    """Base error domain course plan."""

    error_code = "INTERNAL_ERROR"
    status_code = 500
    public_message = "Permintaan course plan gagal."

    def __init__(self, log_message: str | None = None) -> None:
        self.log_message = log_message or type(self).__name__
        super().__init__(self.log_message)


class CoursePlanNotFoundError(CoursePlanDomainError):
    """Course plan/versi tidak ada, atau workflow bukan milik peminta."""

    error_code = "RESOURCE_NOT_FOUND"
    status_code = 404
    public_message = "Course plan tidak ditemukan."

    def __init__(self, identifier: object, *, version: int | None = None) -> None:
        self.identifier = identifier
        self.version = version
        detail = f"course plan {identifier}"
        if version is not None:
            detail += f" versi {version}"
        super().__init__(f"{detail} tidak ditemukan")


class CoursePlanValidationError(CoursePlanDomainError):
    """Nilai input tidak memenuhi aturan domain (HTTP 422)."""

    error_code = "INVALID_REQUEST"
    status_code = 422
    public_message = "Data course plan tidak valid."

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


class CoursePlanStateError(CoursePlanDomainError):
    """Status workflow/versi tidak mengizinkan operasi yang diminta (HTTP 409)."""

    error_code = "INVALID_REQUEST"
    status_code = 409
    public_message = "Status course plan tidak mengizinkan operasi ini."

    def __init__(self, message: str, *, public_message: str | None = None) -> None:
        self.message = message
        if public_message is not None:
            # Pesan publik yang lebih spesifik (mis. "belum lolos validasi")
            # supaya client dapat menampilkan alasan penolakan yang jelas.
            self.public_message = public_message
        super().__init__(message)


class CoursePlanGenerationError(CoursePlanDomainError):
    """Agent gagal menghasilkan rencana yang valid setelah batas percobaan.

    Kode mengikuti kontrak kegagalan generasi LLM (design-api §18) supaya client
    memperlakukan kegagalan perencanaan sama seperti kegagalan analisis RPS.
    """

    error_code = "LLM_GENERATION_FAILED"
    status_code = 500
    public_message = "Course plan gagal dihasilkan. Coba generate ulang."

    def __init__(self, log_message: str) -> None:
        super().__init__(log_message)
