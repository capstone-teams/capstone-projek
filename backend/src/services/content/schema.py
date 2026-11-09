"""Schema structured output untuk generasi konten.

Fungsi ``make_openai_strict_schema`` dipindahkan ke
:mod:`src.services.llm.structured_output` agar dipakai bersama prompt lain;
modul ini tetap mengekspornya untuk pemanggil lama.

Satu schema per jenis konten (LEARNING_MATERIAL, RESOURCE, ASSIGNMENT, QUIZ),
dibangun dari model Output di ``src.schemas.content.REGISTRY``.
"""

from __future__ import annotations

from src.schemas.content import REGISTRY
from src.services.llm.structured_output import make_openai_strict_schema

__all__ = [
    "CONTENT_OUTPUT_SCHEMA",
    "CONTENT_OUTPUT_SCHEMAS",
    "get_output_schema",
    "make_openai_strict_schema",
]

# OpenAI Structured Output Schema per jenis konten
CONTENT_OUTPUT_SCHEMAS: dict[str, dict] = {
    key: make_openai_strict_schema(spec.output_model.model_json_schema())
    for key, spec in REGISTRY.items()
}

# Untuk pemanggil lama: schema learning material.
CONTENT_OUTPUT_SCHEMA = CONTENT_OUTPUT_SCHEMAS["LEARNING_MATERIAL"]


def get_output_schema(content_type) -> dict:
    """Schema untuk satu jenis konten; menerima string atau enum."""
    key = getattr(content_type, "value", content_type)
    return CONTENT_OUTPUT_SCHEMAS[key]
