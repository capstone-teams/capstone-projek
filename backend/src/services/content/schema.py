"""Schema structured output untuk generasi konten.

Fungsi ``make_openai_strict_schema`` dipindahkan ke
:mod:`src.services.llm.structured_output` agar dipakai bersama prompt lain;
modul ini tetap mengekspornya untuk pemanggil lama.
"""

from __future__ import annotations

from src.schemas.content import GeneratedLearningMaterial
from src.services.llm.structured_output import make_openai_strict_schema

__all__ = ["CONTENT_OUTPUT_SCHEMA", "make_openai_strict_schema"]

# OpenAI Structured Output Schema
CONTENT_OUTPUT_SCHEMA = make_openai_strict_schema(
    GeneratedLearningMaterial.model_json_schema()
)
