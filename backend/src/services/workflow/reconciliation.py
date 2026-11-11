"""Menutup run workflow yang terputus saat server berhenti.

Analisis RPS, penyusunan rencana, pembuatan konten, dan eksekusi Moodle berjalan
**in-process**. Restart container (deploy, reload) mematikan proses di tengah
jalan tanpa sempat menulis status akhir, sehingga workflow tertahan di tahap
"berjalan" dan UI menampilkan progres yang tidak pernah selesai. Saat startup
tidak ada run yang mungkin masih hidup, jadi semuanya ditutup sebagai gagal agar
dosen dapat menjalankan ulang langkahnya.

ponytail: run ditandai gagal tanpa memeriksa apakah operasi Moodle sebagian sudah
diterapkan. Eksekusi memakai ID number yang idempoten, jadi aman diulang; bila
kelak butuh laporan parsial, baca ``execution_operations`` sebelum menutup.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session_factory
from src.models.workflow import Workflow, WorkflowStatus
from src.models.workflow_event import EventType, WorkflowEvent
from src.services.workflow.domain import STAGE_BY_STATUS

__all__ = ["close_interrupted_runs", "reconcile_interrupted_runs"]

logger = logging.getLogger(__name__)

#: Status yang hanya mungkin dipegang selama proses aplikasi masih hidup.
INTERRUPTED_STATUSES = frozenset(
    {
        WorkflowStatus.QUEUED,
        WorkflowStatus.PROCESSING_RPS,
        WorkflowStatus.ANALYZING_RPS,
        WorkflowStatus.PLANNING_COURSE,
        WorkflowStatus.GENERATING_CONTENT,
        WorkflowStatus.VALIDATING,
        WorkflowStatus.EXECUTING_TO_MOODLE,
        WorkflowStatus.VERIFYING,
        WorkflowStatus.RETRYING,
    }
)

FAILED_EVENT = "WORKFLOW_FAILED"
FAILED_MESSAGE = (
    "Proses berhenti karena server dimulai ulang. Silakan jalankan ulang langkah ini."
)


async def reconcile_interrupted_runs() -> int:
    """Tutup seluruh run yang terputus; jumlah workflow yang ditutup dikembalikan."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        return await close_interrupted_runs(session)


async def close_interrupted_runs(session: AsyncSession) -> int:
    """Tandai workflow pada status berjalan sebagai gagal beserta event alasannya."""
    statement = select(Workflow).where(Workflow.status.in_(INTERRUPTED_STATUSES))
    victims = (await session.execute(statement)).scalars().all()
    if not victims:
        return 0

    now = datetime.now(UTC)
    for victim in victims:
        stage = STAGE_BY_STATUS.get(victim.status)
        victim.status = WorkflowStatus.FAILED
        victim.completed_at = now
        victim.updated_at = now
        session.add(
            WorkflowEvent(
                workflow_id=victim.id,
                event_type=EventType.ERROR_FAILURE,
                event=FAILED_EVENT,
                stage=stage,
                message=FAILED_MESSAGE,
            )
        )
    await session.commit()
    logger.warning("%s workflow terputus ditandai gagal setelah server mulai ulang", len(victims))
    return len(victims)
