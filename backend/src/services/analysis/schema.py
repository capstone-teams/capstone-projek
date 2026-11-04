from typing import Any

from src.schemas.rps_structured import RPSStructuredData


def _make_openai_strict_schema(schema: Any) -> Any:
    if isinstance(schema, list):
        return [_make_openai_strict_schema(item) for item in schema]

    if not isinstance(schema, dict):
        return schema

    schema = {
        key: _make_openai_strict_schema(value)
        for key, value in schema.items()
        if key != "default"
    }

    properties = schema.get("properties")

    if isinstance(properties, dict):
        schema["required"] = list(properties.keys())
        schema["additionalProperties"] = False

    return schema


RPS_OUTPUT_SCHEMA = _make_openai_strict_schema(
    RPSStructuredData.model_json_schema()
)
