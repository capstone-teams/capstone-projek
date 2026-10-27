"""Domain setup dosen (BE-10.1/BE-10.2).

Modul ini memegang aturan nilai setup dosen tanpa I/O: normalisasi teks, batas
panjang, dan aturan "minimal satu jenis konten aktif". Ia tidak tahu tabel,
session, maupun FastAPI, sehingga aturannya dapat diuji tanpa database.

Bentuk nilainya mengikuti kontrak yang sudah terbit (design-api §7): keempat
field profile berupa teks (``expertise`` adalah satu deskripsi, bukan daftar),
empat flag aktivitas, dan ``additional_prompt`` opsional.

Seluruh pelanggaran dikumpulkan lalu dilempar sekaligus sebagai
:class:`~src.services.instructor.errors.InstructorSetupValidationError`, dengan
``field`` berupa path JSON (``instructor_profile.teaching_style``) supaya
frontend dapat menempelkan pesan pada field yang tepat.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.models.instructor_profile import (
    MAX_DELIVERY_PREFERENCE_LENGTH,
    MAX_EXPERTISE_LENGTH,
    MAX_LANGUAGE_PREFERENCE_LENGTH,
    MAX_TEACHING_STYLE_LENGTH,
)
from src.services.instructor.errors import InstructorSetupValidationError

__all__ = [
    "ACTIVITY_FIELDS",
    "ActivityConfiguration",
    "InstructorProfile",
    "InstructorSetup",
    "normalize_setup",
]

#: Nama field aktivitas sesuai kolom database dan body API.
ACTIVITY_FIELDS = ("learning_material", "learning_resource", "assignment", "quiz")


@dataclass(frozen=True, slots=True)
class InstructorProfile:
    """Preferensi penyampaian dosen. Nilai kosong berarti "tidak diatur"."""

    teaching_style: str = ""
    expertise: str = ""
    delivery_preference: str = ""
    language_preference: str = ""


@dataclass(frozen=True, slots=True)
class ActivityConfiguration:
    """Jenis konten yang boleh dibuat agent, plus additional prompt.

    Default database (BE-10.1): learning material aktif, jenis lain nonaktif.
    """

    learning_material: bool = True
    learning_resource: bool = False
    assignment: bool = False
    quiz: bool = False
    additional_prompt: str | None = None

    @property
    def enabled_activity_types(self) -> tuple[str, ...]:
        """Nama field aktivitas yang aktif, sesuai urutan :data:`ACTIVITY_FIELDS`."""
        return tuple(name for name in ACTIVITY_FIELDS if getattr(self, name))


@dataclass(frozen=True, slots=True)
class InstructorSetup:
    """Setup lengkap seorang dosen."""

    profile: InstructorProfile = field(default_factory=InstructorProfile)
    activity: ActivityConfiguration = field(default_factory=ActivityConfiguration)
    #: Waktu perubahan terakhir salah satu baris; ``None`` bila belum pernah disimpan.
    updated_at: datetime | None = None


def normalize_setup(
    *,
    profile: InstructorProfile,
    activity: ActivityConfiguration,
    prompt_max_length: int,
) -> InstructorSetup:
    """Validasi dan normalisasi nilai setup dosen.

    Seluruh pelanggaran aturan bisnis dikumpulkan dalam satu
    :class:`InstructorSetupValidationError`; nilai yang lolos dikembalikan berupa
    domain siap simpan. Tipe data itu sendiri sudah dijaga schema Pydantic,
    sehingga fungsi ini hanya menangani aturan nilai (panjang dan kelengkapan).
    """
    issues: list[tuple[str, str]] = []

    normalized_profile = InstructorProfile(
        teaching_style=_text(
            profile.teaching_style,
            field="instructor_profile.teaching_style",
            maximum=MAX_TEACHING_STYLE_LENGTH,
            issues=issues,
        ),
        expertise=_text(
            profile.expertise,
            field="instructor_profile.expertise",
            maximum=MAX_EXPERTISE_LENGTH,
            issues=issues,
        ),
        delivery_preference=_text(
            profile.delivery_preference,
            field="instructor_profile.delivery_preference",
            maximum=MAX_DELIVERY_PREFERENCE_LENGTH,
            issues=issues,
        ),
        language_preference=_text(
            profile.language_preference,
            field="instructor_profile.language_preference",
            maximum=MAX_LANGUAGE_PREFERENCE_LENGTH,
            issues=issues,
        ),
    )

    normalized_activity = ActivityConfiguration(
        learning_material=activity.learning_material,
        learning_resource=activity.learning_resource,
        assignment=activity.assignment,
        quiz=activity.quiz,
        additional_prompt=_additional_prompt(
            activity.additional_prompt,
            maximum=prompt_max_length,
            issues=issues,
        ),
    )

    # PRD FR-025/FR-026: agent hanya membuat aktivitas yang dipilih dosen. Tanpa
    # satu pun jenis aktif, tidak ada konten yang boleh dibuat — itu salah
    # konfigurasi, bukan pilihan yang sah.
    if not normalized_activity.enabled_activity_types:
        issues.append(
            (
                "activity_configuration",
                "minimal satu jenis konten harus aktif (learning_material, "
                "learning_resource, assignment, atau quiz)",
            )
        )

    if issues:
        raise InstructorSetupValidationError(issues)

    return InstructorSetup(profile=normalized_profile, activity=normalized_activity)


def _text(value: str, *, field: str, maximum: int, issues: list[tuple[str, str]]) -> str:
    text = value.strip()
    if len(text) > maximum:
        issues.append((field, f"maksimal {maximum} karakter"))
    return text[:maximum]


def _additional_prompt(
    value: str | None, *, maximum: int, issues: list[tuple[str, str]]
) -> str | None:
    """Prompt kosong disimpan sebagai ``None``: tidak ada instruksi tambahan."""
    if value is None:
        return None
    prompt = value.strip()
    if not prompt:
        return None
    if len(prompt) > maximum:
        issues.append(("additional_prompt", f"maksimal {maximum} karakter"))
        return prompt[:maximum]
    return prompt
