"""Penyesuaian JSON Schema Pydantic untuk structured output OpenAI.

Fungsi ini murni (tanpa I/O) dan dipakai bersama oleh seluruh prompt yang
meminta output JSON terstruktur, sehingga aturan strict mode hanya ditulis di
satu tempat:

- semua property dijadikan ``required``;
- field opsional tetap dapat menerima ``null``;
- setiap object memakai ``additionalProperties: false``;
- keyword yang tidak didukung strict mode dibuang.
"""

from __future__ import annotations

from typing import Any

__all__ = ["make_openai_strict_schema"]

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
    """Ubah JSON Schema Pydantic agar sesuai OpenAI strict mode."""

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

    # Semua property wajib dicantumkan dalam strict mode.
    properties = result.get("properties")

    if isinstance(properties, dict):
        result["required"] = list(properties)
        result["additionalProperties"] = False

    return result
