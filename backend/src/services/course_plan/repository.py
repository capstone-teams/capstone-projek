"""Akses data course plan (BE-14.1).

Satu-satunya tempat query tabel ``course_plans`` dan ``course_plan_weeks``.
Repository hanya menjawab "bagaimana versi rencana diambil/disimpan?", tanpa
aturan approval maupun pemilihan tahap workflow — keduanya berada di
:mod:`src.services.course_plan.service` dan orkestrator BE-14.3.

Pemetaan entity ↔ domain berada di modul ini (pola yang sama dengan
:mod:`src.services.workflow.repository`) supaya domain tetap bebas SQLAlchemy.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.course_plan import CoursePlan as CoursePlanEntity
from src.models.course_plan import CoursePlanStatus
from src.models.course_plan_week import CoursePlanWeek as CoursePlanWeekEntity
from src.services.course_plan.domain import (
    CoursePlanDraft,
    CoursePlanRecord,
    CoursePlanWeekRecord,
)

__all__ = ["CoursePlanRepository"]


class CoursePlanRepository:
    """Akses data versi course plan di atas ``AsyncSession`` yang di-inject."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, draft: CoursePlanDraft) -> CoursePlanRecord:
        """Simpan satu versi baru beserta minggunya dalam satu transaksi."""
        entity = CoursePlanEntity(
            workflow_id=draft.workflow_id,
            rps_id=draft.rps_id,
            rps_analysis_id=draft.rps_analysis_id,
            course_id=draft.course_id,
            version=draft.version,
            weeks_count=len(draft.weeks),
            status=CoursePlanStatus.DRAFT,
            plan_data=draft.plan_data,
            activity_configuration=draft.activity_configuration,
            validation_result=draft.validation_result,
            revision_notes=draft.revision_notes,
            regeneration_instruction=draft.regeneration_instruction,
            prompt_version=draft.prompt_version,
            model_name=draft.model_name,
        )
        self._session.add(entity)
        await self._session.flush()

        for week in draft.weeks:
            self._session.add(
                CoursePlanWeekEntity(
                    course_plan_id=entity.id,
                    week_number=week.week_number,
                    title=week.title,
                    learning_outcomes=list(week.learning_outcomes) or None,
                    objectives=list(week.objectives) or None,
                    topics=list(week.topics) or None,
                    methods=list(week.teaching_methods) or None,
                    planned_activities=list(week.planned_activities) or None,
                    week_type=week.week_type,
                    rps_week=week.rps_week,
                )
            )

        await self._session.commit()
        await self._session.refresh(entity)
        return await self._to_record(entity)

    async def get_latest(self, workflow_id: str) -> CoursePlanRecord | None:
        """Versi dengan nomor tertinggi pada sebuah workflow."""
        entity = (
            await self._session.execute(
                select(CoursePlanEntity)
                .where(CoursePlanEntity.workflow_id == workflow_id)
                .order_by(CoursePlanEntity.version.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        return None if entity is None else await self._to_record(entity)

    async def get_by_id(self, plan_id: str) -> CoursePlanRecord | None:
        """Satu versi berdasarkan identifier.

        Dipakai eksekusi (BE-17.1) untuk membaca **snapshot** rencana yang
        dieksekusi, bukan versi terbaru yang mungkin sudah berubah.
        """
        entity = await self._session.get(CoursePlanEntity, plan_id)
        return None if entity is None else await self._to_record(entity)

    async def get_version(
        self, workflow_id: str, version: int
    ) -> CoursePlanRecord | None:
        entity = (
            await self._session.execute(
                select(CoursePlanEntity).where(
                    CoursePlanEntity.workflow_id == workflow_id,
                    CoursePlanEntity.version == version,
                )
            )
        ).scalar_one_or_none()
        return None if entity is None else await self._to_record(entity)

    async def list_versions(self, workflow_id: str) -> list[CoursePlanRecord]:
        """Seluruh versi, terbaru lebih dulu (riwayat penolakan/regenerasi)."""
        entities = (
            await self._session.execute(
                select(CoursePlanEntity)
                .where(CoursePlanEntity.workflow_id == workflow_id)
                .order_by(CoursePlanEntity.version.desc())
            )
        ).scalars().all()
        return [await self._to_record(entity) for entity in entities]

    async def next_version(self, workflow_id: str) -> int:
        """Nomor versi berikutnya; ``1`` bila belum ada versi."""
        latest = (
            await self._session.execute(
                select(func.max(CoursePlanEntity.version)).where(
                    CoursePlanEntity.workflow_id == workflow_id
                )
            )
        ).scalar_one_or_none()
        return int(latest or 0) + 1

    async def has_approved(self, workflow_id: str) -> bool:
        """Apakah workflow sudah memiliki versi yang disetujui."""
        identifier = (
            await self._session.execute(
                select(CoursePlanEntity.id)
                .where(
                    CoursePlanEntity.workflow_id == workflow_id,
                    CoursePlanEntity.status == CoursePlanStatus.APPROVED,
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        return identifier is not None

    async def set_status(
        self,
        plan_id: str,
        status: CoursePlanStatus,
        *,
        approved_at=None,
        revision_notes: str | None = None,
        regeneration_instruction: str | None = None,
    ) -> CoursePlanRecord | None:
        """Ubah status satu versi; versi lain tidak disentuh."""
        entity = await self._session.get(CoursePlanEntity, plan_id)
        if entity is None:
            return None

        entity.status = status
        entity.approved_at = approved_at
        if revision_notes is not None:
            entity.revision_notes = revision_notes
        if regeneration_instruction is not None:
            entity.regeneration_instruction = regeneration_instruction

        await self._session.commit()
        await self._session.refresh(entity)
        return await self._to_record(entity)

    # --- Mapping ----------------------------------------------------------

    async def _to_record(self, entity: CoursePlanEntity) -> CoursePlanRecord:
        week_entities = (
            await self._session.execute(
                select(CoursePlanWeekEntity)
                .where(CoursePlanWeekEntity.course_plan_id == entity.id)
                .order_by(CoursePlanWeekEntity.week_number)
            )
        ).scalars().all()

        plan_data = entity.plan_data or {}
        course = plan_data.get("course") if isinstance(plan_data, dict) else None

        return CoursePlanRecord(
            id=entity.id,
            workflow_id=entity.workflow_id,
            rps_id=entity.rps_id,
            version=entity.version,
            status=entity.status,
            course=course or {},
            weeks=tuple(_to_week_record(week) for week in week_entities),
            weeks_count=entity.weeks_count,
            plan_data=entity.plan_data,
            validation_result=entity.validation_result,
            activity_configuration=entity.activity_configuration,
            revision_notes=entity.revision_notes,
            regeneration_instruction=entity.regeneration_instruction,
            prompt_version=entity.prompt_version,
            model_name=entity.model_name,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            approved_at=entity.approved_at,
        )


def _to_week_record(entity: CoursePlanWeekEntity) -> CoursePlanWeekRecord:
    return CoursePlanWeekRecord(
        id=entity.id,
        week_number=entity.week_number,
        title=entity.title,
        learning_outcomes=tuple(entity.learning_outcomes or ()),
        objectives=tuple(entity.objectives or ()),
        topics=tuple(entity.topics or ()),
        teaching_methods=tuple(entity.methods or ()),
        planned_activities=tuple(entity.planned_activities or ()),
        week_type=entity.week_type,
        rps_week=entity.rps_week,
    )
