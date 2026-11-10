"""Akses data hasil Moodle verification (BE-21.2).

Satu-satunya tempat query tabel ``verification_results``. Aturan pembandingan
dan perbaikan berada di :mod:`src.services.verification.service`.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.verification_result import (
    VerificationResult as VerificationResultEntity,
)
from src.services.verification.domain import Discrepancy, VerificationResultRecord

__all__ = ["VerificationRepository"]


class VerificationRepository:
    """Akses data hasil verifikasi di atas ``AsyncSession`` yang di-inject."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, record: VerificationResultRecord
    ) -> VerificationResultRecord:
        entity = VerificationResultEntity(
            workflow_id=record.workflow_id,
            execution_id=record.execution_id,
            status=record.status,
            discrepancies=[item.to_dict() for item in record.discrepancies],
            repaired=[item.to_dict() for item in record.repaired],
            repair_count=record.repair_count,
            repair_rounds=record.repair_rounds,
            summary=dict(record.summary) if record.summary is not None else None,
            error_message=record.error_message,
            verified_at=record.verified_at,
        )
        self._session.add(entity)
        await self._session.commit()
        await self._session.refresh(entity)
        return _to_record(entity)

    async def get(self, verification_id: str) -> VerificationResultRecord | None:
        entity = await self._session.get(VerificationResultEntity, verification_id)
        return _to_record(entity) if entity is not None else None

    async def get_for_workflow(
        self, workflow_id: str, verification_id: str
    ) -> VerificationResultRecord | None:
        """Hasil verifikasi hanya bila milik workflow yang diminta."""
        record = await self.get(verification_id)
        if record is None or record.workflow_id != workflow_id:
            return None
        return record

    async def list_for_workflow(
        self, workflow_id: str
    ) -> list[VerificationResultRecord]:
        """Riwayat verifikasi satu workflow, terbaru lebih dulu."""
        entities = (
            (
                await self._session.execute(
                    select(VerificationResultEntity)
                    .where(VerificationResultEntity.workflow_id == workflow_id)
                    .order_by(
                        VerificationResultEntity.verified_at.desc(),
                        VerificationResultEntity.created_at.desc(),
                    )
                )
            )
            .scalars()
            .all()
        )
        return [_to_record(entity) for entity in entities]


def _to_record(entity: VerificationResultEntity) -> VerificationResultRecord:
    return VerificationResultRecord(
        id=entity.id,
        workflow_id=entity.workflow_id,
        execution_id=entity.execution_id,
        status=entity.status,
        verified_at=entity.verified_at,
        discrepancies=tuple(
            Discrepancy.from_dict(item) for item in entity.discrepancies or []
        ),
        repaired=tuple(Discrepancy.from_dict(item) for item in entity.repaired or []),
        repair_count=entity.repair_count,
        repair_rounds=entity.repair_rounds,
        summary=dict(entity.summary) if entity.summary is not None else None,
        error_message=entity.error_message,
        created_at=entity.created_at,
    )