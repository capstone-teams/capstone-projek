"""Akses data konten hasil generation (BE-19.1).

Repository ini adalah satu-satunya tempat query tabel ``contents`` dan
``activities`` untuk konten hasil generation, serta ``validation_results`` yang
menempel padanya. Tabel dipilih dari :attr:`ContentKind.table`; domain tetap
tidak tahu SQLAlchemy.

Aturan versi:

- versi pertama memakai kunci deterministik
  :func:`~src.services.content.domain.content_key_for`;
- regenerasi mengirim ``content_key`` versi lama dan mendapat nomor versi
  berikutnya;
- tidak ada baris versi lama yang diubah atau dihapus.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.activity import Activity as ActivityEntity
from src.models.activity import ActivityStatus, ActivityType
from src.models.content import Content as ContentEntity
from src.models.content import ContentStatus, ContentType
from src.models.validation_result import (
    ValidationResult,
    ValidationStatus,
    ValidationTargetType,
)
from src.services.content.domain import (
    ApprovalStatus,
    ContentDraft,
    ContentKind,
    ContentRecord,
    ValidationRecord,
    content_key_for,
)

__all__ = ["ContentRepository"]

_CONTENT_STATUSES = {status.value for status in ContentStatus}
_ACTIVITY_STATUSES = {status.value for status in ActivityStatus}


class ContentRepository:
    """Akses data versi konten dan hasil validasinya."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- Tulis ------------------------------------------------------------

    async def create(self, draft: ContentDraft) -> ContentRecord:
        """Simpan satu versi baru; versi lama tidak disentuh."""
        content_key = draft.content_key or content_key_for(
            draft.workflow_id, draft.week_number, draft.kind
        )
        version = await self.next_version(content_key)

        if draft.kind.is_activity:
            entity: ContentEntity | ActivityEntity = ActivityEntity(
                workflow_id=draft.workflow_id,
                course_plan_id=draft.course_plan_id,
                course_plan_week_id=draft.course_plan_week_id,
                week_number=draft.week_number,
                content_key=content_key,
                type=ActivityType(draft.kind.value),
                title=draft.title,
                activity_data=draft.content_data,
                enabled=True,
                version=version,
                status=ActivityStatus(draft.status.value),
                revision_notes=draft.revision_notes,
                prompt_version=draft.prompt_version,
                model_name=draft.model_name,
                generated_by_agent_run_id=draft.agent_run_id,
            )
        else:
            entity = ContentEntity(
                workflow_id=draft.workflow_id,
                course_plan_id=draft.course_plan_id,
                course_plan_week_id=draft.course_plan_week_id,
                week_number=draft.week_number,
                content_key=content_key,
                content_type=ContentType(draft.kind.value),
                title=draft.title,
                content_data=draft.content_data,
                content_markdown=draft.content_markdown,
                version=version,
                status=ContentStatus(draft.status.value),
                revision_notes=draft.revision_notes,
                prompt_version=draft.prompt_version,
                model_name=draft.model_name,
                generated_by_agent_run_id=draft.agent_run_id,
            )

        self._session.add(entity)
        await self._session.commit()
        await self._session.refresh(entity)
        return self._to_record(entity)

    async def set_status(
        self,
        content_id: str,
        status: ApprovalStatus,
        *,
        revision_notes: str | None = None,
    ) -> ContentRecord | None:
        """Ubah status satu versi; versi lain tidak disentuh."""
        entity = await self._entity_by_id(content_id)
        if entity is None:
            return None

        if isinstance(entity, ActivityEntity):
            entity.status = ActivityStatus(status.value)
        else:
            entity.status = ContentStatus(status.value)

        if revision_notes is not None:
            entity.revision_notes = revision_notes

        await self._session.commit()
        await self._session.refresh(entity)
        return await self._with_validation(self._to_record(entity))

    async def add_validation(
        self,
        content: ContentRecord,
        *,
        status: ValidationStatus,
        checks: dict | None = None,
        errors: dict | None = None,
        warnings: dict | None = None,
        score: float | None = None,
        retry_count: int = 0,
        agent_run_id: str | None = None,
        validated_at: datetime | None = None,
    ) -> ValidationRecord:
        """Simpan hasil validasi (termasuk temuan dan jumlah retry)."""
        entity = ValidationResult(
            agent_run_id=agent_run_id,
            target_type=self._target_type(content),
            target_id=content.id,
            status=status,
            checks=checks,
            errors=errors,
            warnings=warnings,
            score=score,
            retry_count=retry_count,
            validated_at=validated_at or datetime.now(timezone.utc),
        )
        self._session.add(entity)
        await self._session.commit()
        await self._session.refresh(entity)
        return _to_validation(entity)

    # --- Baca -------------------------------------------------------------

    async def get_by_id(self, content_id: str) -> ContentRecord | None:
        """Satu versi berdasarkan identifier (tabel ditentukan saat lookup)."""
        entity = await self._entity_by_id(content_id)
        return None if entity is None else await self._with_validation(
            self._to_record(entity)
        )

    async def get_latest(self, content_key: str) -> ContentRecord | None:
        """Versi terbaru untuk satu kunci konten."""
        entities = [
            *(
                await self._session.execute(
                    select(ContentEntity).where(
                        ContentEntity.content_key == content_key
                    )
                )
            ).scalars(),
            *(
                await self._session.execute(
                    select(ActivityEntity).where(
                        ActivityEntity.content_key == content_key
                    )
                )
            ).scalars(),
        ]
        if not entities:
            return None

        latest = max(entities, key=lambda item: item.version)
        return await self._with_validation(self._to_record(latest))

    async def list_versions(self, content_key: str) -> list[ContentRecord]:
        """Seluruh versi satu konten, terbaru lebih dulu."""
        entities = [
            *(
                await self._session.execute(
                    select(ContentEntity).where(
                        ContentEntity.content_key == content_key
                    )
                )
            ).scalars(),
            *(
                await self._session.execute(
                    select(ActivityEntity).where(
                        ActivityEntity.content_key == content_key
                    )
                )
            ).scalars(),
        ]
        records = sorted(
            (self._to_record(entity) for entity in entities),
            key=lambda record: record.version,
            reverse=True,
        )
        return await self._with_validations(records)

    async def list_for_workflow(
        self,
        workflow_id: str,
        *,
        week_number: int | None = None,
        content_type: ContentKind | None = None,
        status: ApprovalStatus | None = None,
    ) -> list[ContentRecord]:
        """Versi terbaru setiap konten pada workflow, dengan filter opsional.

        Baris lama tanpa ``content_key`` (dibuat sebelum BE-19) tetap muncul,
        tetapi tidak punya hasil validasi.
        """
        records: list[ContentRecord] = []

        include_contents = content_type is None or not content_type.is_activity
        if include_contents and (
            status is None or status.value in _CONTENT_STATUSES
        ):
            statement = select(ContentEntity).where(
                ContentEntity.workflow_id == workflow_id
            )
            if week_number is not None:
                statement = statement.where(
                    ContentEntity.week_number == week_number
                )
            if content_type is not None:
                statement = statement.where(
                    ContentEntity.content_type == ContentType(content_type.value)
                )
            if status is not None:
                statement = statement.where(
                    ContentEntity.status == ContentStatus(status.value)
                )
            records.extend(
                self._to_record(entity)
                for entity in (await self._session.execute(statement)).scalars()
            )

        include_activities = content_type is None or content_type.is_activity
        if include_activities and (
            status is None or status.value in _ACTIVITY_STATUSES
        ):
            statement = select(ActivityEntity).where(
                ActivityEntity.workflow_id == workflow_id
            )
            if week_number is not None:
                statement = statement.where(
                    ActivityEntity.week_number == week_number
                )
            if content_type is not None:
                statement = statement.where(
                    ActivityEntity.type == ActivityType(content_type.value)
                )
            if status is not None:
                statement = statement.where(
                    ActivityEntity.status == ActivityStatus(status.value)
                )
            records.extend(
                self._to_record(entity)
                for entity in (await self._session.execute(statement)).scalars()
            )

        # Daftar konten menampilkan versi terbaru per content key; riwayat versi
        # dibaca lewat ``list_versions``. Baris lama tanpa key diperlakukan
        # sebagai konten tersendiri agar tidak saling menimpa.
        latest: dict[str, ContentRecord] = {}
        for record in records:
            key = record.content_key or record.id
            current = latest.get(key)
            if current is None or record.version > current.version:
                latest[key] = record

        ordered = sorted(
            latest.values(),
            key=lambda record: (
                record.week_number or 0,
                record.kind.value,
                record.version,
            ),
        )
        return await self._with_validations(ordered)

    async def next_version(self, content_key: str) -> int:
        """Nomor versi berikutnya untuk satu kunci konten."""
        content_version = await self._session.scalar(
            select(func.max(ContentEntity.version)).where(
                ContentEntity.content_key == content_key
            )
        )
        activity_version = await self._session.scalar(
            select(func.max(ActivityEntity.version)).where(
                ActivityEntity.content_key == content_key
            )
        )
        return int(max(content_version or 0, activity_version or 0)) + 1

    # --- Mapping ----------------------------------------------------------

    async def _entity_by_id(
        self, content_id: str
    ) -> ContentEntity | ActivityEntity | None:
        entity = await self._session.get(ContentEntity, content_id)
        if entity is not None:
            return entity
        return await self._session.get(ActivityEntity, content_id)

    def _to_record(
        self, entity: ContentEntity | ActivityEntity
    ) -> ContentRecord:
        if isinstance(entity, ActivityEntity):
            return ContentRecord(
                id=entity.id,
                content_key=entity.content_key or "",
                kind=ContentKind(entity.type.value),
                workflow_id=entity.workflow_id,
                course_plan_id=entity.course_plan_id,
                course_plan_week_id=entity.course_plan_week_id,
                week_number=entity.week_number,
                title=entity.title,
                content_data=entity.activity_data,
                content_markdown=None,
                version=entity.version,
                status=ApprovalStatus(entity.status.value),
                revision_notes=entity.revision_notes,
                prompt_version=entity.prompt_version,
                model_name=entity.model_name,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
            )

        return ContentRecord(
            id=entity.id,
            content_key=entity.content_key or "",
            kind=ContentKind(entity.content_type.value),
            workflow_id=entity.workflow_id,
            course_plan_id=entity.course_plan_id,
            course_plan_week_id=entity.course_plan_week_id,
            week_number=entity.week_number,
            title=entity.title,
            content_data=entity.content_data,
            content_markdown=entity.content_markdown,
            version=entity.version,
            status=ApprovalStatus(entity.status.value),
            revision_notes=entity.revision_notes,
            prompt_version=entity.prompt_version,
            model_name=entity.model_name,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    async def _with_validation(self, record: ContentRecord) -> ContentRecord:
        return replace(
            record,
            validation=await self._latest_validation(
                self._target_type(record), record.id
            ),
        )

    async def _with_validations(
        self, records: list[ContentRecord]
    ) -> list[ContentRecord]:
        """Lampirkan hasil validasi terbaru tanpa query per baris."""
        latest: dict[tuple[str, str], ValidationRecord] = {}

        for target_type, ids in (
            (
                ValidationTargetType.CONTENT,
                [record.id for record in records if not record.kind.is_activity],
            ),
            (
                ValidationTargetType.ACTIVITY,
                [record.id for record in records if record.kind.is_activity],
            ),
        ):
            if not ids:
                continue
            entities = (
                await self._session.execute(
                    select(ValidationResult)
                    .where(
                        ValidationResult.target_type == target_type,
                        ValidationResult.target_id.in_(ids),
                    )
                    .order_by(ValidationResult.created_at.asc())
                )
            ).scalars()
            for entity in entities:
                latest[(target_type.value, entity.target_id)] = _to_validation(
                    entity
                )

        return [
            replace(
                record,
                validation=latest.get(
                    (self._target_type(record).value, record.id)
                ),
            )
            for record in records
        ]

    async def _latest_validation(
        self, target_type: ValidationTargetType, target_id: str
    ) -> ValidationRecord | None:
        entity = (
            await self._session.execute(
                select(ValidationResult)
                .where(
                    ValidationResult.target_type == target_type,
                    ValidationResult.target_id == target_id,
                )
                .order_by(ValidationResult.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        return None if entity is None else _to_validation(entity)

    @staticmethod
    def _target_type(record: ContentRecord) -> ValidationTargetType:
        return (
            ValidationTargetType.ACTIVITY
            if record.kind.is_activity
            else ValidationTargetType.CONTENT
        )


def _to_validation(entity: ValidationResult) -> ValidationRecord:
    return ValidationRecord(
        id=entity.id,
        status=entity.status,
        checks=entity.checks,
        errors=entity.errors,
        warnings=entity.warnings,
        score=float(entity.score) if entity.score is not None else None,
        retry_count=entity.retry_count,
        validated_at=entity.validated_at,
        created_at=entity.created_at,
    )
