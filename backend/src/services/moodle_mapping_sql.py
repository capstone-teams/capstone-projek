from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.moodle_entity_mapping import MoodleEntityMapping
from src.services.moodle_mapping import DuplicateMappingError, MoodleMapping

__all__ = ["SqlMoodleMappingRepository"]

_UNIQUE_VIOLATION_SQLSTATE = "23505"


class SqlMoodleMappingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, mapping: MoodleMapping) -> None:
        existing = await self.get_moodle_id(mapping.entity_type, mapping.internal_id)
        if existing is not None:
            if existing != mapping.moodle_id:
                raise _conflict(mapping, existing)
            return

        self._session.add(
            MoodleEntityMapping(
                entity_type=mapping.entity_type,
                internal_id=mapping.internal_id,
                moodle_id=mapping.moodle_id,
            )
        )
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            if not _is_unique_violation(exc):
                raise
            # Bisa jadi save identik dari proses lain yang menang lebih dulu.
            existing = await self.get_moodle_id(mapping.entity_type, mapping.internal_id)
            if existing == mapping.moodle_id:
                return
            raise _conflict(mapping, existing) from exc

    async def get_moodle_id(self, entity_type: str, internal_id: str) -> int | None:
        statement = select(MoodleEntityMapping.moodle_id).where(
            MoodleEntityMapping.entity_type == entity_type,
            MoodleEntityMapping.internal_id == internal_id,
        )
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def get_internal_id(self, entity_type: str, moodle_id: int) -> str | None:
        statement = select(MoodleEntityMapping.internal_id).where(
            MoodleEntityMapping.entity_type == entity_type,
            MoodleEntityMapping.moodle_id == moodle_id,
        )
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def exists(self, entity_type: str, internal_id: str) -> bool:
        return await self.get_moodle_id(entity_type, internal_id) is not None


def _conflict(mapping: MoodleMapping, existing: int | None) -> DuplicateMappingError:
    if existing is not None:
        return DuplicateMappingError(
            f"{mapping.entity_type} '{mapping.internal_id}' sudah dipetakan ke "
            f"Moodle ID {existing}, tidak bisa dipetakan ulang ke {mapping.moodle_id}"
        )
    return DuplicateMappingError(
        f"Moodle ID {mapping.moodle_id} untuk {mapping.entity_type} sudah dipakai "
        "oleh entity internal lain"
    )


def _is_unique_violation(exc: IntegrityError) -> bool:
    original = getattr(exc, "orig", None)
    if getattr(original, "sqlstate", None) == _UNIQUE_VIOLATION_SQLSTATE:
        return True
    if getattr(original, "pgcode", None) == _UNIQUE_VIOLATION_SQLSTATE:
        return True
    return "unique" in str(original).lower()