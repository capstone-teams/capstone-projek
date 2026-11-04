from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


from src.models.content import ContentStatus, ContentType
from src.models.course_plan_week import CoursePlanWeek
from src.services.content.repository import ContentGenerationRepository
from src.services.content.generate_service import generate_week_content


ALLOWED_TRANSITIONS = {
    ContentStatus.DRAFT: {
        ContentStatus.VALIDATED,
    },
    ContentStatus.VALIDATED: {
        ContentStatus.PENDING_REVIEW,
        ContentStatus.DRAFT,
    },
    ContentStatus.PENDING_REVIEW: {
        ContentStatus.APPROVED,
        ContentStatus.REJECTED,
    },
    ContentStatus.REJECTED: {
        ContentStatus.DRAFT,
    },
    ContentStatus.APPROVED: set(),
}

RETRYABLE_STATUSES = {
    ContentStatus.DRAFT,
    ContentStatus.VALIDATED,
    ContentStatus.REJECTED,
}


class InvalidStatusTransition(Exception):
    def __init__(self, current, target):
        super().__init__(
            f"Transisi status tidak diizinkan: {current.value} -> {target.value}"
        )
        self.current = current
        self.target = target


class ContentNotFoundError(Exception):
    def __init__(self, content_id: str):
        super().__init__(f"Konten tidak ditemukan: {content_id}")
        self.content_id = content_id


def _ensure_transition(current, target):
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidStatusTransition(current, target)


class ContentReviewService:

    def __init__(self):
        self.repo = ContentGenerationRepository()

    async def validate_content(
        self,
        db: AsyncSession,
        content_id: str,
    ):
        content = await self._get_content(db, content_id)

        _ensure_transition(content.status, ContentStatus.VALIDATED)

        try:
            await self.repo.update_status(db, content, ContentStatus.VALIDATED)
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
            raise

        return content


    async def retry_content(
        self,
        db: AsyncSession,
        content_id: str,
        additional_prompt: str = "",
        emit_event=None,
        record_trace=None,
    ):
        content = await self._get_content(db, content_id)

        if content.status not in RETRYABLE_STATUSES:
            raise InvalidStatusTransition(content.status, ContentStatus.DRAFT)

        week_number = await db.scalar(
            select(CoursePlanWeek.week_number).where(
                CoursePlanWeek.id == content.course_plan_week_id
            )
        )

        if week_number is None:
            raise ContentNotFoundError(content.course_plan_week_id)

        reject_reason = getattr(content, "reject_reason", None)

        if content.status == ContentStatus.REJECTED and reject_reason:
            additional_prompt = (
                f"{additional_prompt}\nCatatan penolakan: {reject_reason}"
            ).strip()

        material = await generate_week_content(
            db,
            content.course_plan_week_id,
            week_number,
            additional_prompt=additional_prompt,
            emit_event=emit_event,
            record_trace=record_trace,
        )

        try:
            await self.repo.update_content(
                db,
                content,
                title=material.title,
                content_type=ContentType(material.content_type.value),
                content_data=material.content_data.model_dump(mode="json"),
                content_markdown=f"# {material.title}\n\n_Markdown belum dirender._",
            )

            await db.commit()

        except SQLAlchemyError:
            await db.rollback()
            raise

        return content

    async def submit_for_review(
        self,
        db: AsyncSession,
        content_id: str,
    ):
        content = await self._get_content(db, content_id)

        _ensure_transition(content.status, ContentStatus.PENDING_REVIEW)

        try:
            await self.repo.update_status(
                db, content, ContentStatus.PENDING_REVIEW
            )
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
            raise

        return content

    async def approve_content(
        self,
        db: AsyncSession,
        content_id: str,
        reviewer_id: str | None = None,
    ):
        content = await self._get_content(db, content_id)

        _ensure_transition(content.status, ContentStatus.APPROVED)

        try:
            if reviewer_id is not None and hasattr(content, "reviewer_id"):
                content.reviewer_id = reviewer_id

            await self.repo.update_status(db, content, ContentStatus.APPROVED)
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
            raise

        return content

    async def reject_content(
        self,
        db: AsyncSession,
        content_id: str,
        reason: str,
        reviewer_id: str | None = None,
    ):
        content = await self._get_content(db, content_id)

        _ensure_transition(content.status, ContentStatus.REJECTED)

        try:
            if hasattr(content, "reject_reason"):
                content.reject_reason = reason

            if reviewer_id is not None and hasattr(content, "reviewer_id"):
                content.reviewer_id = reviewer_id

            await self.repo.update_status(db, content, ContentStatus.REJECTED)
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
            raise

        return content

    async def _get_content(
        self,
        db: AsyncSession,
        content_id: str,
    ):
        content = await self.repo.get_by_id(db, content_id)

        if content is None:
            raise ContentNotFoundError(content_id)

        return content
