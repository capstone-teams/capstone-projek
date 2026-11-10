
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
    "local_capstonebridge_update_section",
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
        self.users: dict[int, dict] = {
            2: {"id": 2, "username": "admin", "firstname": "Admin", "lastname": "User", "email": "admin@example.com"}
        }
        self.enrolments: dict[int, dict[int, set[int]]] = {}
        self._next_user_id = 10
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

        result = self._dispatch(wsfunction, params)
        if result is None:  # Moodle membalas function tanpa nilai kembali dengan teks "null"
            return httpx.Response(200, content=b"null", headers={"content-type": "application/json"})
        return httpx.Response(200, json=result)

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
        if wsfunction == "core_user_get_users_by_field":
            wanted = {value for key, value in params.items() if key.startswith("values[")}
            return [user for user in self.users.values() if str(user.get(params["field"])) in wanted]
        if wsfunction == "core_user_create_users":
            username = params["users[0][username]"]
            if any(user["username"] == username for user in self.users.values()):
                return moodle_exception("usernameexists", "Username already exists", "invalid_parameter_exception")
            user_id = self._next_user_id
            self._next_user_id += 1
            self.users[user_id] = {
                "id": user_id,
                "username": username,
                "firstname": params["users[0][firstname]"],
                "lastname": params["users[0][lastname]"],
                "email": params["users[0][email]"],
            }
            return [{"id": user_id, "username": username}]
        if wsfunction == "enrol_manual_enrol_users":
            index = 0
            while f"enrolments[{index}][userid]" in params:
                course_id = int(params[f"enrolments[{index}][courseid]"])
                user_id = int(params[f"enrolments[{index}][userid]"])
                role_id = int(params[f"enrolments[{index}][roleid]"])
                self.enrolments.setdefault(course_id, {}).setdefault(user_id, set()).add(role_id)
                index += 1
            return None
        if wsfunction == "core_enrol_get_enrolled_users":
            course_id = int(params["courseid"])
            shortnames = {3: "editingteacher", 5: "student"}
            return [
                {
                    **self.users[user_id],
                    "fullname": f"{self.users[user_id]['firstname']} {self.users[user_id]['lastname']}",
                    "roles": [
                        {"roleid": role, "shortname": shortnames[role]}
                        for role in sorted(roles)
                    ],
                }
                for user_id, roles in self.enrolments.get(course_id, {}).items()
            ]
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
        if wsfunction == "core_courseformat_update_course" and params.get("action") in ("section_show", "section_hide"):
            ids = {int(value) for key, value in params.items() if key.startswith("ids[")}
            for section in self.sections[int(params["courseid"])]:
                if section["id"] in ids:
                    section["visible"] = int(params["action"] == "section_show")
            return "[]"
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
        if wsfunction == "local_capstonebridge_update_section":
            course_id, section_id = int(params["courseid"]), int(params["sectionid"])
            section = next((s for s in self.sections.get(course_id, []) if s["id"] == section_id), None)
            if section is None:
                return moodle_exception("invalidrecord", "Can't find data record in database table course_sections.")
            section.update(name=params["name"], summary=params.get("summary", ""))
            return {"sectionid": section_id, "section": section["section"], "name": params["name"], "updated": 1}
        if wsfunction == "mod_page_get_pages_by_courses":
            return {
                "pages": [{"coursemodule": cmid, "content": content} for cmid, content in self.pages.items()],
                "warnings": [],
            }
        return moodle_exception("invalidfunction", f"Unknown function {wsfunction}")

    def _take_section_id(self) -> int:
        self._next_section_id += 1
        return self._next_section_id


# --- Akses mahasiswa (BE-16.3) -------------------------------------------------

STUDENT_COURSE_ID = 2
STUDENT_ACCOUNT = ("mhs.uji", "Mhs-pass-1#")
OTHER_STUDENT_ACCOUNT = ("mhs.uji2", "Mhs-pass-2#")
STUDENT_ROLE_ID = 5


class StudentMoodle(FakeMoodle):
    """Moodle tiruan dengan login mahasiswa dan pemeriksaan enrolment."""

    def __init__(self) -> None:
        super().__init__()
        self.passwords = {STUDENT_ACCOUNT[0]: STUDENT_ACCOUNT[1], OTHER_STUDENT_ACCOUNT[0]: OTHER_STUDENT_ACCOUNT[1]}
        self.users[20] = {"id": 20, "username": STUDENT_ACCOUNT[0], "firstname": "Mahasiswa", "lastname": "Uji",
                          "email": "mhs.uji@example.com"}
        self.users[21] = {"id": 21, "username": OTHER_STUDENT_ACCOUNT[0], "firstname": "Mahasiswa", "lastname": "Dua",
                          "email": "mhs.uji2@example.com"}
        self.sections[STUDENT_COURSE_ID] += [
            {"id": 203, "section": 2, "name": "Minggu 2", "summary": "", "visible": 1, "modules": []},
            {"id": 204, "section": 3, "name": "Minggu 3", "summary": "", "visible": 1, "modules": []},
        ]
        self.login_requests: list[dict[str, str]] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        body = {key: values[0] for key, values in parse_qs(request.content.decode()).items()}
        if request.url.path.endswith("/login/token.php"):
            self.login_requests.append(body)
            if self.passwords.get(body.get("username")) != body.get("password"):
                return httpx.Response(200, json={"error": "Invalid login, please try again", "errorcode": "invalidlogin"})
            return httpx.Response(200, json={"token": f"student-token-{body['username']}"})
        token = body.get("wstoken", "")
        if token.startswith("student-token-"):
            return httpx.Response(200, json=self._as_student(token.removeprefix("student-token-"), body))
        return super().handler(request)

    def _as_student(self, username: str, body: dict[str, str]):
        if body.get("wsfunction") != "core_course_get_contents":
            return self._as_student_call(username, body)
        course_id = int(body["courseid"])
        user_id = next(uid for uid, user in self.users.items() if user["username"] == username)
        enrolled = STUDENT_ROLE_ID in self.enrolments.get(course_id, {}).get(user_id, set())
        if not enrolled or not self.courses[course_id].get("visible", 1):
            return moodle_exception("requireloginerror", "Course or activity not accessible.", "require_login_exception")
        return [
            {**section, "uservisible": bool(section["visible"])}
            for section in self.sections[course_id]
            if section["visible"] or section["section"] == 0
        ]

    def _as_student_call(self, username: str, body: dict[str, str]):
        """Web service lain dengan token mahasiswa; diperluas ``StudentActivityMoodle``."""
        return moodle_exception("accessexception", "Access control exception", "webservice_access_exception")

    def enrol(self, user_id: int) -> None:
        self.enrolments.setdefault(STUDENT_COURSE_ID, {}).setdefault(user_id, set()).add(STUDENT_ROLE_ID)


# --- Activity hasil eksekusi FULL (BE-21.2) ------------------------------------

ACTIVITY_COURSE_ID = 3
ACTIVITY_CREATE_FUNCTIONS = {
    "local_capstonebridge_create_page": "page",
    "local_capstonebridge_create_url": "url",
    "local_capstonebridge_create_assign": "assign",
    "local_capstonebridge_create_quiz": "quiz",
}
ACTIVITY_UPDATE_FUNCTIONS = {
    "local_capstonebridge_update_page": "page",
    "local_capstonebridge_update_url": "url",
    "local_capstonebridge_update_assign": "assign",
    "local_capstonebridge_update_quiz": "quiz",
}


class ActivityMoodle(FakeMoodle):
    """Course kosong + plugin activity; module tampil pada ``core_course_get_contents``.

    Module disimpan di dalam section, sehingga perubahan manual (hapus, ganti
    nama, pindah section) terlihat saat course dibaca ulang seperti di Moodle.
    """

    def __init__(self) -> None:
        super().__init__()
        self.courses[ACTIVITY_COURSE_ID] = {
            "id": ACTIVITY_COURSE_ID, "fullname": "Basis Data", "shortname": "IF123", "format": "topics",
            "visible": 1, "categoryid": 1, "summary": "",
        }
        self.sections[ACTIVITY_COURSE_ID] = [
            {"id": 300, "section": 0, "name": "General", "summary": "", "visible": 1, "modules": []}
        ]
        self.idnumbers: dict[int, str] = {}
        self._next_cmid = 900

    # Perubahan manual dosen/admin langsung di Moodle -------------------------

    def module(self, cmid: int) -> dict | None:
        for section in self.sections[ACTIVITY_COURSE_ID]:
            for module in section["modules"]:
                if module["id"] == cmid:
                    return module
        return None

    def section_of(self, cmid: int) -> int | None:
        for section in self.sections[ACTIVITY_COURSE_ID]:
            if any(module["id"] == cmid for module in section["modules"]):
                return section["section"]
        return None

    def weekly_modules(self) -> list[dict]:
        return [m for s in self.sections[ACTIVITY_COURSE_ID] if s["section"] > 0 for m in s["modules"]]

    def delete_module(self, cmid: int) -> None:
        for section in self.sections[ACTIVITY_COURSE_ID]:
            section["modules"] = [module for module in section["modules"] if module["id"] != cmid]
        self.idnumbers.pop(cmid, None)

    def move_module(self, cmid: int, section_number: int) -> None:
        module = self.module(cmid)
        self.delete_module(cmid)
        self._section(section_number)["modules"].append(module)

    def add_manual_module(self, section_number: int, name: str, modname: str = "forum") -> int:
        cmid = self._next_cmid
        self._next_cmid += 1
        self._section(section_number)["modules"].append(
            {"id": cmid, "name": name, "modname": modname, "visible": 1}
        )
        return cmid

    def _section(self, number: int) -> dict:
        return next(item for item in self.sections[ACTIVITY_COURSE_ID] if item["section"] == number)

    # Plugin local_capstonebridge ---------------------------------------------

    def _dispatch(self, wsfunction, params):
        if wsfunction in ACTIVITY_CREATE_FUNCTIONS:
            idnumber = params.get("idnumber", "")
            existing = next((cmid for cmid, value in self.idnumbers.items() if value and value == idnumber), None)
            if existing is not None:
                return self._response(existing, created=0)
            cmid = self._next_cmid
            self._next_cmid += 1
            self._section(int(params["section"]))["modules"].append(
                {"id": cmid, "name": params["name"], "modname": ACTIVITY_CREATE_FUNCTIONS[wsfunction], "visible": 1}
            )
            self.idnumbers[cmid] = idnumber
            return self._response(cmid, created=1)
        if wsfunction in ACTIVITY_UPDATE_FUNCTIONS:
            cmid = int(params["cmid"])
            module = self.module(cmid)
            if module is None or module["modname"] != ACTIVITY_UPDATE_FUNCTIONS[wsfunction]:
                return moodle_exception("invalidcoursemodule", "Invalid course module ID")
            module["name"] = params["name"]
            if self.section_of(cmid) != int(params["section"]):
                self.move_module(cmid, int(params["section"]))
            return self._response(cmid, created=0)
        return super()._dispatch(wsfunction, params)

    def _response(self, cmid: int, *, created: int) -> dict:
        return {
            "cmid": cmid, "instanceid": cmid + 1000, "created": created, "updated": 1,
            "section": self.section_of(cmid), "questioncount": 1, "questionsreplaced": 0, "hasattempts": 0,
        }


# --- Akses mahasiswa ke activity (BE-21.3) --------------------------------------

STUDENT_VIEW_FUNCTIONS = {
    "mod_page_view_page": ("page", "pageid"),
    "mod_url_view_url": ("url", "urlid"),
    "mod_assign_view_assign": ("assign", "assignid"),
    "mod_quiz_view_quiz": ("quiz", "quizid"),
    "mod_quiz_get_quiz_access_information": ("quiz", "quizid"),
    "mod_quiz_start_attempt": ("quiz", "quizid"),
}


class StudentActivityMoodle(StudentMoodle):
    """Course 2 berisi page, url, assign, dan quiz di minggu 1 yang dapat dibuka mahasiswa.

    Activity hanya terbuka bagi mahasiswa yang terdaftar sebagai student pada
    course yang terlihat, dan activity tersembunyi ditolak, seperti di Moodle.
    """

    def __init__(self) -> None:
        super().__init__()
        week_one = self.sections[STUDENT_COURSE_ID][1]
        week_one["modules"] = [
            {"id": 501, "instance": 41, "name": "Pengantar HTML", "modname": "page", "visible": 1},
            {"id": 502, "instance": 42, "name": "Tugas 1", "modname": "assign", "visible": 1},
            {"id": 503, "instance": 43, "name": "Artikel HTML", "modname": "url", "visible": 1},
            {"id": 504, "instance": 44, "name": "Kuis 1", "modname": "quiz", "visible": 1},
        ]
        self.student_calls: list[tuple[str, str]] = []
        self.attempts: dict[int, dict] = {}
        #: Fungsi yang ditolak Moodle walaupun mahasiswa terdaftar (mis. quiz tanpa soal).
        self.student_failures: dict[str, dict] = {}

    def module(self, cmid: int) -> dict:
        return next(m for s in self.sections[STUDENT_COURSE_ID] for m in s["modules"] if m["id"] == cmid)

    def _as_student_call(self, username: str, body: dict[str, str]):
        function = body.get("wsfunction", "")
        self.student_calls.append((username, function))
        if function == "mod_quiz_process_attempt":
            attempt = self.attempts[int(body["attemptid"])]
            attempt["state"] = "finished" if body.get("finishattempt") == "1" else "inprogress"
            return {"state": attempt["state"], "warnings": []}
        if function not in STUDENT_VIEW_FUNCTIONS:
            return super()._as_student_call(username, body)
        modname, parameter = STUDENT_VIEW_FUNCTIONS[function]
        instance = int(body[parameter])
        located = next(
            (
                (section, module)
                for section in self.sections[STUDENT_COURSE_ID]
                for module in section["modules"]
                if module["modname"] == modname and module.get("instance") == instance
            ),
            None,
        )
        if located is None:
            return moodle_exception("invalidrecord", "Can't find data record in database.")
        section, module = located
        user_id = next(uid for uid, user in self.users.items() if user["username"] == username)
        enrolled = STUDENT_ROLE_ID in self.enrolments.get(STUDENT_COURSE_ID, {}).get(user_id, set())
        if not enrolled or not self.courses[STUDENT_COURSE_ID].get("visible", 1):
            return moodle_exception("requireloginerror", "Course or activity not accessible.", "require_login_exception")
        if not module["visible"] or not section["visible"]:
            return moodle_exception("requireloginerror", "Activity is hidden.", "require_login_exception")
        if function in self.student_failures:
            return self.student_failures[function]
        if function == "mod_quiz_get_quiz_access_information":
            return {"canattempt": True, "canpreview": False, "preventaccessreasons": [], "warnings": []}
        if function == "mod_quiz_start_attempt":
            attempt_id = 7000 + len(self.attempts)
            self.attempts[attempt_id] = {"user": username, "quiz": instance, "state": "inprogress"}
            return {"attempt": {"id": attempt_id, "quiz": instance, "state": "inprogress"}, "warnings": []}
        return {"status": True, "warnings": []}

    def _dispatch(self, wsfunction, params):
        if wsfunction == "core_courseformat_update_course" and params.get("action") in ("cm_show", "cm_hide"):
            ids = {int(value) for key, value in params.items() if key.startswith("ids[")}
            for section in self.sections[int(params["courseid"])]:
                for module in section["modules"]:
                    if module["id"] in ids:
                        module["visible"] = int(params["action"] == "cm_show")
            return "[]"
        return super()._dispatch(wsfunction, params)
