from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class CourseDTO:
    internal_id: str | None
    moodle_id: int
    fullname: str
    shortname: str
    visible: bool = True


@dataclass(frozen=True)
class SectionDTO:
    moodle_section_id: int
    name: str
    section_number: int
    module_ids: list[int] = field(default_factory=list)


class IMoodleIntegration(Protocol):
    async def get_course(self, internal_course_id: str) -> CourseDTO: ...

    async def create_course(
        self, internal_course_id: str, fullname: str, shortname: str, category_id: int = 1
    ) -> CourseDTO: ...

    async def update_course(
        self,
        internal_course_id: str,
        *,
        fullname: str | None = None,
        shortname: str | None = None,
        visible: bool | None = None,
    ) -> CourseDTO: ...

    async def find_course(self, shortname: str) -> CourseDTO | None: ...

    async def get_course_contents(self, internal_course_id: str) -> list[SectionDTO]: ...

    async def get_weekly_sections(self, internal_course_id: str) -> list[SectionDTO]: ...

    async def resolve_week_section(
        self, internal_course_id: str, internal_week_id: str, week_number: int
    ) -> SectionDTO: ...