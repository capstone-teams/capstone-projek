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
 
 
@dataclass(frozen=True) 
class LearningMaterial: 
    title: str 
    content: str 
    description: str = "" 
 
 
@dataclass(frozen=True) 
class LearningMaterialDTO: 
    internal_id: str 
    moodle_module_id: int 
    moodle_section_id: int 
    title: str 
    content: str 
    description: str = "" 
 
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
 
    async def create_section( 
        self, internal_course_id: str, internal_week_id: str, week_number: int, name: str 
    ) -> SectionDTO: ... 
 
    async def update_section( 
        self, internal_course_id: str, internal_week_id: str, *, name: str 
    ) -> SectionDTO: ...

    async def create_learning_material(
        self,
        internal_course_id: str,
        internal_week_id: str,
        internal_material_id: str,
        material: LearningMaterial,
    ) -> LearningMaterialDTO: ...

    async def update_learning_material(
        self, internal_material_id: str, material: LearningMaterial
    ) -> LearningMaterialDTO: ...