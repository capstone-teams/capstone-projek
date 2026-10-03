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

    async def find_course(self, shortname: str) -> CourseDTO | None: ...

    async def get_course_contents(self, internal_course_id: str) -> list[SectionDTO]: ...