"""Akses data setup dosen (BE-10.1).

Satu-satunya tempat query tabel ``instructor_profiles`` dan
``activity_configurations``. Repository tidak memutuskan aturan bisnis; ia hanya
memuat dan menyimpan, lalu mengembalikan domain
:class:`~src.services.instructor.domain.InstructorSetup`.

Baris 0..1 per dosen: dosen yang belum pernah menyimpan setup tidak memiliki
baris, sehingga :meth:`InstructorSetupRepository.load` mengembalikan ``None`` dan
service memakai nilai default.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.activity_configuration import ActivityConfiguration as ActivityEntity
from src.models.instructor_profile import InstructorProfile as ProfileEntity
from src.services.instructor.domain import (
    ActivityConfiguration,
    InstructorProfile,
    InstructorSetup,
)

__all__ = ["InstructorSetupRepository"]


class InstructorSetupRepository:
    """Baca/tulis setup dosen di atas ``AsyncSession`` yang di-inject dari luar."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def load(self, user_id: str) -> InstructorSetup | None:
        """Setup dosen, atau ``None`` bila belum ada satu baris pun."""
        profile = (
            await self._session.execute(
                select(ProfileEntity).where(ProfileEntity.user_id == user_id)
            )
        ).scalar_one_or_none()
        activity = (
            await self._session.execute(
                select(ActivityEntity).where(ActivityEntity.user_id == user_id)
            )
        ).scalar_one_or_none()

        if profile is None and activity is None:
            return None

        return InstructorSetup(
            profile=_to_profile(profile),
            activity=_to_activity(activity),
            updated_at=_latest_update(profile, activity),
        )

    async def save(self, user_id: str, setup: InstructorSetup) -> None:
        """Simpan setup dosen (insert atau update kedua baris dalam satu commit).

        ``ponytail:`` dua penyimpanan **pertama** yang berjalan bersamaan untuk
        dosen yang sama dapat bertabrakan pada unique constraint ``user_id``;
        request kedua gagal alih-alih menimpa. Upsert atomik
        (``INSERT ... ON CONFLICT``) ditambahkan bila ini terukur terjadi — form
        setup disimpan manual, jadi praktis tidak pernah bersamaan.
        """
        profile = await self._get_or_create(ProfileEntity, user_id)
        profile.teaching_style = setup.profile.teaching_style
        profile.expertise = setup.profile.expertise
        profile.delivery_preference = setup.profile.delivery_preference
        profile.language_preference = setup.profile.language_preference

        activity = await self._get_or_create(ActivityEntity, user_id)
        activity.learning_material = setup.activity.learning_material
        activity.learning_resource = setup.activity.learning_resource
        activity.assignment = setup.activity.assignment
        activity.quiz = setup.activity.quiz
        activity.additional_prompt = setup.activity.additional_prompt

        await self._session.commit()

    async def _get_or_create(
        self,
        entity_type: type[ProfileEntity] | type[ActivityEntity],
        user_id: str,
    ) -> ProfileEntity | ActivityEntity:
        statement = select(entity_type).where(entity_type.user_id == user_id)
        entity = (await self._session.execute(statement)).scalar_one_or_none()
        if entity is None:
            entity = entity_type(user_id=user_id)
            self._session.add(entity)
        return entity


def _to_profile(entity: ProfileEntity | None) -> InstructorProfile:
    if entity is None:
        return InstructorProfile()
    return InstructorProfile(
        teaching_style=entity.teaching_style or "",
        expertise=entity.expertise or "",
        delivery_preference=entity.delivery_preference or "",
        language_preference=entity.language_preference or "",
    )


def _to_activity(entity: ActivityEntity | None) -> ActivityConfiguration:
    if entity is None:
        return ActivityConfiguration()
    return ActivityConfiguration(
        learning_material=entity.learning_material,
        learning_resource=entity.learning_resource,
        assignment=entity.assignment,
        quiz=entity.quiz,
        additional_prompt=entity.additional_prompt,
    )


def _latest_update(
    profile: ProfileEntity | None, activity: ActivityEntity | None
) -> datetime | None:
    """Waktu perubahan terakhir dari kedua baris (``updated_at`` dikelola database)."""
    timestamps = [
        entity.updated_at for entity in (profile, activity) if entity is not None
    ]
    return max(timestamps) if timestamps else None
