from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from src.services.moodle_adapter_exceptions import MoodleEntityNotFoundError
from src.services.moodle_client import MoodleClient
from src.services.moodle_exceptions import MoodleAPIError, MoodleError

logger = logging.getLogger(__name__)

SITE_INFO_FUNCTION = "core_webservice_get_site_info"
GET_COURSES_FUNCTION = "core_course_get_courses"
GET_COURSES_BY_FIELD_FUNCTION = "core_course_get_courses_by_field"
GET_CONTENTS_FUNCTION = "core_course_get_contents"
CREATE_COURSES_FUNCTION = "core_course_create_courses"
UPDATE_COURSES_FUNCTION = "core_course_update_courses"
UPDATE_COURSE_FORMAT_FUNCTION = "core_courseformat_update_course"
RENAME_SECTION_FUNCTION = "core_update_inplace_editable"
UPDATE_SECTION_FUNCTION = "local_capstonebridge_update_section"
GET_PAGES_FUNCTION = "mod_page_get_pages_by_courses"
GET_USERS_BY_FIELD_FUNCTION = "core_user_get_users_by_field"
CREATE_USERS_FUNCTION = "core_user_create_users"
ENROL_USERS_FUNCTION = "enrol_manual_enrol_users"
GET_ENROLLED_USERS_FUNCTION = "core_enrol_get_enrolled_users"

#: Role bawaan Moodle yang dipakai integrasi (ID default instalasi Moodle).
ROLE_IDS = {"teacher": 3, "student": 5}  # teacher = editingteacher

MONITORED_FUNCTIONS = (
    SITE_INFO_FUNCTION,
    GET_COURSES_FUNCTION,
    GET_COURSES_BY_FIELD_FUNCTION,
    GET_CONTENTS_FUNCTION,
    CREATE_COURSES_FUNCTION,
    UPDATE_COURSES_FUNCTION,
    "core_course_edit_section",
    UPDATE_COURSE_FORMAT_FUNCTION,
    RENAME_SECTION_FUNCTION,
    UPDATE_SECTION_FUNCTION,
    GET_PAGES_FUNCTION,
)

SITE_COURSE_FORMAT = "site"
PAGE_MODULE_NAME = "page"

CONNECTED_STATUS = "CONNECTED"
DISCONNECTED_STATUS = "DISCONNECTED"


@dataclass(frozen=True)
class FunctionAvailability:
    name: str
    available: bool


@dataclass(frozen=True)
class MoodleStatus:
    connected: bool
    site_name: str
    release: str
    version: str
    functions: list[FunctionAvailability]

    @property
    def all_functions_available(self) -> bool:
        return all(function.available for function in self.functions)

    @property
    def status(self) -> str:
        return CONNECTED_STATUS if self.connected else DISCONNECTED_STATUS

    @property
    def message(self) -> str:
        return f"Terhubung ke {self.site_name} (Moodle {self.release})."


@dataclass(frozen=True)
class MoodleCourse:
    moodle_course_id: int
    fullname: str
    shortname: str
    visible: bool
    summary: str = ""
    category_id: int | None = None
    course_format: str = "topics"
    category: str | None = None

    @property
    def id(self) -> int:
        return self.moodle_course_id


@dataclass(frozen=True)
class MoodleModule:
    moodle_module_id: int
    name: str
    modname: str
    visible: bool
    description: str = ""
    content: str | None = None


@dataclass(frozen=True)
class MoodleSection:
    moodle_section_id: int
    section_number: int
    name: str
    summary: str
    visible: bool
    modules: list[MoodleModule] = field(default_factory=list)


@dataclass(frozen=True)
class MoodleCourseContents:
    moodle_course_id: int
    sections: list[MoodleSection]


@dataclass(frozen=True)
class MoodleUser:
    moodle_user_id: int
    username: str
    fullname: str
    email: str = ""


@dataclass(frozen=True)
class MoodleEnrolment:
    user: MoodleUser
    roles: tuple[str, ...]


@dataclass(frozen=True)
class SectionWriteResult:
    section: MoodleSection
    created: bool


class MoodleIntegrationService:
    def __init__(self, client: MoodleClient) -> None:
        self._client = client

    @property
    def client(self) -> MoodleClient:
        """Client dasar untuk operasi activity (BE-12) pada cakupan FULL."""
        return self._client

    async def get_status(self) -> MoodleStatus:
        # Probe status harus cepat dan jujur: tidak di-retry.
        info = _expect_dict(await self._client.call(SITE_INFO_FUNCTION, retry=False), SITE_INFO_FUNCTION)
        available = {item.get("name") for item in info.get("functions") or []}
        return MoodleStatus(
            connected=True,
            site_name=info.get("sitename", ""),
            release=info.get("release", ""),
            version=str(info.get("version", "")),
            functions=[
                FunctionAvailability(name=name, available=name in available)
                for name in MONITORED_FUNCTIONS
            ],
        )

    async def list_courses(self) -> list[MoodleCourse]:
        raw_courses = _expect_list(await self._client.call(GET_COURSES_FUNCTION), GET_COURSES_FUNCTION)
        return [
            _to_course(raw)
            for raw in raw_courses
            if raw.get("format") != SITE_COURSE_FORMAT
        ]

    async def get_course(self, moodle_course_id: int) -> MoodleCourse:
        raw_courses = _expect_list(
            await self._client.call(
                GET_COURSES_FUNCTION,
                {"options": {"ids": [moodle_course_id]}},
            ),
            GET_COURSES_FUNCTION,
        )
        if not raw_courses:
            raise MoodleEntityNotFoundError(f"Course Moodle {moodle_course_id} tidak ditemukan.")
        return _to_course(raw_courses[0])

    async def get_course_by_shortname(self, shortname: str) -> MoodleCourse:
        """Baca course berdasarkan shortname (unik di Moodle)."""
        if not shortname.strip():
            raise ValueError("shortname tidak boleh kosong")
        payload = _expect_dict(
            await self._client.call(
                GET_COURSES_BY_FIELD_FUNCTION,
                {"field": "shortname", "value": shortname.strip()},
            ),
            GET_COURSES_BY_FIELD_FUNCTION,
        )
        courses = [
            raw
            for raw in payload.get("courses") or []
            if raw.get("format") != SITE_COURSE_FORMAT
        ]
        if not courses:
            raise MoodleEntityNotFoundError(
                f"Course Moodle dengan shortname '{shortname}' tidak ditemukan."
            )
        return _to_course(courses[0])

    async def update_course(
        self,
        moodle_course_id: int,
        *,
        fullname: str | None = None,
        shortname: str | None = None,
        summary: str | None = None,
        visible: bool | None = None,
    ) -> MoodleCourse:
        """Perbarui field course yang diberikan; field ``None`` tidak diubah."""
        changes: dict[str, Any] = {}
        for field_name, value in (("fullname", fullname), ("shortname", shortname)):
            if value is not None:
                if not value.strip():
                    raise ValueError(f"{field_name} tidak boleh kosong")
                changes[field_name] = value.strip()
        if summary is not None:
            changes["summary"] = summary
            changes["summaryformat"] = 1  # FORMAT_HTML
        if visible is not None:
            changes["visible"] = int(visible)
        if not changes:
            raise ValueError("tidak ada field course yang diperbarui")

        await self.get_course(moodle_course_id)
        payload = await self._client.call(
            UPDATE_COURSES_FUNCTION,
            {"courses": [{"id": moodle_course_id, **changes}]},
        )
        warnings = payload.get("warnings") if isinstance(payload, dict) else None
        if warnings:
            # Moodle melaporkan kegagalan per course sebagai warning, bukan exception.
            warning = warnings[0]
            raise MoodleAPIError(
                warning.get("message") or "Moodle menolak perubahan course",
                code=warning.get("warningcode") or "update_failed",
                wsfunction=UPDATE_COURSES_FUNCTION,
            )
        return await self.get_course(moodle_course_id)

    async def get_course_contents(self, moodle_course_id: int) -> MoodleCourseContents:
        await self.get_course(moodle_course_id)
        sections = await self._fetch_sections(moodle_course_id)
        if any(
            module.modname == PAGE_MODULE_NAME
            for section in sections
            for module in section.modules
        ):
            pages = await self._fetch_page_contents(moodle_course_id)
            sections = [_with_page_content(section, pages) for section in sections]
        return MoodleCourseContents(
            moodle_course_id=moodle_course_id,
            sections=sections,
        )

    async def create_course(
        self,
        fullname: str,
        shortname: str,
        category_id: int,
    ) -> MoodleCourse:
        created = _expect_list(
            await self._client.call(
                CREATE_COURSES_FUNCTION,
                {
                    "courses": [
                        {
                            "fullname": fullname,
                            "shortname": shortname,
                            "categoryid": category_id,
                        }
                    ]
                },
            ),
            CREATE_COURSES_FUNCTION,
        )
        if not created or "id" not in created[0]:
            raise MoodleAPIError(
                "Moodle tidak mengembalikan ID course baru",
                code="invalid_response",
                wsfunction=CREATE_COURSES_FUNCTION,
            )
        return await self.get_course(int(created[0]["id"]))

    async def save_section(
        self,
        moodle_course_id: int,
        name: str,
        section_number: int | None = None,
        *,
        summary: str | None = None,
        section_id: int | None = None,
    ) -> SectionWriteResult:
        """Buat atau perbarui satu section course.

        Section target dicari berdasarkan ``section_id`` (mis. dari tabel mapping)
        lebih dulu, lalu ``section_number``; bila keduanya tidak ditemukan, section
        baru ditambahkan. Tanpa ``summary`` hanya nama yang diubah
        (``core_update_inplace_editable``); dengan ``summary`` nama dan ringkasan
        HTML disimpan sekaligus lewat ``local_capstonebridge_update_section``.

        Bila ``section_number`` lebih besar dari section terakhir, section kosong
        di antaranya ikut ditambahkan supaya nomor section tetap sama dengan nomor
        minggu walaupun minggu sebelumnya gagal disimpan.
        """
        course = await self.get_course(moodle_course_id)
        before = await self._fetch_sections(moodle_course_id)

        target = None
        if section_id is not None:
            target = next(
                (s for s in before if s.moodle_section_id == section_id),
                None,
            )
        if target is None and section_number is not None:
            target = next(
                (s for s in before if s.section_number == section_number),
                None,
            )
        created = target is None

        if target is None:
            target = await self._add_section(moodle_course_id, before)
            while section_number is not None and target.section_number < section_number:
                target = await self._add_section(
                    moodle_course_id,
                    await self._fetch_sections(moodle_course_id),
                )

        if summary is None:
            await self._client.call(
                RENAME_SECTION_FUNCTION,
                {
                    "component": f"format_{course.course_format}",
                    "itemtype": "sectionname",
                    "itemid": target.moodle_section_id,
                    "value": name,
                },
            )
        else:
            await self._client.call(
                UPDATE_SECTION_FUNCTION,
                {
                    "courseid": moodle_course_id,
                    "sectionid": target.moodle_section_id,
                    "name": name,
                    "summary": summary,
                },
            )

        for section in await self._fetch_sections(moodle_course_id):
            if section.moodle_section_id == target.moodle_section_id:
                return SectionWriteResult(section=section, created=created)
        raise MoodleAPIError(
            "Section tidak ditemukan setelah disimpan",
            code="section_not_found",
            wsfunction=(
                UPDATE_SECTION_FUNCTION
                if summary is not None
                else RENAME_SECTION_FUNCTION
            ),
        )

    # --- User dan enrolment (BE-04.5) ----------------------------------------

    async def get_user_by_username(self, username: str) -> MoodleUser | None:
        """Cari akun Moodle berdasarkan username; ``None`` bila tidak ada."""
        if not username.strip():
            raise ValueError("username tidak boleh kosong")
        users = _expect_list(
            await self._client.call(
                GET_USERS_BY_FIELD_FUNCTION,
                {"field": "username", "values": [username.strip().lower()]},
            ),
            GET_USERS_BY_FIELD_FUNCTION,
        )
        return _to_user(users[0]) if users else None

    async def create_user(
        self,
        *,
        username: str,
        password: str,
        firstname: str,
        lastname: str,
        email: str,
    ) -> MoodleUser:
        """Buat akun Moodle (auth manual). Password tidak pernah dicatat di log."""
        values = {
            "username": username,
            "password": password,
            "firstname": firstname,
            "lastname": lastname,
            "email": email,
        }
        empty = [name for name, value in values.items() if not value.strip()]
        if empty:
            raise ValueError(f"field akun wajib diisi: {', '.join(empty)}")
        created = _expect_list(
            await self._client.call(
                CREATE_USERS_FUNCTION,
                {
                    "users": [
                        {
                            **values,
                            "username": username.strip().lower(),
                            "auth": "manual",
                        }
                    ]
                },
            ),
            CREATE_USERS_FUNCTION,
        )
        if not created or "id" not in created[0]:
            raise MoodleAPIError(
                "Moodle tidak mengembalikan ID akun baru",
                code="invalid_response",
                wsfunction=CREATE_USERS_FUNCTION,
            )
        user = await self.get_user_by_username(username)
        if user is None:
            raise MoodleAPIError(
                "Akun tidak ditemukan setelah dibuat",
                code="user_not_found",
                wsfunction=CREATE_USERS_FUNCTION,
            )
        return user

    async def enrol_users(
        self,
        moodle_course_id: int,
        enrolments: Sequence[tuple[int, str]],
    ) -> None:
        """Daftarkan user ke course dengan role ``teacher`` atau ``student`` (enrolment manual).

        Aman diulang: mendaftarkan user yang sudah terdaftar tidak membuat enrolment ganda.
        """
        if not enrolments:
            raise ValueError("daftar enrolment kosong")
        unknown = sorted({role for _, role in enrolments} - ROLE_IDS.keys())
        if unknown:
            raise ValueError(
                f"role tidak dikenal: {unknown}; gunakan 'teacher' atau 'student'"
            )
        await self.get_course(moodle_course_id)
        await self._client.call(
            ENROL_USERS_FUNCTION,
            {
                "enrolments": [
                    {
                        "roleid": ROLE_IDS[role],
                        "userid": user_id,
                        "courseid": moodle_course_id,
                    }
                    for user_id, role in enrolments
                ]
            },
        )

    async def get_enrolled_users(
        self,
        moodle_course_id: int,
    ) -> list[MoodleEnrolment]:
        """Daftar user yang terdaftar di course beserta role-nya."""
        users = _expect_list(
            await self._client.call(
                GET_ENROLLED_USERS_FUNCTION,
                {"courseid": moodle_course_id},
            ),
            GET_ENROLLED_USERS_FUNCTION,
        )
        return [
            MoodleEnrolment(
                user=_to_user(raw),
                roles=tuple(role.get("shortname", "") for role in raw.get("roles") or []),
            )
            for raw in users
        ]

    async def _add_section(
        self,
        moodle_course_id: int,
        existing: list[MoodleSection],
    ) -> MoodleSection:
        await self._client.call(
            UPDATE_COURSE_FORMAT_FUNCTION,
            {
                "action": "section_add",
                "courseid": moodle_course_id,
            },
        )
        known_ids = {section.moodle_section_id for section in existing}
        added = [
            section
            for section in await self._fetch_sections(moodle_course_id)
            if section.moodle_section_id not in known_ids
        ]
        if not added:
            raise MoodleAPIError(
                "Moodle tidak membuat section baru",
                code="section_not_created",
                wsfunction=UPDATE_COURSE_FORMAT_FUNCTION,
            )
        return max(added, key=lambda section: section.section_number)

    async def _fetch_sections(
        self,
        moodle_course_id: int,
    ) -> list[MoodleSection]:
        raw_sections = _expect_list(
            await self._client.call(
                GET_CONTENTS_FUNCTION,
                {"courseid": moodle_course_id},
            ),
            GET_CONTENTS_FUNCTION,
        )
        return [_to_section(raw) for raw in raw_sections]

    async def _fetch_page_contents(
        self,
        moodle_course_id: int,
    ) -> dict[int, str]:
        try:
            payload = await self._client.call(
                GET_PAGES_FUNCTION,
                {"courseids": [moodle_course_id]},
            )
        except MoodleError as exc:
            logger.warning(
                "Konten page tidak dapat dibaca: type=%s code=%s",
                exc.error_type,
                exc.code,
            )
            return {}
        pages = payload.get("pages") if isinstance(payload, dict) else None
        return {
            int(page["coursemodule"]): page.get("content", "")
            for page in pages or []
            if "coursemodule" in page
        }


def _expect_list(
    payload: Any,
    wsfunction: str,
) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise MoodleAPIError(
            "Respons Moodle tidak sesuai format yang diharapkan",
            code="invalid_response",
            wsfunction=wsfunction,
        )
    return payload


def _expect_dict(
    payload: Any,
    wsfunction: str,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise MoodleAPIError(
            "Respons Moodle tidak sesuai format yang diharapkan",
            code="invalid_response",
            wsfunction=wsfunction,
        )
    return payload


def _to_course(raw: dict[str, Any]) -> MoodleCourse:
    category_id = raw.get("categoryid")
    return MoodleCourse(
        moodle_course_id=int(raw["id"]),
        fullname=raw.get("fullname", ""),
        shortname=raw.get("shortname", ""),
        visible=bool(raw.get("visible", 1)),
        summary=raw.get("summary") or "",
        category_id=int(category_id) if category_id is not None else None,
        course_format=raw.get("format") or "topics",
        category=raw.get("categoryname") or None,
    )


def _to_user(raw: dict[str, Any]) -> MoodleUser:
    return MoodleUser(
        moodle_user_id=int(raw["id"]),
        username=raw.get("username", ""),
        fullname=raw.get("fullname")
        or f"{raw.get('firstname', '')} {raw.get('lastname', '')}".strip(),
        email=raw.get("email") or "",
    )


def _to_module(raw: dict[str, Any]) -> MoodleModule:
    return MoodleModule(
        moodle_module_id=int(raw["id"]),
        name=raw.get("name", ""),
        modname=raw.get("modname", ""),
        visible=bool(raw.get("visible", 1)),
        description=raw.get("description") or "",
    )


def _to_section(raw: dict[str, Any]) -> MoodleSection:
    return MoodleSection(
        moodle_section_id=int(raw["id"]),
        section_number=int(raw.get("section", 0)),
        name=raw.get("name", ""),
        summary=raw.get("summary") or "",
        visible=bool(raw.get("visible", 1)),
        modules=[
            _to_module(module)
            for module in raw.get("modules") or []
            if "id" in module
        ],
    )


def _with_page_content(
    section: MoodleSection,
    pages: dict[int, str],
) -> MoodleSection:
    modules = [
        replace(module, content=pages.get(module.moodle_module_id))
        if module.modname == PAGE_MODULE_NAME
        else module
        for module in section.modules
    ]
    return replace(section, modules=modules)