"""DTO setup dosen (design-api §7, BE-10.2).

Bentuk request/response mengikuti kontrak yang sudah terbit pada BE-06.4; kelas
di sini adalah **pemindahan** dari ``src/schemas/contract.py`` (nama kelas
dipertahankan supaya schema OpenAPI tidak berubah) setelah endpoint aslinya
mendarat.

Dua hal yang tidak dijaga di sini, karena merupakan aturan bisnis dan bukan
bentuk data:

- batas panjang ``additional_prompt`` berasal dari environment
  (``INSTRUCTOR_ADDITIONAL_PROMPT_MAX_LENGTH``);
- "minimal satu jenis aktivitas aktif".

Keduanya divalidasi layer service dan dilaporkan sebagai ``422 INVALID_REQUEST``
dengan ``details`` per field (issue BE-10.2), sama seperti kesalahan tipe data
pada body.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ActivityConfiguration",
    "InstructorProfileSetup",
    "InstructorSetupResponse",
    "InstructorSetupUpdate",
]


class InstructorProfileSetup(BaseModel):
    """Preferensi mengajar dosen yang dipakai agent pada semua kursusnya."""

    teaching_style: str | None = None
    expertise: str | None = None
    delivery_preference: str | None = None
    language_preference: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "teaching_style": "Interaktif dengan studi kasus",
                "expertise": "Rekayasa Perangkat Lunak",
                "delivery_preference": "Materi ringkas, banyak contoh kode",
                "language_preference": "Bahasa Indonesia",
            }
        }
    )


class ActivityConfiguration(BaseModel):
    """Jenis aktivitas pembelajaran yang boleh dihasilkan agent.

    Minimal satu harus ``true``; konfigurasi tanpa aktivitas aktif ditolak
    ``INVALID_REQUEST`` dengan detail per field (BE-10.2).
    """

    learning_material: bool = True
    learning_resource: bool = False
    assignment: bool = False
    quiz: bool = False

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "learning_material": True,
                "learning_resource": True,
                "assignment": False,
                "quiz": False,
            }
        }
    )


class InstructorSetupResponse(BaseModel):
    """Response ``GET``/``PUT /api/v1/instructors/me/setup`` (design-api §7)."""

    instructor_profile: InstructorProfileSetup
    additional_prompt: str = Field(default="", description="Instruksi tambahan untuk agent.")
    activity_configuration: ActivityConfiguration
    updated_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "instructor_profile": {
                    "teaching_style": "Interaktif dengan studi kasus",
                    "expertise": "Rekayasa Perangkat Lunak",
                    "delivery_preference": "Materi ringkas, banyak contoh kode",
                    "language_preference": "Bahasa Indonesia",
                },
                "additional_prompt": "Sertakan contoh SQL pada setiap materi.",
                "activity_configuration": {
                    "learning_material": True,
                    "learning_resource": True,
                    "assignment": False,
                    "quiz": False,
                },
                "updated_at": "2026-10-21T08:02:00Z",
            }
        }
    )


class InstructorSetupUpdate(BaseModel):
    """Body ``PUT /api/v1/instructors/me/setup`` (design-api §7).

    Seluruh field opsional: hanya nilai yang dikirim yang diubah. Batas panjang
    ``additional_prompt`` dikonfigurasi melalui environment (BE-10.2), sehingga
    nilai batasnya tidak di-hardcode pada kontrak ini.
    """

    instructor_profile: InstructorProfileSetup | None = None
    additional_prompt: str | None = None
    activity_configuration: ActivityConfiguration | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "instructor_profile": {"teaching_style": "Berbasis proyek"},
                "additional_prompt": "Sertakan contoh SQL pada setiap materi.",
                "activity_configuration": {"learning_material": True, "quiz": True},
            }
        }
    )
