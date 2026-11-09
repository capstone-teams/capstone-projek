from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.rps_analysis import RPSAnalysis
from src.models.course_plan_week import CoursePlanWeek
from src.models.course_plan import CoursePlan
from src.models.content import Content, ContentStatus
from src.models.activity import Activity, ActivityStatus, ActivityType
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

    # ==========================================
    # CONTENT (tabel contents)
    # ==========================================
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

    # ==========================================
    # ACTIVITY (tabel activities: Assignment & Quiz)
    # ==========================================
    @staticmethod
    async def get_activity_by_week_id(
        db: AsyncSession,
        course_plan_week_id: str,
        activity_type,
    ) -> Activity | None:
        result = await db.execute(
            select(Activity)
            .where(
                Activity.course_plan_week_id == course_plan_week_id,
                Activity.type == ActivityType(activity_type),
            )
            .order_by(Activity.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_activity_by_id(
        db: AsyncSession,
        activity_id: str,
    ) -> Activity | None:
        result = await db.execute(
            select(Activity).where(Activity.id == activity_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_activity_status(
        db: AsyncSession,
        activity: Activity,
        status: ActivityStatus,
    ) -> Activity:
        activity.status = status

        await db.flush()
        return activity

    @staticmethod
    async def update_activity(
        db: AsyncSession,
        activity: Activity,
        *,
        title: str,
        activity_data: dict,
    ) -> Activity:
        activity.title = title
        activity.activity_data = activity_data
        activity.version += 1
        activity.status = ActivityStatus.DRAFT

        await db.flush()
        return activity

    @staticmethod
    async def create_activity(
        db: AsyncSession,
        *,
        course_plan_week_id: str,
        type,
        title: str,
        activity_data: dict,
    ) -> Activity:
        activity = Activity(
            course_plan_week_id=course_plan_week_id,
            type=ActivityType(type),
            title=title,
            activity_data=activity_data,
            version=1,
            status=ActivityStatus.DRAFT,
        )

        db.add(activity)
        await db.flush()

        return activity
