"""Error domain setup dosen (BE-10).

Error domain berada di layer service dan bukan ``HTTPException``; pemetaan ke
HTTP dilakukan ``src/middlewares/error_handlers.py``. Kontraknya sama dengan
error domain lain (lihat :mod:`src.services.rps.errors`): ``error_code``,
``status_code``, ``public_message``, dan ``log_message``.

Validasi setup memakai ``422 INVALID_REQUEST`` sesuai kontrak design-api §7.2 —
bukan ``VALIDATION_FAILED``, karena code tersebut dipakai untuk kesalahan schema
global dan frontend memetakan ``INVALID_REQUEST`` ke pesan per field. Setiap
pelanggaran membawa ``details`` berisi ``field`` dan ``message`` supaya frontend
dapat menempelkan pesan pada field yang salah.
"""

from __future__ import annotations

__all__ = ["InstructorSetupError", "InstructorSetupValidationError"]


class InstructorSetupError(Exception):
    """Base error domain setup dosen."""

    error_code = "INTERNAL_ERROR"
    status_code = 500
    public_message = "Pengaturan dosen gagal diproses."

    def __init__(
        self,
        log_message: str | None = None,
        *,
        details: list[dict[str, str]] | None = None,
    ) -> None:
        self.log_message = log_message or type(self).__name__
        self.details = details or []
        super().__init__(self.log_message)


class InstructorSetupValidationError(InstructorSetupError):
    """Nilai setup dosen melanggar aturan bisnis.

    Menerima **seluruh** pelanggaran sekaligus, bukan yang pertama saja, sehingga
    dosen dapat memperbaiki semua field bermasalah dalam satu kali perbaikan.
    ``issues`` berisi pasangan ``(field, message)``.
    """

    error_code = "INVALID_REQUEST"
    status_code = 422
    public_message = "Pengaturan dosen tidak valid."

    def __init__(self, issues: list[tuple[str, str]]) -> None:
        self.issues = issues
        details = [{"field": field, "message": message} for field, message in issues]
        super().__init__(
            "; ".join(f"{field}: {message}" for field, message in issues),
            details=details,
        )
