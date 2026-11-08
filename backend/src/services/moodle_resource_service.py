"""Operasi learning resource (tautan referensi) ke Moodle (BE-12.1).

Resource mengikuti Content Schema §14 dan dipublikasikan sebagai activity URL
melalui plugin ``local_capstonebridge`` (BE-04.6). Section Moodle ditentukan
dari nomor minggu; section yang belum ada dibuat otomatis oleh Moodle.

Idempotency dijaga di dua tempat:

* tabel ``moodle_entity_mappings`` menyimpan ID internal resource dan
  course module ID Moodle (``cmid``), sehingga eksekusi ulang melakukan update;
* idempotency key disimpan sebagai *ID number* activity di Moodle, sehingga
  bila proses terhenti setelah create tetapi sebelum mapping tersimpan,
  eksekusi berikutnya tetap memakai activity yang sama.
"""

from __future__ import annotations

import html
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from src.services.moodle_client import MoodleClient
from src.services.moodle_mapping import IMoodleMappingRepository, MoodleMapping

__all__ = [
    "RESOURCE_ENTITY_TYPE",
    "InvalidLearningResourceError",
    "LearningResource",
    "MoodleResourceService",
    "ResourcePublishResult",
    "resource_idempotency_key",
]

RESOURCE_ENTITY_TYPE = "url_resource"
SUPPORTED_RESOURCE_TYPE = "external_link"
CREATE_FUNCTION = "local_capstonebridge_create_url"
UPDATE_FUNCTION = "local_capstonebridge_update_url"

_IDEMPOTENCY_PREFIX = "capstone-resource-"
_MAX_IDNUMBER_LENGTH = 100  # panjang kolom course_modules.idnumber di Moodle


class InvalidLearningResourceError(ValueError):
    """Data resource tidak memenuhi Content Schema §14."""


@dataclass(frozen=True)
class LearningResource:
    """Resource referensi sesuai Content Schema §14."""

    id: str
    title: str
    url: str
    description: str = ""
    resource_type: str = SUPPORTED_RESOURCE_TYPE

    @classmethod
    def from_content(cls, content: Mapping[str, Any]) -> LearningResource:
        """Bangun resource dari content item (``type: resource``)."""
        if content.get("type") != "resource":
            raise InvalidLearningResourceError("content item bukan bertipe 'resource'")
        return cls(
            id=str(content.get("id") or ""),
            title=str(content.get("title") or ""),
            url=str(content.get("url") or ""),
            description=str(content.get("description") or ""),
            resource_type=str(content.get("resource_type") or ""),
        )


@dataclass(frozen=True)
class ResourcePublishResult:
    resource_id: str
    moodle_course_id: int
    week: int
    cmid: int
    instance_id: int
    idempotency_key: str
    created: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "moodle_course_id": self.moodle_course_id,
            "week": self.week,
            "cmid": self.cmid,
            "instance_id": self.instance_id,
            "idempotency_key": self.idempotency_key,
            "created": self.created,
        }


def resource_idempotency_key(resource_id: str) -> str:
    """Idempotency key yang disimpan sebagai ID number activity di Moodle."""
    return f"{_IDEMPOTENCY_PREFIX}{resource_id}"


class MoodleResourceService:
    def __init__(self, client: MoodleClient, mappings: IMoodleMappingRepository) -> None:
        self._client = client
        self._mappings = mappings

    async def publish(
        self, moodle_course_id: int, week: int, resource: LearningResource
    ) -> ResourcePublishResult:
        """Buat resource pada section minggu ``week``, atau perbarui bila sudah ada."""
        _validate(moodle_course_id, week, resource)
        key = resource_idempotency_key(resource.id)
        fields = {
            "courseid": moodle_course_id,
            "name": resource.title.strip(),
            "externalurl": resource.url.strip(),
            "intro": _description_html(resource.description),
        }

        cmid = await self._mappings.get_moodle_id(RESOURCE_ENTITY_TYPE, resource.id)
        created = False
        if cmid is None:
            result = await self._client.call(
                CREATE_FUNCTION, {**fields, "section": week, "idnumber": key}
            )
            cmid = int(result["cmid"])
            created = int(result["created"]) == 1
            if not created:
                # Activity sudah ada di Moodle (eksekusi sebelumnya terhenti sebelum
                # mapping tersimpan): samakan isinya dengan data terbaru.
                result = await self._update(cmid, week, fields)
            await self._mappings.save(MoodleMapping(RESOURCE_ENTITY_TYPE, resource.id, cmid))
        else:
            result = await self._update(cmid, week, fields)

        return ResourcePublishResult(
            resource_id=resource.id,
            moodle_course_id=moodle_course_id,
            week=week,
            cmid=cmid,
            instance_id=int(result["instanceid"]),
            idempotency_key=key,
            created=created,
        )

    async def _update(self, cmid: int, week: int, fields: dict[str, Any]) -> dict[str, Any]:
        return await self._client.call(UPDATE_FUNCTION, {**fields, "cmid": cmid, "section": week})


def _validate(moodle_course_id: int, week: int, resource: LearningResource) -> None:
    if moodle_course_id <= 0:
        raise InvalidLearningResourceError("moodle_course_id harus bilangan positif")
    if week < 0:
        raise InvalidLearningResourceError("nomor minggu tidak boleh negatif")
    if not resource.id.strip():
        raise InvalidLearningResourceError("resource wajib memiliki id")
    if len(resource_idempotency_key(resource.id)) > _MAX_IDNUMBER_LENGTH:
        raise InvalidLearningResourceError("id resource terlalu panjang untuk idempotency key")
    if not resource.title.strip():
        raise InvalidLearningResourceError("judul resource wajib diisi")
    if resource.resource_type != SUPPORTED_RESOURCE_TYPE:
        raise InvalidLearningResourceError(
            f"resource_type '{resource.resource_type}' belum didukung; gunakan 'external_link'"
        )
    parsed = urlparse(resource.url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise InvalidLearningResourceError("url resource harus berupa alamat http(s) yang lengkap")


def _description_html(description: str) -> str:
    text = description.strip()
    if not text:
        return ""
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    return "".join(f"<p>{html.escape(part)}</p>" for part in paragraphs)