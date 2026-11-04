"""Service baca course, course plan, dan konten mingguan.

Read-only: tidak ada operasi tulis di sini. Tujuannya satu — membuat data yang
sudah ada di database (termasuk data contoh ``scripts/seed_sample_course.py``)
dapat dibaca lewat API sebelum generator (BE-14) mendarat.

Scoping akses dilakukan di query, bukan di route: setiap pencarian course selalu
menyertakan ``instructor_id`` pemilik, sehingga course milik dosen lain berhenti
sebagai ``404 RESOURCE_NOT_FOUND`` yang sama dengan course yang tidak ada.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Activity, Content, Course, CoursePlan, CoursePlanWeek
from src.services.course.errors import CourseNotFoundError

__all__ = ["CourseReadService"]


class CourseReadService:
    """Query baca untuk endpoint ``/courses`` (design-api §8–§10)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @classmethod
    def from_session(cls, session: AsyncSession) -> CourseReadService:
        return cls(session)

    async def list_courses(self, *, instructor_id: str) -> list[Course]:
        result = await self._session.execute(
            select(Course)
            .where(Course.instructor_id == instructor_id)
            .order_by(Course.created_at)
        )
        return list(result.scalars().all())

    async def get_course(self, *, course_id: str, instructor_id: str) -> Course:
        course = (
            await self._session.execute(
                select(Course).where(
                    Course.id == course_id, Course.instructor_id == instructor_id
                )
            )
        ).scalar_one_or_none()
        if course is None:
            raise CourseNotFoundError(course_id)
        return course

    async def get_plan(self, *, course_id: str) -> CoursePlan | None:
        """Rencana dengan versi tertinggi; ``None`` bila belum ada."""
        return (
            await self._session.execute(
                select(CoursePlan)
                .where(CoursePlan.course_id == course_id)
                .order_by(CoursePlan.version.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def list_weeks(self, *, plan_id: str) -> list[CoursePlanWeek]:
        result = await self._session.execute(
            select(CoursePlanWeek)
            .where(CoursePlanWeek.course_plan_id == plan_id)
            .order_by(CoursePlanWeek.week_number)
        )
        return list(result.scalars().all())

    async def list_contents(self, *, week_ids: list[str]) -> list[Content]:
        """Konten semua minggu, versi terbaru lebih dulu.

        Pemanggil memilih entri pertama per ``(minggu, jenis)`` sehingga hanya
        versi terbaru yang tampil tanpa menghapus riwayat versi lama.
        """
        if not week_ids:
            return []
        result = await self._session.execute(
            select(Content)
            .where(Content.course_plan_week_id.in_(week_ids))
            .order_by(Content.version.desc())
        )
        return list(result.scalars().all())

    async def list_activities(self, *, week_ids: list[str]) -> list[Activity]:
        """Aktivitas semua minggu, versi terbaru lebih dulu (lihat list_contents)."""
        if not week_ids:
            return []
        result = await self._session.execute(
            select(Activity)
            .where(Activity.course_plan_week_id.in_(week_ids))
            .order_by(Activity.version.desc())
        )
        return list(result.scalars().all())
