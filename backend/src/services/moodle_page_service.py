"""Operasi learning material (Page) ke Moodle (BE-04.4).

Learning material dipublikasikan sebagai activity Page melalui plugin
``local_capstonebridge`` (BE-04.6) pada section sesuai nomor minggu. Isi page
berupa HTML: dari ``LearningMaterialData`` (``contents.content_data``, Content
Schema §11–§13) dirangkai menjadi Markdown dengan ``render_material_markdown``,
lalu dikonversi menjadi HTML yang sudah di-escape.

Idempotency sama seperti operasi activity lain (BE-12):

* tabel ``moodle_entity_mappings`` menyimpan ID konten internal dan course
  module ID Moodle (``cmid``), sehingga eksekusi ulang melakukan update;
* idempotency key disimpan sebagai *ID number* activity di Moodle, sehingga
  bila proses terhenti setelah create tetapi sebelum mapping tersimpan,
  eksekusi berikutnya tetap memakai page yang sama.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from src.schemas.content import LearningMaterialData, render_material_markdown
from src.services.moodle_client import MoodleClient
from src.services.moodle_html import markdown_to_html, paragraphs_html
from src.services.moodle_mapping import IMoodleMappingRepository, MoodleMapping

__all__ = [
    "PAGE_ENTITY_TYPE",
    "InvalidLearningMaterialError",
    "LearningMaterialPage",
    "MoodlePageService",
    "PagePublishResult",
    "page_idempotency_key",
]

PAGE_ENTITY_TYPE = "learning_material"
CREATE_FUNCTION = "local_capstonebridge_create_page"
UPDATE_FUNCTION = "local_capstonebridge_update_page"

_IDEMPOTENCY_PREFIX = "capstone-page-"
_MAX_IDNUMBER_LENGTH = 100  # panjang kolom course_modules.idnumber di Moodle
_MAX_NAME_LENGTH = 255


class InvalidLearningMaterialError(ValueError):
    """Data learning material tidak valid."""


@dataclass(frozen=True)
class LearningMaterialPage:
    """Satu learning material yang dipasang sebagai Page."""

    id: str
    title: str
    content_html: str
    summary: str = ""

    @classmethod
    def from_markdown(cls, content_id: str, title: str, markdown: str, summary: str = "") -> LearningMaterialPage:
        """Bangun page dari Markdown (misalnya kolom ``contents.content_markdown``)."""
        return cls(id=str(content_id), title=title, content_html=markdown_to_html(markdown), summary=summary)

    @classmethod
    def from_content(
        cls, content_id: str, title: str, content_data: Mapping[str, Any]
    ) -> LearningMaterialPage:
        """Bangun page dari baris ``contents`` bertipe ``LEARNING_MATERIAL``."""
        try:
            data = LearningMaterialData.model_validate(dict(content_data))
        except ValidationError as exc:
            raise InvalidLearningMaterialError(f"content_data learning material tidak valid: {exc}") from exc
        return cls.from_markdown(content_id, title, render_material_markdown(data))


@dataclass(frozen=True)
class PagePublishResult:
    content_id: str
    moodle_course_id: int
    week: int
    cmid: int
    instance_id: int
    idempotency_key: str
    created: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "content_id": self.content_id,
            "moodle_course_id": self.moodle_course_id,
            "week": self.week,
            "cmid": self.cmid,
            "instance_id": self.instance_id,
            "idempotency_key": self.idempotency_key,
            "created": self.created,
        }


def page_idempotency_key(content_id: str) -> str:
    """Idempotency key yang disimpan sebagai ID number page di Moodle."""
    return f"{_IDEMPOTENCY_PREFIX}{content_id}"


class MoodlePageService:
    def __init__(self, client: MoodleClient, mappings: IMoodleMappingRepository) -> None:
        self._client = client
        self._mappings = mappings

    async def publish(self, moodle_course_id: int, week: int, page: LearningMaterialPage) -> PagePublishResult:
        """Buat page pada section minggu ``week``, atau perbarui bila sudah ada."""
        _validate(moodle_course_id, week, page)
        key = page_idempotency_key(page.id)
        fields = {
            "courseid": moodle_course_id,
            "name": page.title.strip(),
            "content": page.content_html,
            "intro": paragraphs_html(page.summary),
        }

        cmid = await self._mappings.get_moodle_id(PAGE_ENTITY_TYPE, page.id)
        created = False
        if cmid is None:
            result = await self._client.call(CREATE_FUNCTION, {**fields, "section": week, "idnumber": key})
            cmid = int(result["cmid"])
            created = int(result["created"]) == 1
            if not created:
                # Page sudah ada di Moodle (eksekusi sebelumnya terhenti sebelum
                # mapping tersimpan): samakan isinya dengan data terbaru.
                result = await self._update(cmid, week, fields)
            await self._mappings.save(MoodleMapping(PAGE_ENTITY_TYPE, page.id, cmid))
        else:
            result = await self._update(cmid, week, fields)

        return PagePublishResult(
            content_id=page.id,
            moodle_course_id=moodle_course_id,
            week=week,
            cmid=cmid,
            instance_id=int(result["instanceid"]),
            idempotency_key=key,
            created=created,
        )

    async def _update(self, cmid: int, week: int, fields: dict[str, Any]) -> dict[str, Any]:
        return await self._client.call(UPDATE_FUNCTION, {**fields, "cmid": cmid, "section": week})


def _validate(moodle_course_id: int, week: int, page: LearningMaterialPage) -> None:
    if moodle_course_id <= 0:
        raise InvalidLearningMaterialError("moodle_course_id harus bilangan positif")
    if week < 0:
        raise InvalidLearningMaterialError("nomor minggu tidak boleh negatif")
    if not page.id.strip():
        raise InvalidLearningMaterialError("learning material wajib memiliki id")
    if len(page_idempotency_key(page.id)) > _MAX_IDNUMBER_LENGTH:
        raise InvalidLearningMaterialError("id learning material terlalu panjang untuk idempotency key")
    if not page.title.strip():
        raise InvalidLearningMaterialError("judul learning material wajib diisi")
    if len(page.title.strip()) > _MAX_NAME_LENGTH:
        raise InvalidLearningMaterialError("judul learning material maksimal 255 karakter")
    if not page.content_html.strip():
        raise InvalidLearningMaterialError("isi learning material wajib diisi")