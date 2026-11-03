
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.rps_analysis import RPSAnalysis
from src.models.course_plan_week import CoursePlanWeek
from src.models.course_plan import CoursePlan
from src.models.content import Content, ContentStatus
from sqlalchemy.orm import joinedload, selectinload

class ContentGenerationRepository:

    @staticmethod
    async def get_context(
        db: AsyncSession,
        course_plan_id: str,
    ):
        result = await db.execute(
            select(CoursePlan, CoursePlanWeek)
            .join(
                CoursePlanWeek,
                CoursePlanWeek.course_plan_id == CoursePlan.id,
            )
            .where(
                CoursePlan.id == course_plan_id
            )
            # .options(
            #     joinedload(CoursePlan.rps_analysis)
            # )
        )

        rows = result.all()

        if not rows:
            return None

        course_plan = rows[0][0]
        weeks = [row[1] for row in rows]

        return course_plan, weeks
    # async def get_context(
    #     db: AsyncSession,
    #     rps_id: str,
    # ) -> RPSAnalysis | None:
    #     result = await db.execute(
    #         select(RPSAnalysis)
    #         .where(RPSAnalysis.rps_id == rps_id)
    #         .order_by(RPSAnalysis.version.desc())
    #         .limit(1)
    #     )

    @staticmethod
    async def get_by_week_id(
        db: AsyncSession,
        course_plan_week_id: str,
    ) -> Content | None:
        result = await db.execute(
            select(Content)
            .where(Content.course_plan_week_id == course_plan_week_id)
            .order_by(Content.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        content_id: str,
    ) -> Content | None:
        result = await db.execute(
            select(Content).where(Content.id == content_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_status(
        db: AsyncSession,
        content: Content,
        status: ContentStatus,
    ) -> Content:
        content.status = status

        await db.flush()
        return content

    @staticmethod
    async def update_content(
        db: AsyncSession,
        content: Content,
        *,
        title: str,
        content_type,
        content_data: dict,
        content_markdown: str,
        generated_by_agent_run_id: str | None = None,
    ) -> Content:
        content.title = title
        content.content_type = content_type
        content.content_data = content_data
        content.content_markdown = content_markdown
        content.version += 1

        if generated_by_agent_run_id is not None:
            content.generated_by_agent_run_id = generated_by_agent_run_id

        content.status = ContentStatus.DRAFT

        await db.flush()
        return content

    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        course_plan_week_id: str,
        title: str,
        content_type,
        content_data: dict,
        content_markdown: str,
        generated_by_agent_run_id: str | None = None,
    ) -> Content:
        content = Content(
            course_plan_week_id=course_plan_week_id,
            title=title,
            content_type=content_type,
            content_data=content_data,
            content_markdown=content_markdown,
            version=1,
            status=ContentStatus.DRAFT,
            generated_by_agent_run_id=generated_by_agent_run_id,
        )

        db.add(content)
        await db.flush()

        return content
