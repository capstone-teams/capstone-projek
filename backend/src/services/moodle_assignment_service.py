
"""Operasi assignment ke Moodle (BE-12.2).

Isi assignment diambil dari ``AssignmentData`` (``activities.activity_data``,
lihat :mod:`src.schemas.content`): instruksi, hasil yang dikumpulkan, dan rubric
penilaian (Content Schema §15–§16). Isi tersebut dirangkai menjadi deskripsi
HTML activity Assignment dan dipublikasikan melalui plugin
``local_capstonebridge`` (BE-04.6, minimal versi 0.4.0) pada section sesuai
nomor minggu.

Pengaturan pengumpulan tidak dihasilkan oleh generation, sehingga memakai
:class:`AssignmentSettings` dengan nilai default berikut:

* submission online text **dan** file aktif, sehingga mahasiswa dapat mengetik
  jawaban atau mengunggah dokumen;
* maksimal 5 file, ukuran mengikuti batas course;
* nilai maksimum 100 (sama dengan ``gradepointmax`` bawaan Moodle);
* tanpa due date (Content Schema §15: agent tidak boleh mengarang deadline).

Rubric MVP disimpan sebagai tabel kriteria pada deskripsi assignment, belum
memakai advanced grading Moodle (Content Schema §16).

Idempotency dijaga di dua tempat, sama seperti resource (BE-12.1):

* tabel ``moodle_entity_mappings`` menyimpan ID activity internal dan course
  module ID Moodle (``cmid``), sehingga eksekusi ulang melakukan update;
* idempotency key disimpan sebagai *ID number* activity di Moodle, sehingga
  bila proses terhenti setelah create tetapi sebelum mapping tersimpan,
  eksekusi berikutnya tetap memakai activity yang sama.
"""

from __future__ import annotations

import html
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import ValidationError

from src.schemas.content import AssignmentData
from src.services.moodle_client import MoodleClient
from src.services.moodle_html import inline_markdown, markdown_to_html
from src.services.moodle_mapping import IMoodleMappingRepository, MoodleMapping


__all__ = [
    "ASSIGNMENT_ENTITY_TYPE",
    "SUBMISSION_FILE",
    "SUBMISSION_ONLINE_TEXT",
    "AssignmentContent",
    "AssignmentPublishResult",
    "AssignmentSettings",
    "InvalidAssignmentError",
    "MoodleAssignmentService",
    "RubricItem",
    "assignment_idempotency_key",
    "render_assignment_intro",
]


ASSIGNMENT_ENTITY_TYPE = "assignment"
CREATE_FUNCTION = "local_capstonebridge_create_assign"
UPDATE_FUNCTION = "local_capstonebridge_update_assign"

SUBMISSION_ONLINE_TEXT = "online_text"
SUBMISSION_FILE = "file"
SUPPORTED_SUBMISSION_TYPES = frozenset({SUBMISSION_ONLINE_TEXT, SUBMISSION_FILE})

DEFAULT_SUBMISSION_TYPES = (SUBMISSION_ONLINE_TEXT, SUBMISSION_FILE)
DEFAULT_MAX_FILES = 5
DEFAULT_MAX_GRADE = 100
MAX_FILES_LIMIT = 20  # batas bawaan assignsubmission_file | maxfiles

_IDEMPOTENCY_PREFIX = "capstone-assignment-"
_MAX_IDNUMBER_LENGTH = 100  # panjang kolom course_modules.idnumber di Moodle
_MAX_NAME_LENGTH = 255


class InvalidAssignmentError(ValueError):
    """Data assignment atau pengaturannya tidak valid."""


@dataclass(frozen=True)
class RubricItem:
    criterion: str
    description: str
    weight_percent: int


@dataclass(frozen=True)
class AssignmentContent:
    """Isi assignment hasil generation (Content Schema §15–§16)."""

    id: str
    title: str
    instructions_markdown: str
    expected_outputs: tuple[str, ...] = ()
    rubric: tuple[RubricItem, ...] = ()

    @classmethod
    def from_activity(
        cls, activity_id: str, title: str, activity_data: Mapping[str, Any]
    ) -> AssignmentContent:
        """Bangun dari baris ``activities`` bertipe ``ASSIGNMENT``."""
        try:
            data = AssignmentData.model_validate(dict(activity_data))
        except ValidationError as exc:
            raise InvalidAssignmentError(f"activity_data assignment tidak valid: {exc}") from exc
        return cls(
            id=str(activity_id),
            title=title,
            instructions_markdown=data.instructions_markdown,
            expected_outputs=tuple(data.expected_outputs),
            rubric=tuple(
                RubricItem(item.criterion, item.description, item.weight_percent)
                for item in data.rubric
            ),
        )


@dataclass(frozen=True)
class AssignmentSettings:
    """Pengaturan pengumpulan dan penilaian di Moodle."""

    submission_types: tuple[str, ...] = DEFAULT_SUBMISSION_TYPES
    max_files: int = DEFAULT_MAX_FILES
    max_grade: int = DEFAULT_MAX_GRADE
    due: datetime | None = None

    def to_moodle(self) -> dict[str, int]:
        return {
            "onlinetext": int(SUBMISSION_ONLINE_TEXT in self.submission_types),
            "filesubmission": int(SUBMISSION_FILE in self.submission_types),
            "maxfiles": self.max_files,
            "grade": self.max_grade,
            "duedate": int(self.due.timestamp()) if self.due is not None else 0,
        }


@dataclass(frozen=True)
class AssignmentPublishResult:
    assignment_id: str
    moodle_course_id: int
    week: int
    cmid: int
    instance_id: int
    idempotency_key: str
    created: bool
    settings: AssignmentSettings = field(default_factory=AssignmentSettings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "assignment_id": self.assignment_id,
            "moodle_course_id": self.moodle_course_id,
            "week": self.week,
            "cmid": self.cmid,
            "instance_id": self.instance_id,
            "idempotency_key": self.idempotency_key,
            "created": self.created,
            "submission_types": list(self.settings.submission_types),
            "max_files": self.settings.max_files,
            "max_grade": self.settings.max_grade,
            "due": self.settings.due.isoformat() if self.settings.due else None,
        }


def assignment_idempotency_key(assignment_id: str) -> str:
    """Idempotency key yang disimpan sebagai ID number activity di Moodle."""
    return f"{_IDEMPOTENCY_PREFIX}{assignment_id}"


class MoodleAssignmentService:
    def __init__(self, client: MoodleClient, mappings: IMoodleMappingRepository) -> None:
        self._client = client
        self._mappings = mappings

    async def publish(
        self,
        moodle_course_id: int,
        week: int,
        assignment: AssignmentContent,
        settings: AssignmentSettings | None = None,
    ) -> AssignmentPublishResult:
        """Buat assignment pada section minggu ``week``, atau perbarui bila sudah ada."""
        settings = settings or AssignmentSettings()
        _validate(moodle_course_id, week, assignment, settings)
        key = assignment_idempotency_key(assignment.id)
        fields = {
            "courseid": moodle_course_id,
            "name": assignment.title.strip(),
            "intro": render_assignment_intro(assignment),
            **settings.to_moodle(),
        }

        cmid = await self._mappings.get_moodle_id(ASSIGNMENT_ENTITY_TYPE, assignment.id)
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
            await self._mappings.save(MoodleMapping(ASSIGNMENT_ENTITY_TYPE, assignment.id, cmid))
        else:
            result = await self._update(cmid, week, fields)

        return AssignmentPublishResult(
            assignment_id=assignment.id,
            moodle_course_id=moodle_course_id,
            week=week,
            cmid=cmid,
            instance_id=int(result["instanceid"]),
            idempotency_key=key,
            created=created,
            settings=settings,
        )

    async def _update(self, cmid: int, week: int, fields: dict[str, Any]) -> dict[str, Any]:
        return await self._client.call(UPDATE_FUNCTION, {**fields, "cmid": cmid, "section": week})


def _validate(
    moodle_course_id: int,
    week: int,
    assignment: AssignmentContent,
    settings: AssignmentSettings,
) -> None:
    if moodle_course_id <= 0:
        raise InvalidAssignmentError("moodle_course_id harus bilangan positif")
    if week < 0:
        raise InvalidAssignmentError("nomor minggu tidak boleh negatif")
    if not assignment.id.strip():
        raise InvalidAssignmentError("assignment wajib memiliki id")
    if len(assignment_idempotency_key(assignment.id)) > _MAX_IDNUMBER_LENGTH:
        raise InvalidAssignmentError("id assignment terlalu panjang untuk idempotency key")
    if not assignment.title.strip():
        raise InvalidAssignmentError("judul assignment wajib diisi")
    if len(assignment.title.strip()) > _MAX_NAME_LENGTH:
        raise InvalidAssignmentError("judul assignment maksimal 255 karakter")
    if not assignment.instructions_markdown.strip():
        raise InvalidAssignmentError("instruksi assignment wajib diisi")
    if assignment.rubric:
        if any(not item.criterion.strip() for item in assignment.rubric):
            raise InvalidAssignmentError("setiap kriteria rubric wajib memiliki nama")
        total = sum(item.weight_percent for item in assignment.rubric)
        if total != 100:
            raise InvalidAssignmentError(f"total bobot rubric harus 100, saat ini {total}")

    if not settings.submission_types:
        raise InvalidAssignmentError("minimal satu jenis pengumpulan harus aktif")
    unknown = set(settings.submission_types) - SUPPORTED_SUBMISSION_TYPES
    if unknown:
        raise InvalidAssignmentError(
            f"jenis pengumpulan {sorted(unknown)} belum didukung; gunakan 'online_text' atau 'file'"
        )
    if not 1 <= settings.max_files <= MAX_FILES_LIMIT:
        raise InvalidAssignmentError(f"max_files harus 1 sampai {MAX_FILES_LIMIT}")
    if settings.max_grade <= 0:
        raise InvalidAssignmentError("max_grade harus lebih dari 0")
    if settings.due is not None and settings.due.tzinfo is None:
        raise InvalidAssignmentError("due date wajib menyertakan zona waktu")


# --- Deskripsi assignment (HTML) ---------------------------------------------


def render_assignment_intro(assignment: AssignmentContent) -> str:
    """Rangkai instruksi, hasil yang dikumpulkan, dan rubric menjadi HTML."""
    parts = [markdown_to_html(assignment.instructions_markdown, heading_tag="h5")]
    outputs = [item.strip() for item in assignment.expected_outputs if item.strip()]
    if outputs:
        items = "".join(f"<li>{inline_markdown(item)}</li>" for item in outputs)
        parts.append(f"<h5>Hasil yang Dikumpulkan</h5><ul>{items}</ul>")
    if assignment.rubric:
        rows = "".join(
            "<tr>"
            f"<td>{html.escape(item.criterion.strip())}</td>"
            f"<td>{html.escape(item.description.strip())}</td>"
            f"<td>{item.weight_percent}%</td>"
            "</tr>"
            for item in assignment.rubric
        )
        parts.append(
            "<h5>Kriteria Penilaian</h5>"
            '<table class="generaltable">'
            "<thead><tr><th>Kriteria</th><th>Deskripsi</th><th>Bobot</th></tr></thead>"
            f"<tbody>{rows}</tbody>"
            "</table>"
        )
    return "".join(parts)
