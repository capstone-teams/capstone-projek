import json

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.activity import ActivityStatus
from src.models.content import ContentStatus
from src.models.course_plan_week import CoursePlanWeek
from src.schemas.content import to_row
from src.services.content.generate_service import generate_contents
from src.services.content.repository import ContentGenerationRepository


# ==========================================
# CONTENT (Learning Material / Resource): tabel contents
# ==========================================
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


# ==========================================
# ACTIVITY (Assignment / Quiz): tabel activities
# Tidak ada PENDING_REVIEW / REJECTED; ada EXECUTED (sudah dieksekusi ke Moodle).
# ==========================================
ACTIVITY_ALLOWED_TRANSITIONS = {
    ActivityStatus.DRAFT: {
        ActivityStatus.VALIDATED,
    },
    ActivityStatus.VALIDATED: {
        ActivityStatus.APPROVED,
        ActivityStatus.DRAFT,
    },
    ActivityStatus.APPROVED: {
        ActivityStatus.EXECUTED,
    },
    ActivityStatus.EXECUTED: set(),
}

ACTIVITY_RETRYABLE_STATUSES = {
    ActivityStatus.DRAFT,
    ActivityStatus.VALIDATED,
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


def _ensure_activity_transition(current, target):
    if target not in ACTIVITY_ALLOWED_TRANSITIONS[current]:
        raise InvalidStatusTransition(current, target)


def _value(x) -> str:
    return getattr(x, "value", x)


def _previous_version_text(title: str, data: dict | None) -> str:
    """Versi sekarang (yang akan ditimpa) sebagai teks untuk prompt regenerasi.

    Traceability dibuang karena diisi ulang oleh backend, bukan oleh LLM.
    """
    body = {k: v for k, v in (data or {}).items() if k != "traceability"}
    return json.dumps({"title": title, **body}, ensure_ascii=False, indent=2)


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
        revision_notes: str = "",
    ):
        content = await self._get_content(db, content_id)

        if content.status not in RETRYABLE_STATUSES:
            raise InvalidStatusTransition(content.status, ContentStatus.DRAFT)

        week = await db.get(CoursePlanWeek, content.course_plan_week_id)

        if week is None:
            raise ContentNotFoundError(content.course_plan_week_id)

        reject_reason = getattr(content, "reject_reason", None)

        if content.status == ContentStatus.REJECTED and reject_reason:
            revision_notes = (
                f"{revision_notes}\nCatatan penolakan: {reject_reason}"
            ).strip()

        # save=False: hasil disimpan di bawah ke baris yang sudah ada.
        results = await generate_contents(
            db,
            week.course_plan_id,
            week_numbers=[week.week_number],
            content_types=[_value(content.content_type)],
            additional_prompt=additional_prompt,
            previous_version=_previous_version_text(content.title, content.content_data),
            revision_notes=revision_notes,
            emit_event=emit_event,
            record_trace=record_trace,
            save=False,
        )

        result = results[0]

        if result.error is not None:
            raise result.error

        row = to_row(result.content_type, result.material, result.ctx)

        try:
            await self.repo.update_content(
                db,
                content,
                title=row["title"],
                content_type=row["content_type"],
                content_data=row["content_data"],
                content_markdown=row["content_markdown"],
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


class ActivityReviewService:
    """Alur review untuk Assignment dan Quiz (tabel activities)."""

    def __init__(self):
        self.repo = ContentGenerationRepository()

    async def validate_activity(
        self,
        db: AsyncSession,
        activity_id: str,
    ):
        activity = await self._get_activity(db, activity_id)

        _ensure_activity_transition(activity.status, ActivityStatus.VALIDATED)

        await self._set_status(db, activity, ActivityStatus.VALIDATED)

        return activity

    async def retry_activity(
        self,
        db: AsyncSession,
        activity_id: str,
        additional_prompt: str = "",
        emit_event=None,
        record_trace=None,
        revision_notes: str = "",
    ):
        activity = await self._get_activity(db, activity_id)

        if activity.status not in ACTIVITY_RETRYABLE_STATUSES:
            raise InvalidStatusTransition(activity.status, ActivityStatus.DRAFT)

        week = await db.get(CoursePlanWeek, activity.course_plan_week_id)

        if week is None:
            raise ContentNotFoundError(activity.course_plan_week_id)

        results = await generate_contents(
            db,
            week.course_plan_id,
            week_numbers=[week.week_number],
            content_types=[_value(activity.type)],
            additional_prompt=additional_prompt,
            previous_version=_previous_version_text(activity.title, activity.activity_data),
            revision_notes=revision_notes,
            emit_event=emit_event,
            record_trace=record_trace,
            save=False,
        )

        result = results[0]

        if result.error is not None:
            raise result.error

        row = to_row(result.content_type, result.material, result.ctx)

        try:
            await self.repo.update_activity(
                db,
                activity,
                title=row["title"],
                activity_data=row["activity_data"],
            )
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
            raise

        return activity

    async def approve_activity(
        self,
        db: AsyncSession,
        activity_id: str,
    ):
        activity = await self._get_activity(db, activity_id)

        _ensure_activity_transition(activity.status, ActivityStatus.APPROVED)

        await self._set_status(db, activity, ActivityStatus.APPROVED)

        return activity

    async def mark_executed(
        self,
        db: AsyncSession,
        activity_id: str,
    ):
        """Dipanggil setelah aktivitas berhasil dieksekusi ke Moodle."""
        activity = await self._get_activity(db, activity_id)

        _ensure_activity_transition(activity.status, ActivityStatus.EXECUTED)

        await self._set_status(db, activity, ActivityStatus.EXECUTED)

        return activity

    async def _set_status(
        self,
        db: AsyncSession,
        activity,
        status: ActivityStatus,
    ) -> None:
        try:
            await self.repo.update_activity_status(db, activity, status)
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
            raise

    async def _get_activity(
        self,
        db: AsyncSession,
        activity_id: str,
    ):
        activity = await self.repo.get_activity_by_id(db, activity_id)

        if activity is None:
            raise ContentNotFoundError(activity_id)

        return activity
