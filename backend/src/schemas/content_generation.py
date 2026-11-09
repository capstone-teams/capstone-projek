"""DTO endpoint generate/regenerate konten (BE-19.3).

Bentuk request mengikuti issue BE-19.3 dan design-api §10:

- generate menerima ``"all"`` atau daftar nomor minggu;
- regenerate memakai :class:`RegenerationScope` dengan catatan revisi wajib.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.services.content.generation import RegenerationScope

__all__ = [
    "ContentGenerateRequest",
    "ContentGenerationResponse",
    "ContentRegenerateRequest",
]


class ContentGenerateRequest(BaseModel):
    """Body ``POST /workflows/{workflow_id}/contents/generate``."""

    weeks: list[int] | Literal["all"] = Field(
        default="all",
        description='``"all"`` atau daftar nomor minggu, mis. ``[1, 2]``.',
    )


class ContentRegenerateRequest(BaseModel):
    """Body ``POST /workflows/{workflow_id}/contents/regenerate``."""

    scope: RegenerationScope = Field(
        default=RegenerationScope.COURSE,
        description="COURSE = seluruh konten, MINGGU = satu minggu, ITEM = satu konten.",
    )
    week_number: int | None = Field(
        default=None, ge=1, description="Wajib untuk scope MINGGU."
    )
    content_id: str | None = Field(
        default=None, description="Wajib untuk scope ITEM."
    )
    notes: str = Field(
        default="", description="Catatan revisi dosen; wajib diisi."
    )


class ContentGenerationResponse(BaseModel):
    """Response ``202`` setelah run generation dijadwalkan."""

    workflow_id: str
    status: str
    scope: RegenerationScope | None = None
    message: str
