from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class DuplicateMappingError(Exception):
    pass


@dataclass(frozen=True)
class MoodleMapping:
    entity_type: str
    internal_id: str
    moodle_id: int


class IMoodleMappingRepository(Protocol):
    async def save(self, mapping: MoodleMapping) -> None: ...

    async def get_moodle_id(self, entity_type: str, internal_id: str) -> int | None: ...

    async def get_internal_id(self, entity_type: str, moodle_id: int) -> str | None: ...

    async def exists(self, entity_type: str, internal_id: str) -> bool: ...


class InMemoryMoodleMappingRepository:
    def __init__(self) -> None:
        self._by_internal: dict[tuple[str, str], int] = {}
        self._by_moodle: dict[tuple[str, int], str] = {}

    async def save(self, mapping: MoodleMapping) -> None:
        key = (mapping.entity_type, mapping.internal_id)
        existing = self._by_internal.get(key)
        if existing is not None and existing != mapping.moodle_id:
            raise DuplicateMappingError(
                f"{mapping.entity_type} '{mapping.internal_id}' sudah dipetakan ke "
                f"Moodle ID {existing}, tidak bisa dipetakan ulang ke {mapping.moodle_id}"
            )
        self._by_internal[key] = mapping.moodle_id
        self._by_moodle[(mapping.entity_type, mapping.moodle_id)] = mapping.internal_id

    async def get_moodle_id(self, entity_type: str, internal_id: str) -> int | None:
        return self._by_internal.get((entity_type, internal_id))

    async def get_internal_id(self, entity_type: str, moodle_id: int) -> str | None:
        return self._by_moodle.get((entity_type, moodle_id))

    async def exists(self, entity_type: str, internal_id: str) -> bool:
        return (entity_type, internal_id) in self._by_internal