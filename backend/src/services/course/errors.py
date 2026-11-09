"""Error domain baca course (BE-14 pendahuluan).

Bentuknya mengikuti error domain lain (lihat :mod:`src.services.rps.errors`):
``error_code``, ``status_code``, ``public_message``, dan ``log_message``.
Pemetaan ke HTTP dilakukan ``src.middlewares.error_handlers``.
"""

from __future__ import annotations

__all__ = ["CourseDomainError", "CourseNotFoundError"]


class CourseDomainError(Exception):
    """Base error domain course."""

    error_code = "INTERNAL_ERROR"
    status_code = 500
    public_message = "Course gagal dibaca."

    def __init__(self, log_message: str | None = None) -> None:
        self.log_message = log_message or type(self).__name__
        super().__init__(self.log_message)


class CourseNotFoundError(CourseDomainError):
    """Course tidak ada **atau** bukan milik dosen yang login.

    Keduanya memakai respons yang sama supaya keberadaan course milik dosen lain
    tidak bisa ditebak dari perbedaan status.
    """

    error_code = "RESOURCE_NOT_FOUND"
    status_code = 404
    public_message = "Course tidak ditemukan."

    def __init__(self, course_id: str) -> None:
        super().__init__(f"course tidak ditemukan: {course_id}")
