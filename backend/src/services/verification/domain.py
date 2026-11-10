"""Representasi domain Moodle verification (BE-21.2).

Pembandingan kondisi course Moodle dengan kondisi yang diharapkan dilakukan
oleh fungsi murni :func:`compare_course` (tanpa I/O), sehingga aturan
pembandingan dapat diuji tanpa Moodle dan tanpa database:

- section: jumlah, urutan (nomor section = nomor minggu), dan nama;
- activity: keberadaan, jenis module, section, dan judul;
- Moodle object ID: ID yang tercatat pada tabel mapping BE-04.3 dibandingkan
  dengan objek yang benar-benar ada, serta dengan ID yang tercatat pada operasi
  eksekusi.

Setiap perbedaan memiliki jenis stabil (:class:`DiscrepancyType`). Perbedaan
yang terkait dengan operasi eksekusi dapat diperbaiki dengan menjalankan ulang
operasi itu; activity tidak terduga (mis. ditambahkan dosen langsung di Moodle)
hanya dilaporkan dan tidak pernah dihapus.
"""

from __future__ import annotations

import enum
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.models.execution_operation import OperationType
from src.models.verification import VerificationStatus
from src.services.moodle_integration_service import MoodleCourseContents

__all__ = [
    "ActivityExpectation",
    "Comparison",
    "Discrepancy",
    "DiscrepancyType",
    "MODULE_BY_OPERATION_TYPE",
    "SectionExpectation",
    "VerificationResultRecord",
    "compare_course",
    "status_for",
]

#: Jenis operasi konten → nama module Moodle (``modname``).
MODULE_BY_OPERATION_TYPE: dict[OperationType, str] = {
    OperationType.LEARNING_MATERIAL: "page",
    OperationType.LEARNING_RESOURCE: "url",
    OperationType.ASSIGNMENT: "assign",
    OperationType.QUIZ: "quiz",
}

#: Target perbedaan untuk section mingguan.
SECTION_TARGET = "SECTION"
#: Target perbedaan untuk module yang tidak dikenali.
ACTIVITY_TARGET = "ACTIVITY"


class DiscrepancyType(str, enum.Enum):
    """Jenis perbedaan antara kondisi yang diharapkan dan kondisi Moodle."""

    #: Section atau activity yang diharapkan tidak ada di course.
    MISSING = "MISSING"
    #: Activity ada, tetapi berada di section (minggu) yang salah.
    WRONG_SECTION = "WRONG_SECTION"
    #: Nama section atau judul activity berbeda.
    TITLE_MISMATCH = "TITLE_MISMATCH"
    #: Module di section mingguan yang tidak berasal dari eksekusi.
    UNEXPECTED = "UNEXPECTED"
    #: Moodle object ID tidak sesuai dengan mapping BE-04.3 atau catatan operasi.
    MAPPING_MISMATCH = "MAPPING_MISMATCH"


DISCREPANCY_LABELS: dict[DiscrepancyType, str] = {
    DiscrepancyType.MISSING: "hilang",
    DiscrepancyType.WRONG_SECTION: "salah section",
    DiscrepancyType.TITLE_MISMATCH: "judul berbeda",
    DiscrepancyType.UNEXPECTED: "tidak terduga",
    DiscrepancyType.MAPPING_MISMATCH: "ID Moodle tidak sesuai mapping",
}


@dataclass(frozen=True, kw_only=True)
class Discrepancy:
    """Satu perbedaan hasil verifikasi; aman ditampilkan ke dosen."""

    type: DiscrepancyType
    #: ``SECTION``, jenis operasi konten (mis. ``QUIZ``), atau ``ACTIVITY``.
    target: str
    message: str
    week_number: int | None = None
    expected: dict[str, Any] = field(default_factory=dict)
    actual: dict[str, Any] = field(default_factory=dict)
    #: Operasi eksekusi yang menghasilkan objek ini (``None`` untuk UNEXPECTED).
    operation_id: str | None = None
    moodle_object_id: int | None = None
    #: Mapping BE-04.3 menunjuk objek yang tidak ada lagi dan harus dibuang
    #: sebelum operasi dijalankan ulang.
    stale_mapping: bool = False

    @property
    def repairable(self) -> bool:
        return (
            self.type is not DiscrepancyType.UNEXPECTED
            and self.operation_id is not None
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "label": DISCREPANCY_LABELS[self.type],
            "target": self.target,
            "week_number": self.week_number,
            "message": self.message,
            "expected": dict(self.expected),
            "actual": dict(self.actual),
            "operation_id": self.operation_id,
            "moodle_object_id": self.moodle_object_id,
            "repairable": self.repairable,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Discrepancy:
        return cls(
            type=DiscrepancyType(data["type"]),
            target=str(data.get("target") or ""),
            message=str(data.get("message") or ""),
            week_number=data.get("week_number"),
            expected=dict(data.get("expected") or {}),
            actual=dict(data.get("actual") or {}),
            operation_id=data.get("operation_id"),
            moodle_object_id=data.get("moodle_object_id"),
        )


@dataclass(frozen=True, kw_only=True)
class SectionExpectation:
    """Section mingguan yang diharapkan dari course plan."""

    week_number: int
    name: str
    operation_id: str | None = None
    #: ID section pada mapping BE-04.3 (``course_plan_week``).
    mapped_section_id: int | None = None


@dataclass(frozen=True, kw_only=True)
class ActivityExpectation:
    """Activity yang diharapkan dari satu operasi konten eksekusi."""

    operation_id: str
    operation_type: OperationType
    week_number: int
    title: str
    #: cmid pada mapping BE-04.3; ``None`` bila belum pernah berhasil dibuat.
    mapped_cmid: int | None = None
    #: cmid yang tercatat pada operasi eksekusi.
    recorded_cmid: int | None = None

    @property
    def modname(self) -> str:
        return MODULE_BY_OPERATION_TYPE[self.operation_type]


@dataclass(frozen=True)
class Comparison:
    """Hasil satu kali pembandingan course dengan kondisi yang diharapkan."""

    discrepancies: tuple[Discrepancy, ...]
    summary: dict[str, int]

    @property
    def repairable(self) -> tuple[Discrepancy, ...]:
        return tuple(item for item in self.discrepancies if item.repairable)


def compare_course(
    contents: MoodleCourseContents,
    sections: Sequence[SectionExpectation],
    activities: Sequence[ActivityExpectation],
    *,
    report_unexpected: bool = True,
) -> Comparison:
    """Bandingkan isi course Moodle dengan section dan activity yang diharapkan."""
    discrepancies: list[Discrepancy] = []
    actual_sections = {section.section_number: section for section in contents.sections}
    weekly_numbers = sorted(number for number in actual_sections if number > 0)

    for expected in sorted(sections, key=lambda item: item.week_number):
        actual = actual_sections.get(expected.week_number)
        if actual is None:
            discrepancies.append(
                Discrepancy(
                    type=DiscrepancyType.MISSING,
                    target=SECTION_TARGET,
                    week_number=expected.week_number,
                    message=f"Section minggu {expected.week_number} tidak ada di course.",
                    expected={"name": expected.name},
                    operation_id=expected.operation_id,
                    moodle_object_id=expected.mapped_section_id,
                    stale_mapping=expected.mapped_section_id is not None,
                )
            )
            continue
        if actual.name != expected.name:
            discrepancies.append(
                Discrepancy(
                    type=DiscrepancyType.TITLE_MISMATCH,
                    target=SECTION_TARGET,
                    week_number=expected.week_number,
                    message=f"Nama section minggu {expected.week_number} berbeda.",
                    expected={"name": expected.name},
                    actual={"name": actual.name},
                    operation_id=expected.operation_id,
                    moodle_object_id=actual.moodle_section_id,
                )
            )
        if (
            expected.mapped_section_id is not None
            and expected.mapped_section_id != actual.moodle_section_id
        ):
            discrepancies.append(
                Discrepancy(
                    type=DiscrepancyType.MAPPING_MISMATCH,
                    target=SECTION_TARGET,
                    week_number=expected.week_number,
                    message=f"Mapping section minggu {expected.week_number} menunjuk section lain.",
                    expected={"moodle_object_id": expected.mapped_section_id},
                    actual={"moodle_object_id": actual.moodle_section_id},
                    operation_id=expected.operation_id,
                    moodle_object_id=actual.moodle_section_id,
                    stale_mapping=True,
                )
            )

    modules: dict[int, tuple[int, Any]] = {
        module.moodle_module_id: (section.section_number, module)
        for section in contents.sections
        for module in section.modules
    }
    expected_cmids: set[int] = set()
    found_activities = 0
    for expected in activities:
        label = f"{expected.operation_type.value} minggu {expected.week_number}"
        base = {
            "target": expected.operation_type.value,
            "week_number": expected.week_number,
            "operation_id": expected.operation_id,
        }
        if expected.mapped_cmid is None:
            discrepancies.append(
                Discrepancy(
                    type=DiscrepancyType.MISSING,
                    message=f"{label} belum pernah dibuat di Moodle.",
                    expected={"title": expected.title, "modname": expected.modname},
                    **base,
                )
            )
            continue
        expected_cmids.add(expected.mapped_cmid)
        located = modules.get(expected.mapped_cmid)
        if located is None:
            discrepancies.append(
                Discrepancy(
                    type=DiscrepancyType.MISSING,
                    message=f"{label} tidak ada di course (kemungkinan dihapus dari Moodle).",
                    expected={"title": expected.title, "modname": expected.modname},
                    moodle_object_id=expected.mapped_cmid,
                    stale_mapping=True,
                    **base,
                )
            )
            continue
        section_number, module = located
        if module.modname != expected.modname:
            discrepancies.append(
                Discrepancy(
                    type=DiscrepancyType.MAPPING_MISMATCH,
                    message=f"Mapping {label} menunjuk module {module.modname}.",
                    expected={"modname": expected.modname},
                    actual={"modname": module.modname},
                    moodle_object_id=expected.mapped_cmid,
                    stale_mapping=True,
                    **base,
                )
            )
            continue
        found_activities += 1
        if section_number != expected.week_number:
            discrepancies.append(
                Discrepancy(
                    type=DiscrepancyType.WRONG_SECTION,
                    message=f"{label} berada di section {section_number}.",
                    expected={"section": expected.week_number},
                    actual={"section": section_number},
                    moodle_object_id=expected.mapped_cmid,
                    **base,
                )
            )
        if module.name != expected.title:
            discrepancies.append(
                Discrepancy(
                    type=DiscrepancyType.TITLE_MISMATCH,
                    message=f"Judul {label} berbeda.",
                    expected={"title": expected.title},
                    actual={"title": module.name},
                    moodle_object_id=expected.mapped_cmid,
                    **base,
                )
            )
        if (
            expected.recorded_cmid is not None
            and expected.recorded_cmid != expected.mapped_cmid
        ):
            discrepancies.append(
                Discrepancy(
                    type=DiscrepancyType.MAPPING_MISMATCH,
                    message=f"ID Moodle pada operasi {label} berbeda dengan mapping.",
                    expected={"moodle_object_id": expected.mapped_cmid},
                    actual={"moodle_object_id": expected.recorded_cmid},
                    moodle_object_id=expected.mapped_cmid,
                    **base,
                )
            )

    if report_unexpected:
        for cmid, (section_number, module) in sorted(modules.items()):
            if section_number <= 0 or cmid in expected_cmids:
                continue
            discrepancies.append(
                Discrepancy(
                    type=DiscrepancyType.UNEXPECTED,
                    target=ACTIVITY_TARGET,
                    week_number=section_number,
                    message=f"Module {module.modname} '{module.name}' tidak berasal dari eksekusi.",
                    actual={
                        "title": module.name,
                        "modname": module.modname,
                        "section": section_number,
                    },
                    moodle_object_id=cmid,
                )
            )

    summary = {
        "expected_sections": len(sections),
        "actual_sections": len(weekly_numbers),
        "expected_activities": len(activities),
        "found_activities": found_activities,
    }
    return Comparison(discrepancies=tuple(discrepancies), summary=summary)


def status_for(discrepancies: Iterable[Discrepancy]) -> VerificationStatus:
    """``PASS`` tanpa perbedaan; ``PARTIAL`` bila hanya UNEXPECTED; selain itu ``FAIL``."""
    items = list(discrepancies)
    if not items:
        return VerificationStatus.PASS
    if all(not item.repairable for item in items):
        return VerificationStatus.PARTIAL
    return VerificationStatus.FAIL


@dataclass(frozen=True, kw_only=True)
class VerificationResultRecord:
    """Satu hasil Moodle verification beserta perbedaan dan perbaikannya."""

    workflow_id: str
    execution_id: str
    status: VerificationStatus
    verified_at: datetime
    discrepancies: tuple[Discrepancy, ...] = ()
    repaired: tuple[Discrepancy, ...] = ()
    repair_count: int = 0
    repair_rounds: int = 0
    summary: dict[str, int] | None = None
    error_message: str | None = None
    id: str | None = None
    created_at: datetime | None = None

    @property
    def matches(self) -> bool:
        """Kondisi Moodle sesuai dengan yang direncanakan dan disetujui."""
        return self.status is VerificationStatus.PASS