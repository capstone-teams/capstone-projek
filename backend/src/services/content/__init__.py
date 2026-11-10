"""Modul konten hasil generation (BE-19).

- ``domain`` — jenis konten, status approval, dan record versi konten;
- ``repository`` — akses tabel ``contents``/``activities`` beserta hasil
  validasinya;
- ``service`` — operasi review: baca per minggu/jenis, riwayat versi, dan
  keputusan approve/reject dosen pemilik workflow.

Tahap generation (BE-19.3) dibangun di atas lapisan ini.
"""

from src.services.content.domain import (
    ApprovalStatus,
    ContentDraft,
    ContentKind,
    ContentRecord,
    ValidationRecord,
    content_key_for,
)
from src.services.content.errors import (
    ContentDomainError,
    ContentNotFoundError,
    ContentStateError,
    ContentValidationError,
)
from src.services.content.repository import (
    ContentGenerationRepository,
    ContentRepository,
)
from src.services.content.service import ContentReviewService

__all__ = [
    "ApprovalStatus",
    "ContentDomainError",
    "ContentDraft",
    "ContentGenerationRepository",
    "ContentKind",
    "ContentNotFoundError",
    "ContentRecord",
    "ContentRepository",
    "ContentReviewService",
    "ContentStateError",
    "ContentValidationError",
    "ValidationRecord",
    "content_key_for",
]
