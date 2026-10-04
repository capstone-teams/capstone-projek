from __future__ import annotations

from dataclasses import replace

from src.services.moodle_adapter_exceptions import (
    MoodleEntityNotFoundError,
    MoodleOperationFailedError,
)
from src.services.moodle_integration_interface import (
    CourseDTO,
    LearningMaterial,
    LearningMaterialDTO,
    SectionDTO,
)


class MockMoodleIntegration:
    def __init__(self) -> None:
        self._courses: dict[str, CourseDTO] = {}
        self._sections: dict[str, list[SectionDTO]] = {}
        self._week_links: dict[str, int] = {}
        self._materials: dict[str, tuple[str, LearningMaterialDTO]] = {}
        self._next_course_id = 1
        self._next_section_id = 100
        self._next_module_id = 500

    async def get_course(self, internal_course_id: str) -> CourseDTO:
        return self._require_course(internal_course_id)

    async def create_course(
        self, internal_course_id: str, fullname: str, shortname: str, category_id: int = 1
    ) -> CourseDTO:
        existing = self._courses.get(internal_course_id)
        if existing is not None:
            return existing
        self._ensure_shortname_free(shortname)
        course = CourseDTO(
            internal_id=internal_course_id,
            moodle_id=self._next_course_id,
            fullname=fullname,
            shortname=shortname,
        )
        self._next_course_id += 1
        self._courses[internal_course_id] = course
        self._sections[internal_course_id] = [self._new_section("General", 0)]
        return course

    async def update_course(
        self,
        internal_course_id: str,
        *,
        fullname: str | None = None,
        shortname: str | None = None,
        visible: bool | None = None,
    ) -> CourseDTO:
        fields = {"fullname": fullname, "shortname": shortname, "visible": visible}
        changes = {key: value for key, value in fields.items() if value is not None}
        if not changes:
            raise ValueError("update_course membutuhkan minimal satu field yang diubah")
        course = self._require_course(internal_course_id)
        if "shortname" in changes and changes["shortname"] != course.shortname:
            self._ensure_shortname_free(changes["shortname"])
        updated = replace(course, **changes)
        self._courses[internal_course_id] = updated
        return updated

    async def find_course(self, shortname: str) -> CourseDTO | None:
        shortname = shortname.strip()
        if not shortname:
            raise ValueError("shortname tidak boleh kosong")
        return next((c for c in self._courses.values() if c.shortname == shortname), None)

    async def get_course_contents(self, internal_course_id: str) -> list[SectionDTO]:
        self._require_course(internal_course_id)
        return sorted(self._sections[internal_course_id], key=lambda s: s.section_number)

    async def get_weekly_sections(self, internal_course_id: str) -> list[SectionDTO]:
        sections = await self.get_course_contents(internal_course_id)
        return [section for section in sections if section.section_number > 0]

    async def resolve_week_section(
        self, internal_course_id: str, internal_week_id: str, week_number: int
    ) -> SectionDTO:
        if week_number < 1:
            raise ValueError("week_number harus minimal 1")
        sections = await self.get_weekly_sections(internal_course_id)
        linked_id = self._week_links.get(internal_week_id)
        if linked_id is not None:
            return self._section_by_id(internal_course_id, linked_id)
        section = next((s for s in sections if s.section_number == week_number), None)
        if section is None:
            raise MoodleEntityNotFoundError(
                f"Course '{internal_course_id}' belum memiliki section untuk minggu {week_number}."
            )
        self._week_links[internal_week_id] = section.moodle_section_id
        return section

    async def create_section(
        self, internal_course_id: str, internal_week_id: str, week_number: int, name: str
    ) -> SectionDTO:
        self._require_course(internal_course_id)
        if week_number < 1:
            raise ValueError("week_number harus minimal 1")
        if not name.strip():
            raise ValueError("name tidak boleh kosong")
        linked_id = self._week_links.get(internal_week_id)
        if linked_id is not None:
            return self._section_by_id(internal_course_id, linked_id)
        sections = self._sections[internal_course_id]
        section = next((s for s in sections if s.section_number == week_number), None)
        if section is None:
            section = self._new_section(name, week_number)
            sections.append(section)
        self._week_links[internal_week_id] = section.moodle_section_id
        return section

    async def update_section(
        self, internal_course_id: str, internal_week_id: str, *, name: str
    ) -> SectionDTO:
        self._require_course(internal_course_id)
        if not name.strip():
            raise ValueError("name tidak boleh kosong")
        linked_id = self._week_links.get(internal_week_id)
        if linked_id is None:
            raise MoodleEntityNotFoundError(
                f"Minggu '{internal_week_id}' belum memiliki section di course '{internal_course_id}'."
            )
        section = self._section_by_id(internal_course_id, linked_id)
        updated = replace(section, name=name)
        self._swap_section(internal_course_id, section, updated)
        return updated

    async def create_learning_material(
        self,
        internal_course_id: str,
        internal_week_id: str,
        internal_material_id: str,
        material: LearningMaterial,
    ) -> LearningMaterialDTO:
        self._require_course(internal_course_id)
        self._validate_material(material)
        existing = self._materials.get(internal_material_id)
        if existing is not None:
            return existing[1]
        linked_id = self._week_links.get(internal_week_id)
        if linked_id is None:
            raise MoodleEntityNotFoundError(
                f"Minggu '{internal_week_id}' belum memiliki section di course '{internal_course_id}'."
            )
        section = self._section_by_id(internal_course_id, linked_id)
        module_id = self._next_module_id
        self._next_module_id += 1
        created = LearningMaterialDTO(
            internal_id=internal_material_id,
            moodle_module_id=module_id,
            moodle_section_id=section.moodle_section_id,
            title=material.title,
            content=material.content,
            description=material.description,
        )
        self._materials[internal_material_id] = (internal_course_id, created)
        self._swap_section(
            internal_course_id, section, replace(section, module_ids=[*section.module_ids, module_id])
        )
        return created

    async def update_learning_material(
        self, internal_material_id: str, material: LearningMaterial
    ) -> LearningMaterialDTO:
        self._validate_material(material)
        existing = self._materials.get(internal_material_id)
        if existing is None:
            raise MoodleEntityNotFoundError(
                f"Learning material '{internal_material_id}' belum dibuat di Moodle."
            )
        internal_course_id, current = existing
        updated = replace(
            current,
            title=material.title,
            content=material.content,
            description=material.description,
        )
        self._materials[internal_material_id] = (internal_course_id, updated)
        return updated

    def _swap_section(
        self, internal_course_id: str, old: SectionDTO, new: SectionDTO
    ) -> None:
        sections = self._sections[internal_course_id]
        sections[sections.index(old)] = new

    @staticmethod
    def _validate_material(material: LearningMaterial) -> None:
        if not material.title.strip():
            raise ValueError("title tidak boleh kosong")
        if not material.content.strip():
            raise ValueError("content tidak boleh kosong")

    def _require_course(self, internal_course_id: str) -> CourseDTO:
        course = self._courses.get(internal_course_id)
        if course is None:
            raise MoodleEntityNotFoundError(f"Course '{internal_course_id}' tidak ditemukan.")
        return course

    def _ensure_shortname_free(self, shortname: str) -> None:
        if any(course.shortname == shortname for course in self._courses.values()):
            raise MoodleOperationFailedError(f"Shortname '{shortname}' sudah dipakai course lain.")

    def _section_by_id(self, internal_course_id: str, section_id: int) -> SectionDTO:
        section = next(
            (s for s in self._sections[internal_course_id] if s.moodle_section_id == section_id),
            None,
        )
        if section is None:
            raise MoodleEntityNotFoundError(
                f"Section {section_id} tidak ditemukan di course '{internal_course_id}'."
            )
        return section

    def _new_section(self, name: str, number: int) -> SectionDTO:
        section = SectionDTO(
            moodle_section_id=self._next_section_id, name=name, section_number=number
        )
        self._next_section_id += 1
        return section