from __future__ import annotations

from src.services.moodle_execution import MoodleExecutionTracker
from src.services.moodle_integration_interface import (
    CourseDTO,
    IMoodleIntegration,
    LearningMaterial,
    LearningMaterialDTO,
    SectionDTO,
)

COURSE = "course"
WEEK = "course_plan_week"
MATERIAL = "learning_material"


class TrackedMoodleIntegration:
    def __init__(self, inner: IMoodleIntegration, tracker: MoodleExecutionTracker) -> None:
        self._inner = inner
        self._tracker = tracker

    async def get_course(self, internal_course_id: str) -> CourseDTO:
        return await self._inner.get_course(internal_course_id)

    async def find_course(self, shortname: str) -> CourseDTO | None:
        return await self._inner.find_course(shortname)

    async def get_course_contents(self, internal_course_id: str) -> list[SectionDTO]:
        return await self._inner.get_course_contents(internal_course_id)

    async def get_weekly_sections(self, internal_course_id: str) -> list[SectionDTO]:
        return await self._inner.get_weekly_sections(internal_course_id)

    async def resolve_week_section(
        self, internal_course_id: str, internal_week_id: str, week_number: int
    ) -> SectionDTO:
        return await self._inner.resolve_week_section(
            internal_course_id, internal_week_id, week_number
        )

    async def create_course(
        self, internal_course_id: str, fullname: str, shortname: str, category_id: int = 1
    ) -> CourseDTO:
        return await self._tracker.run(
            "create_course",
            COURSE,
            internal_course_id,
            lambda: self._inner.create_course(internal_course_id, fullname, shortname, category_id),
            moodle_id_of=lambda course: course.moodle_id,
        )

    async def update_course(
        self,
        internal_course_id: str,
        *,
        fullname: str | None = None,
        shortname: str | None = None,
        visible: bool | None = None,
    ) -> CourseDTO:
        return await self._tracker.run(
            "update_course",
            COURSE,
            internal_course_id,
            lambda: self._inner.update_course(
                internal_course_id, fullname=fullname, shortname=shortname, visible=visible
            ),
            moodle_id_of=lambda course: course.moodle_id,
        )

    async def create_section(
        self, internal_course_id: str, internal_week_id: str, week_number: int, name: str
    ) -> SectionDTO:
        return await self._tracker.run(
            "create_section",
            WEEK,
            internal_week_id,
            lambda: self._inner.create_section(
                internal_course_id, internal_week_id, week_number, name
            ),
            moodle_id_of=lambda section: section.moodle_section_id,
        )

    async def update_section(
        self, internal_course_id: str, internal_week_id: str, *, name: str
    ) -> SectionDTO:
        return await self._tracker.run(
            "update_section",
            WEEK,
            internal_week_id,
            lambda: self._inner.update_section(internal_course_id, internal_week_id, name=name),
            moodle_id_of=lambda section: section.moodle_section_id,
        )

    async def create_learning_material(
        self,
        internal_course_id: str,
        internal_week_id: str,
        internal_material_id: str,
        material: LearningMaterial,
    ) -> LearningMaterialDTO:
        return await self._tracker.run(
            "create_learning_material",
            MATERIAL,
            internal_material_id,
            lambda: self._inner.create_learning_material(
                internal_course_id, internal_week_id, internal_material_id, material
            ),
            moodle_id_of=lambda created: created.moodle_module_id,
        )

    async def update_learning_material(
        self, internal_material_id: str, material: LearningMaterial
    ) -> LearningMaterialDTO:
        return await self._tracker.run(
            "update_learning_material",
            MATERIAL,
            internal_material_id,
            lambda: self._inner.update_learning_material(internal_material_id, material),
            moodle_id_of=lambda updated: updated.moodle_module_id,
        )