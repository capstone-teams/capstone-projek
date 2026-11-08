from __future__ import annotations

from urllib.parse import parse_qs

import httpx

TOKEN = "fake-moodle-token-8f3a1c"
BASE_URL = "http://moodle.test/moodle"

ALL_FUNCTIONS = [
    "core_webservice_get_site_info",
    "core_course_get_courses",
    "core_course_get_courses_by_field",
    "core_course_get_contents",
    "core_course_create_courses",
    "core_course_update_courses",
    "core_course_edit_section",
    "core_courseformat_update_course",
    "core_update_inplace_editable",
    "mod_page_get_pages_by_courses",
]


def moodle_exception(errorcode: str, message: str, exception: str = "moodle_exception") -> dict:
    return {"exception": exception, "errorcode": errorcode, "message": message}


class FakeMoodle:
    def __init__(self, token: str = TOKEN) -> None:
        self.token = token
        self.calls: list[tuple[str, dict[str, str]]] = []
        self.functions = list(ALL_FUNCTIONS)
        self.failing: dict[str, dict] = {}
        self.raise_on_request: Exception | None = None
        self.courses: dict[int, dict] = {
            1: {"id": 1, "fullname": "Moodle ITK", "shortname": "ITK", "format": "site"},
            2: {
                "id": 2,
                "fullname": "Pemrograman Web",
                "shortname": "PW101",
                "format": "topics",
                "visible": 1,
                "categoryid": 1,
                "summary": "<p>Course uji</p>",
            },
        }
        self.sections: dict[int, list[dict]] = {
            2: [
                {"id": 201, "section": 0, "name": "General", "summary": "", "visible": 1, "modules": []},
                {
                    "id": 202,
                    "section": 1,
                    "name": "Minggu 1",
                    "summary": "",
                    "visible": 1,
                    "modules": [
                        {"id": 501, "name": "Pengantar HTML", "modname": "page", "visible": 1, "description": ""},
                        {"id": 502, "name": "Tugas 1", "modname": "assign", "visible": 1, "description": "<p>Kerjakan</p>"},
                    ],
                },
            ]
        }
        self.pages: dict[int, str] = {501: "<h2>Isi halaman yang digenerate</h2>"}
        self._next_course_id = 3
        self._next_section_id = 300

    def called(self, wsfunction: str) -> list[dict[str, str]]:
        return [params for name, params in self.calls if name == wsfunction]

    def handler(self, request: httpx.Request) -> httpx.Response:
        if self.raise_on_request is not None:
            raise self.raise_on_request
        params = {key: values[0] for key, values in parse_qs(request.content.decode()).items()}
        wsfunction = params.get("wsfunction", "")
        self.calls.append((wsfunction, params))

        if params.get("wstoken") != self.token:
            return httpx.Response(200, json=moodle_exception("invalidtoken", "Invalid token - token not found"))
        if wsfunction in self.failing:
            return httpx.Response(200, json=self.failing[wsfunction])
        return httpx.Response(200, json=self._dispatch(wsfunction, params))

    def _dispatch(self, wsfunction: str, params: dict[str, str]):
        if wsfunction == "core_webservice_get_site_info":
            return {
                "sitename": "Moodle ITK",
                "release": "4.5.1+ (Build: 20250101)",
                "version": "2024100701",
                "functions": [{"name": name, "version": "1"} for name in self.functions],
            }
        if wsfunction == "core_course_get_courses":
            if "options[ids][0]" in params:
                wanted = {int(value) for key, value in params.items() if key.startswith("options[ids]")}
                return [course for cid, course in self.courses.items() if cid in wanted]
            return list(self.courses.values())
        if wsfunction == "core_course_get_courses_by_field":
            field, value = params.get("field"), params.get("value")
            return {
                "courses": [course for course in self.courses.values() if str(course.get(field)) == value],
                "warnings": [],
            }
        if wsfunction == "core_course_update_courses":
            course_id = int(params["courses[0][id]"])
            shortname = params.get("courses[0][shortname]")
            if shortname and any(
                cid != course_id and course.get("shortname") == shortname for cid, course in self.courses.items()
            ):
                return {
                    "warnings": [
                        {"item": "course", "itemid": course_id, "warningcode": "shortnametaken",
                         "message": "Short name is already used"}
                    ]
                }
            course = self.courses[course_id]
            for field in ("fullname", "shortname", "summary"):
                if f"courses[0][{field}]" in params:
                    course[field] = params[f"courses[0][{field}]"]
            if "courses[0][visible]" in params:
                course["visible"] = int(params["courses[0][visible]"])
            return {"warnings": []}
        if wsfunction == "core_course_get_contents":
            course_id = int(params["courseid"])
            if course_id not in self.sections:
                return moodle_exception("invalidcourseid", "Invalid course id")
            return self.sections[course_id]
        if wsfunction == "core_course_create_courses":
            shortname = params["courses[0][shortname]"]
            if any(course.get("shortname") == shortname for course in self.courses.values()):
                return moodle_exception("shortnametaken", "Short name is already used")
            course_id = self._next_course_id
            self._next_course_id += 1
            self.courses[course_id] = {
                "id": course_id,
                "fullname": params["courses[0][fullname]"],
                "shortname": shortname,
                "format": "topics",
                "visible": 1,
                "categoryid": int(params["courses[0][categoryid]"]),
                "summary": "",
            }
            self.sections[course_id] = [
                {"id": self._take_section_id(), "section": 0, "name": "", "summary": "", "visible": 1, "modules": []}
            ]
            return [{"id": course_id, "shortname": shortname}]
        if wsfunction == "core_courseformat_update_course":
            course_sections = self.sections[int(params["courseid"])]
            course_sections.append(
                {
                    "id": self._take_section_id(),
                    "section": len(course_sections),
                    "name": "",
                    "summary": "",
                    "visible": 1,
                    "modules": [],
                }
            )
            return "[]"
        if wsfunction == "core_update_inplace_editable":
            section_id = int(params["itemid"])
            for course_sections in self.sections.values():
                for section in course_sections:
                    if section["id"] == section_id:
                        section["name"] = params["value"]
            return {"itemid": section_id, "displayvalue": params["value"]}
        if wsfunction == "mod_page_get_pages_by_courses":
            return {
                "pages": [{"coursemodule": cmid, "content": content} for cmid, content in self.pages.items()],
                "warnings": [],
            }
        return moodle_exception("invalidfunction", f"Unknown function {wsfunction}")

    def _take_section_id(self) -> int:
        self._next_section_id += 1
        return self._next_section_id