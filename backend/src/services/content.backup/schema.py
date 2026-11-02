# src/services/content/schema.py
from __future__ import annotations

from typing import Any

from src.schemas.content import ContentGenerationContext

# Keyword yang tidak (konsisten) didukung OpenAI strict structured output.
# Batasan ini tetap ditegakkan oleh Pydantic saat `model_validate`.
_UNSUPPORTED_KEYWORDS = frozenset(
    {
        "default",
        "minLength",
        "maxLength",
        "pattern",
        "format",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
        "minItems",
        "maxItems",
        "uniqueItems",
    }
)

# Key yang isinya adalah *peta nama -> schema*, bukan schema itu sendiri.
# Nama di dalamnya (mis. field "title" atau "default") tidak boleh difilter.
_SCHEMA_MAPS = frozenset({"properties", "$defs"})


def make_openai_strict_schema(schema: Any) -> Any:
    """Ubah JSON Schema Pydantic agar sesuai OpenAI strict mode.

    - semua property dijadikan ``required`` (field opsional tetap bisa ``null``
      karena Pydantic sudah menghasilkan ``anyOf: [..., {"type": "null"}]``);
    - ``additionalProperties: false`` pada setiap object;
    - keyword yang tidak didukung dibuang.
    """
    if isinstance(schema, list):
        return [make_openai_strict_schema(item) for item in schema]

    if not isinstance(schema, dict):
        return schema

    result: dict[str, Any] = {}
    for key, value in schema.items():
        if key in _UNSUPPORTED_KEYWORDS:
            continue
        if key in _SCHEMA_MAPS and isinstance(value, dict):
            result[key] = {
                name: make_openai_strict_schema(sub) for name, sub in value.items()
            }
        else:
            result[key] = make_openai_strict_schema(value)

    properties = result.get("properties")
    if isinstance(properties, dict):
        result["required"] = list(properties)
        result["additionalProperties"] = False

    return result


CONTENT_OUTPUT_SCHEMA = make_openai_strict_schema(
    GeneratedLearningMaterial.model_json_schema()
)

# Hanya dipakai bila memanggil API OpenAI langsung. Kalau `LLMService.execute_prompt`
# sudah membungkus `output_schema` menjadi response_format, cukup pakai
# CONTENT_OUTPUT_SCHEMA seperti RPS_OUTPUT_SCHEMA di analisis RPS.
CONTENT_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "content_generator_output",  # hanya [a-zA-Z0-9_-]
        "strict": True,
        "schema": CONTENT_OUTPUT_SCHEMA,
    },
}
