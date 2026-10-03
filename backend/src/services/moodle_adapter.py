from __future__ import annotations

from typing import Any

from src.services.moodle_adapter_exceptions import (
    MoodleEntityNotFoundError,
    MoodleOperationFailedError,
)
from src.services.moodle_client import MoodleClient
from src.services.moodle_exceptions import MoodleError
from src.services.moodle_integration_interface import CourseDTO, SectionDTO
from src.services.moodle_mapping import IMoodleMappingRepository, MoodleMapping

COURSE_ENTITY_TYPE = "course"


class MoodleAdapter:
    def __init__(self, client: MoodleClient, mapping_repository: IMoodleMappingRepository) -> None:
        self._client = client
        self._mappings = mapping_repository

    async def get_course(self, internal_course_id: str) -> CourseDTO:
        moodle_id = await self._require_moodle_course_id(internal_course_id)
        courses = await self._safe_call("core_course_get_courses", {"ids": [moodle_id]})
        if not courses:
            raise MoodleEntityNotFoundError(
                f"Course '{internal_course_id}' (Moodle ID {moodle_id}) tidak ditemukan di Moodle."
            )
        return self._to_course_dto(internal_course_id, courses[0])

    async def create_course(
        self, internal_course_id: str, fullname: str, shortname: str, category_id: int = 1
    ) -> CourseDTO:
        if await self._mappings.exists(COURSE_ENTITY_TYPE, internal_course_id):
            return await self.get_course(internal_course_id)

        created = await self._safe_call(
            "core_course_create_courses",
            {
                "courses": [
                    {"fullname": fullname, "shortname": shortname, "categoryid": category_id}
                ]
            },
        )
        if not created:
            raise MoodleOperationFailedError(
                f"Moodle tidak mengembalikan course ID untuk '{internal_course_id}'."
            )

        moodle_id = int(created[0]["id"])
        await self._mappings.save(
            MoodleMapping(
                entity_type=COURSE_ENTITY_TYPE,
                internal_id=internal_course_id,
                moodle_id=moodle_id,
            )
        )
        return CourseDTO(
            internal_id=internal_course_id,
            moodle_id=moodle_id,
            fullname=fullname,
            shortname=shortname,
        )

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
        moodle_id = await self._require_moodle_course_id(internal_course_id)
        result = await self._safe_call(
            "core_course_update_courses",
            {"courses": [{"id": moodle_id, **changes}]},
        )
        warnings = result.get("warnings") or []
        if warnings:
            reason = warnings[0].get("message", "alasan tidak diketahui")
            raise MoodleOperationFailedError(
                f"Moodle menolak update course '{internal_course_id}': {reason}"
            )
        return await self.get_course(internal_course_id)

    async def find_course(self, shortname: str) -> CourseDTO | None:
        shortname = shortname.strip()
        if not shortname:
            raise ValueError("shortname tidak boleh kosong")
        result = await self._safe_call(
            "core_course_get_courses_by_field", {"field": "shortname", "value": shortname}
        )
        courses = result.get("courses") or []
        if not courses:
            return None
        moodle_id = int(courses[0]["id"])
        internal_id = await self._mappings.get_internal_id(COURSE_ENTITY_TYPE, moodle_id)
        return self._to_course_dto(internal_id, courses[0])

    async def get_course_contents(self, internal_course_id: str) -> list[SectionDTO]:
        moodle_id = await self._require_moodle_course_id(internal_course_id)
        sections = await self._safe_call("core_course_get_contents", {"courseid": moodle_id})
        return [self._to_section_dto(section) for section in sections]

    async def _require_moodle_course_id(self, internal_course_id: str) -> int:
        moodle_id = await self._mappings.get_moodle_id(COURSE_ENTITY_TYPE, internal_course_id)
        if moodle_id is None:
            raise MoodleEntityNotFoundError(
                f"Course '{internal_course_id}' belum memiliki Moodle course."
            )
        return moodle_id

    async def _safe_call(self, wsfunction: str, params: dict[str, Any]) -> Any:
        try:
            return await self._client.call(wsfunction, params)
        except MoodleError as exc:
            raise MoodleOperationFailedError(
                f"Operasi Moodle '{wsfunction}' gagal: {exc.message}",
                original_error=exc,
            ) from exc

    @staticmethod
    def _to_course_dto(internal_course_id: str | None, raw: dict[str, Any]) -> CourseDTO:
        return CourseDTO(
            internal_id=internal_course_id,
            moodle_id=int(raw["id"]),
            fullname=raw.get("fullname", ""),
            shortname=raw.get("shortname", ""),
            visible=bool(raw.get("visible", 1)),
        )

    @staticmethod
    def _to_section_dto(raw: dict[str, Any]) -> SectionDTO:
        modules = raw.get("modules") or []
        return SectionDTO(
            moodle_section_id=int(raw["id"]),
            name=raw.get("name", ""),
            section_number=int(raw.get("section", 0)),
            module_ids=[int(module["id"]) for module in modules if "id" in module],
        )