
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.rps_analysis import RPSAnalysis


class ContentGenerationRepository:

    @staticmethod
    async def get_context(
        db: AsyncSession,
        rps_id: str,
    ) -> RPSAnalysis | None:
        result = await db.execute(
            select(RPSAnalysis)
            .where(RPSAnalysis.rps_id == rps_id)
            .order_by(RPSAnalysis.version.desc())
            .limit(1)
        )

        return result.scalar_one_or_none()
