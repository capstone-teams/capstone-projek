from __future__ import annotations

from typing import Any

from src.schemas.content import GeneratedLearningMaterial


# JSON Schema keywords yang tidak didukung OpenAI Strict Mode.
_UNSUPPORTED_KEYWORDS = {
    "default",
    "title",
    "examples",
    "format",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "minLength",
    "maxLength",
    "pattern",
    "minItems",
    "maxItems",
    "uniqueItems",
    "minProperties",
    "maxProperties",
    "multipleOf",
}

# Keyword yang berisi mapping schema.
_SCHEMA_MAPS = {
    "$defs",
    "properties",
    "patternProperties",
    "definitions",
}


def make_openai_strict_schema(schema: Any) -> Any:
    """Ubah JSON Schema Pydantic agar sesuai OpenAI strict mode.

    - Semua property dijadikan required.
    - Field opsional tetap dapat menerima null.
    - Setiap object menggunakan additionalProperties: false.
    - Keyword yang tidak didukung dibuang.
    """

    if isinstance(schema, list):
        return [
            make_openai_strict_schema(item)
            for item in schema
        ]

    if not isinstance(schema, dict):
        return schema

    result: dict[str, Any] = {}

    for key, value in schema.items():
        if key in _UNSUPPORTED_KEYWORDS:
            continue

        if key in _SCHEMA_MAPS and isinstance(value, dict):
            result[key] = {
                name: make_openai_strict_schema(sub)
                for name, sub in value.items()
            }
        else:
            result[key] = make_openai_strict_schema(value)

    # Semua property wajib dicantumkan dalam strict mode.
    properties = result.get("properties")

    if isinstance(properties, dict):
        result["required"] = list(properties)
        result["additionalProperties"] = False

    return result


# OpenAI Structured Output Schema
CONTENT_OUTPUT_SCHEMA = make_openai_strict_schema(
    GeneratedLearningMaterial.model_json_schema()
)
