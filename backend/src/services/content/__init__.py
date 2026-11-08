"""Modul konten hasil generation (BE-19).

- ``domain`` — jenis konten, status approval, dan record versi konten;
- ``repository`` — akses tabel ``contents``/``activities`` beserta hasil
  validasinya.

Endpoint review (BE-19.2) dan tahap generation (BE-19.3) dibangun di atas
lapisan ini.
"""

from src.services.content.domain import (
    ApprovalStatus,
    ContentDraft,
    ContentKind,
    ContentRecord,
    ValidationRecord,
    content_key_for,
)
from src.services.content.repository import ContentRepository

__all__ = [
    "ApprovalStatus",
    "ContentDraft",
    "ContentKind",
    "ContentRecord",
    "ContentRepository",
    "ValidationRecord",
    "content_key_for",
]
