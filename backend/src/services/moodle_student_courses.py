"""Course Moodle dari sisi mahasiswa (akses mahasiswa ke hasil generate).

Mahasiswa yang login ke aplikasi melihat course Moodle tempat ia terdaftar
beserta section dan activity yang terlihat oleh mahasiswa, termasuk materi,
resource, assignment, dan quiz hasil eksekusi. Data dibaca melalui token
integrasi backend (frontend tidak memegang token Moodle), sehingga aturan akses
Moodle diterapkan ulang di sini:

- akun aplikasi dicocokkan dengan akun Moodle berdasarkan ``username``;
- hanya course yang terlihat (``visible``) dan tempat mahasiswa terdaftar;
- section dan module yang disembunyikan dosen tidak dikirim;
- course yang tidak memenuhi syarat diperlakukan sama seperti tidak ada (404),
  sehingga mahasiswa tidak dapat menebak course lain.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace

from src.services.moodle_adapter_exceptions import MoodleEntityNotFoundError
from src.services.moodle_integration_service import (
    MoodleCourse,
    MoodleCourseContents,
    MoodleIntegrationService,
)

__all__ = ["StudentCourseService"]

#: Batas pemeriksaan enrolment yang berjalan bersamaan saat menyusun daftar course.
MAX_CONCURRENT_CHECKS = 8


class StudentCourseService:
    """Daftar course, detail course, dan isi course yang boleh dilihat mahasiswa."""

    def __init__(self, moodle: MoodleIntegrationService) -> None:
        self._moodle = moodle

    async def list_courses(self, username: str) -> list[MoodleCourse]:
        """Course terlihat tempat mahasiswa terdaftar, urut seperti daftar Moodle."""
        courses = [course for course in await self._moodle.list_courses() if course.visible]
        limit = asyncio.Semaphore(MAX_CONCURRENT_CHECKS)

        async def check(course: MoodleCourse) -> bool:
            async with limit:
                return await self._is_enrolled(username, course.moodle_course_id)

        enrolled = await asyncio.gather(*(check(course) for course in courses))
        return [course for course, ok in zip(courses, enrolled) if ok]

    async def get_course(self, username: str, moodle_course_id: int) -> MoodleCourse:
        return await self._require_access(username, moodle_course_id)

    async def get_course_contents(
        self, username: str, moodle_course_id: int
    ) -> MoodleCourseContents:
        """Isi course tanpa section dan module yang disembunyikan dari mahasiswa."""
        await self._require_access(username, moodle_course_id)
        contents = await self._moodle.get_course_contents(
            moodle_course_id, with_intros=True
        )
        sections = [
            replace(
                section,
                modules=[module for module in section.modules if module.visible],
            )
            for section in contents.sections
            if section.visible
        ]
        return replace(contents, sections=sections)

    async def _require_access(
        self, username: str, moodle_course_id: int
    ) -> MoodleCourse:
        course = await self._moodle.get_course(moodle_course_id)
        if not course.visible or not await self._is_enrolled(
            username, moodle_course_id
        ):
            raise MoodleEntityNotFoundError(
                f"Course Moodle {moodle_course_id} tidak ditemukan."
            )
        return course

    async def _is_enrolled(self, username: str, moodle_course_id: int) -> bool:
        wanted = username.strip().lower()
        if not wanted:
            return False
        enrolled = await self._moodle.get_enrolled_users(moodle_course_id)
        return any(item.user.username.lower() == wanted for item in enrolled)