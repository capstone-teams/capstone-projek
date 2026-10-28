"""Konteks dosen untuk agent (BE-10.3).

Agent **tidak** boleh query database sendiri. Ia menerima konteks dosen dari
:class:`~src.services.instructor.service.InstructorSetupService` sebagai payload
yang siap diserialisasi ke YAML, memakai serializer BE-08.1
(:func:`src.services.rps.yaml_export.dump_yaml`) — format yang sama dengan input
LLM RPS.

Dokumen yang dihasilkan selalu memuat penanda hierarki konteks:

- ``context_role: supporting`` — konteks dosen hanya pendukung;
- ``academic_source_of_truth: rps`` — fakta akademik tetap milik RPS, sesuai PRD
  FR-010 dan agent-design §15: profile mengubah *penyajian*, bukan fakta.

Field kosong dibuang agar tidak membuang token dan tidak memberi kesan dosen
"mengatur" sesuatu yang belum ia isi.
"""

from __future__ import annotations

from typing import Any

from src.services.instructor.domain import ACTIVITY_FIELDS, InstructorSetup
from src.services.rps.yaml_export import dump_yaml

__all__ = [
    "ACADEMIC_SOURCE_OF_TRUTH",
    "CONTEXT_NOTE",
    "CONTEXT_ROLE",
    "instructor_context_to_yaml",
    "to_agent_context",
]

#: Konteks dosen berada di bawah RPS dan tidak boleh mengubah fakta akademik.
CONTEXT_ROLE = "supporting"
ACADEMIC_SOURCE_OF_TRUTH = "rps"
CONTEXT_NOTE = (
    "Konteks pendukung. Informasi akademik dari RPS tetap menjadi sumber utama "
    "dan tidak boleh diubah oleh preferensi dosen."
)


def to_agent_context(setup: InstructorSetup) -> dict[str, Any]:
    """Payload konteks dosen siap dipakai prompt course planning/content generation."""
    payload: dict[str, Any] = {
        "context_role": CONTEXT_ROLE,
        "academic_source_of_truth": ACADEMIC_SOURCE_OF_TRUTH,
        "note": CONTEXT_NOTE,
    }

    profile = {
        "teaching_style": setup.profile.teaching_style,
        "expertise": setup.profile.expertise,
        "delivery_preference": setup.profile.delivery_preference,
        "language_preference": setup.profile.language_preference,
    }
    profile = {key: value for key, value in profile.items() if value}
    if profile:
        payload["instructor_profile"] = profile

    if setup.activity.additional_prompt:
        payload["additional_prompt"] = setup.activity.additional_prompt

    # Seluruh jenis ditulis eksplisit (termasuk yang nonaktif): agent harus tahu
    # apa yang **tidak** boleh dibuat, bukan hanya apa yang boleh (PRD FR-026).
    payload["activity_configuration"] = {
        name: bool(getattr(setup.activity, name)) for name in ACTIVITY_FIELDS
    }
    return payload


def instructor_context_to_yaml(setup: InstructorSetup) -> str:
    """Serialisasi konteks dosen ke YAML untuk prompt agent."""
    return dump_yaml(to_agent_context(setup))
