"""Akses mahasiswa ke course hasil eksekusi (BE-16.3).

Membuktikan alur *Mengakses Course* pada proposal (§3.3.9, §3.4.9) terhadap
course target hasil eksekusi struktur (BE-16.2):

1. mahasiswa uji didaftarkan ke course target sebagai ``student`` melalui
   operasi enrolment BE-04.5;
2. course dan section mingguan diperiksa (dan bila diminta, ditampilkan) agar
   terlihat oleh mahasiswa;
3. mahasiswa terdaftar login ke Moodle dengan akunnya sendiri dan membaca
   struktur course; hasilnya dibandingkan dengan section mingguan course;
4. mahasiswa yang tidak terdaftar login dengan akunnya sendiri dan harus
   ditolak oleh Moodle.

Sejak BE-21.3 pemeriksaan juga mencakup setiap activity hasil eksekusi FULL:
visibilitas activity, mahasiswa terdaftar membuka page dan url, membuka
assignment, dan membuka quiz (opsional benar-benar memulai attempt lalu
langsung menyelesaikannya), sedangkan mahasiswa tidak terdaftar harus ditolak
pada setiap activity.

Langkah 3 dan 4 memakai token milik mahasiswa (``login/token.php`` dengan
service ``moodle_mobile_app``), bukan token integrasi, sehingga yang diuji adalah
hak akses Moodle untuk akun mahasiswa itu sendiri. Password dan token mahasiswa
tidak pernah dicatat di log, laporan, maupun pesan error.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import httpx

from src.services.moodle_client import DEFAULT_TIMEOUT_SECONDS, MoodleClient
from src.services.moodle_exceptions import (
    MoodleConnectionError,
    MoodleError,
    MoodlePermissionError,
    MoodleTimeoutError,
)
from src.services.moodle_integration_service import MoodleIntegrationService, MoodleUser

__all__ = [
    "ACTIVITY_VIEW_FUNCTIONS",
    "ActivityAccess",
    "ActivityVisibility",
    "CourseVisibility",
    "MoodleStudentAccessService",
    "StudentAccessReport",
    "StudentAccessSetupError",
    "StudentAccountNotFoundError",
    "StudentCourseView",
    "StudentLoginError",
]

#: Service bawaan Moodle yang memberi token kepada akun pengguna biasa.
STUDENT_TOKEN_SERVICE = "moodle_mobile_app"
STUDENT_ROLE = "student"

WeeklySections = tuple[tuple[int, str], ...]

#: Jenis activity hasil eksekusi FULL → web service "membuka" sebagai mahasiswa
#: beserta nama parameter instance-nya (semua tersedia pada ``moodle_mobile_app``).
ACTIVITY_VIEW_FUNCTIONS: dict[str, tuple[str, str]] = {
    "page": ("mod_page_view_page", "pageid"),
    "url": ("mod_url_view_url", "urlid"),
    "assign": ("mod_assign_view_assign", "assignid"),
    "quiz": ("mod_quiz_view_quiz", "quizid"),
}

ACTIVITY_LABELS: dict[str, str] = {
    "page": "Learning material (page)",
    "url": "Learning resource (url)",
    "assign": "Assignment",
    "quiz": "Quiz",
}


class StudentAccessSetupError(ValueError):
    """Prasyarat verifikasi akses mahasiswa tidak terpenuhi."""


class StudentAccountNotFoundError(StudentAccessSetupError):
    """Akun mahasiswa uji belum ada di Moodle."""

    def __init__(self, username: str) -> None:
        super().__init__(
            f"Akun Moodle '{username}' tidak ditemukan. Jalankan scripts.setup_moodle_test_accounts lebih dulu."
        )
        self.username = username


class StudentLoginError(StudentAccessSetupError):
    """Akun mahasiswa tidak bisa mendapat token dari Moodle."""

    def __init__(self, username: str, code: str, message: str) -> None:
        super().__init__(f"Login Moodle sebagai '{username}' gagal ({code}): {message}")
        self.username = username
        self.code = code


@dataclass(frozen=True)
class ActivityVisibility:
    """Satu activity di section mingguan menurut pengaturan course."""

    moodle_module_id: int
    modname: str
    name: str
    section_number: int
    visible: bool
    instance_id: int | None = None

    @property
    def checked(self) -> bool:
        """Jenis activity hasil eksekusi yang dibuka sebagai mahasiswa."""
        return self.modname in ACTIVITY_VIEW_FUNCTIONS and self.instance_id is not None


@dataclass(frozen=True)
class CourseVisibility:
    """Visibilitas course, section mingguan, dan activity menurut pengaturan course."""

    moodle_course_id: int
    course_visible: bool
    weekly_sections: WeeklySections
    hidden_sections: tuple[int, ...] = ()
    activities: tuple[ActivityVisibility, ...] = ()

    @property
    def hidden_activities(self) -> tuple[int, ...]:
        return tuple(
            item.moodle_module_id for item in self.activities if not item.visible
        )

    @property
    def visible(self) -> bool:
        return (
            self.course_visible
            and not self.hidden_sections
            and not self.hidden_activities
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "moodle_course_id": self.moodle_course_id,
            "course_visible": self.course_visible,
            "weekly_sections": len(self.weekly_sections),
            "hidden_sections": list(self.hidden_sections),
            "activities": len(self.activities),
            "hidden_activities": list(self.hidden_activities),
            "visible": self.visible,
        }


@dataclass(frozen=True)
class ActivityAccess:
    """Hasil satu akun mahasiswa membuka satu activity."""

    moodle_module_id: int
    modname: str
    name: str
    section_number: int
    opened: bool
    error_code: str | None = None
    #: Quiz: Moodle mengizinkan mahasiswa memulai attempt (``canattempt``).
    can_attempt: bool | None = None
    #: Quiz: attempt diminta untuk benar-benar dimulai (opsi ``start_quiz``).
    attempt_requested: bool = False
    #: Quiz: attempt berhasil dimulai lalu langsung diselesaikan.
    attempt_started: bool = False

    @property
    def ok_for_enrolled(self) -> bool:
        if not self.opened:
            return False
        return self.attempt_started if self.attempt_requested else True

    def to_dict(self) -> dict[str, Any]:
        return {
            "moodle_module_id": self.moodle_module_id,
            "modname": self.modname,
            "name": self.name,
            "section": self.section_number,
            "opened": self.opened,
            "error_code": self.error_code,
            "can_attempt": self.can_attempt,
            "attempt_started": self.attempt_started,
        }


@dataclass(frozen=True)
class StudentCourseView:
    """Apa yang dilihat satu akun mahasiswa ketika membuka course."""

    username: str
    can_open: bool
    weekly_sections: WeeklySections = ()
    error_code: str | None = None
    activities: tuple[ActivityAccess, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "username": self.username,
            "can_open": self.can_open,
            "weekly_sections": [
                {"section": number, "name": name}
                for number, name in self.weekly_sections
            ],
            "error_code": self.error_code,
            "activities": [item.to_dict() for item in self.activities],
        }


@dataclass(frozen=True)
class StudentAccessReport:
    """Hasil verifikasi student access pada satu course."""

    moodle_course_id: int
    visibility: CourseVisibility
    enrolled: StudentCourseView
    not_enrolled: StudentCourseView
    #: ``False`` bila hanya struktur course yang diperiksa (tanpa activity).
    activities_checked: bool = True

    @property
    def enrolled_sees_all_sections(self) -> bool:
        return (
            self.enrolled.can_open
            and bool(self.visibility.weekly_sections)
            and self.enrolled.weekly_sections == self.visibility.weekly_sections
        )

    @property
    def enrolled_opens_all_activities(self) -> bool:
        """Mahasiswa terdaftar membuka setiap activity yang diperiksa (BE-21.3)."""
        if not self.activities_checked:
            return True
        expected = {
            item.moodle_module_id for item in self.visibility.activities if item.checked
        }
        opened = {
            item.moodle_module_id
            for item in self.enrolled.activities
            if item.ok_for_enrolled
        }
        return expected <= opened

    @property
    def not_enrolled_rejected(self) -> bool:
        return not self.not_enrolled.can_open and not any(
            item.opened for item in self.not_enrolled.activities
        )

    @property
    def ok(self) -> bool:
        return (
            self.visibility.visible
            and self.enrolled_sees_all_sections
            and self.enrolled_opens_all_activities
            and self.not_enrolled_rejected
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "moodle_course_id": self.moodle_course_id,
            "ok": self.ok,
            "visibility": self.visibility.to_dict(),
            "enrolled": self.enrolled.to_dict(),
            "enrolled_sees_all_sections": self.enrolled_sees_all_sections,
            "enrolled_opens_all_activities": self.enrolled_opens_all_activities,
            "not_enrolled": self.not_enrolled.to_dict(),
            "not_enrolled_rejected": self.not_enrolled_rejected,
        }


class MoodleStudentAccessService:
    """Enrolment, pemeriksaan visibilitas, dan uji akses mahasiswa pada course target."""

    def __init__(
        self,
        moodle: MoodleIntegrationService,
        *,
        base_url: str,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._moodle = moodle
        self._base_url = base_url.strip().rstrip("/")
        self._timeout = timeout
        self._transport = transport

    @classmethod
    def from_settings(
        cls, moodle: MoodleIntegrationService, settings: Any, **kwargs: Any
    ) -> MoodleStudentAccessService:
        kwargs.setdefault(
            "timeout",
            getattr(settings, "moodle_timeout_seconds", None)
            or DEFAULT_TIMEOUT_SECONDS,
        )
        return cls(moodle, base_url=settings.MOODLE_BASE_URL, **kwargs)

    # --- Enrolment -----------------------------------------------------------

    async def enrol_students(
        self, moodle_course_id: int, usernames: Sequence[str]
    ) -> tuple[MoodleUser, ...]:
        """Daftarkan akun mahasiswa uji ke course target sebagai ``student`` (BE-04.5).

        Aman diulang; enrolment yang sudah ada tidak digandakan.
        """
        if not usernames:
            raise ValueError("daftar mahasiswa kosong")
        users = []
        for username in usernames:
            user = await self._moodle.get_user_by_username(username)
            if user is None:
                raise StudentAccountNotFoundError(username)
            users.append(user)
        await self._moodle.enrol_users(
            moodle_course_id, [(user.moodle_user_id, STUDENT_ROLE) for user in users]
        )
        return tuple(users)

    async def is_enrolled(self, moodle_course_id: int, username: str) -> bool:
        enrolled = await self._moodle.get_enrolled_users(moodle_course_id)
        return any(item.user.username == username.strip().lower() for item in enrolled)

    # --- Visibilitas ---------------------------------------------------------

    async def check_visibility(self, moodle_course_id: int) -> CourseVisibility:
        """Course dan section mingguan yang tersembunyi dari mahasiswa."""
        course = await self._moodle.get_course(moodle_course_id)
        contents = await self._moodle.get_course_contents(moodle_course_id)
        weekly = [
            section for section in contents.sections if section.section_number > 0
        ]
        return CourseVisibility(
            moodle_course_id=moodle_course_id,
            course_visible=course.visible,
            weekly_sections=tuple(
                (section.section_number, section.name) for section in weekly
            ),
            hidden_sections=tuple(
                section.section_number for section in weekly if not section.visible
            ),
            activities=tuple(
                ActivityVisibility(
                    moodle_module_id=module.moodle_module_id,
                    modname=module.modname,
                    name=module.name,
                    section_number=section.section_number,
                    visible=module.visible,
                    instance_id=module.instance_id,
                )
                for section in weekly
                for module in section.modules
            ),
        )

    async def ensure_visible(self, moodle_course_id: int) -> CourseVisibility:
        """Tampilkan course dan section mingguan yang tersembunyi, lalu periksa ulang."""
        visibility = await self.check_visibility(moodle_course_id)
        if not visibility.course_visible:
            await self._moodle.update_course(moodle_course_id, visible=True)
        if visibility.hidden_sections:
            contents = await self._moodle.get_course_contents(moodle_course_id)
            hidden = set(visibility.hidden_sections)
            await self._moodle.set_section_visibility(
                moodle_course_id,
                [
                    section.moodle_section_id
                    for section in contents.sections
                    if section.section_number in hidden
                ],
                True,
            )
        if visibility.hidden_activities:
            await self._moodle.set_module_visibility(
                moodle_course_id, list(visibility.hidden_activities), True
            )
        if visibility.visible:
            return visibility
        return await self.check_visibility(moodle_course_id)

    # --- Akses sebagai mahasiswa ---------------------------------------------

    async def open_course_as(
        self,
        username: str,
        password: str,
        moodle_course_id: int,
        *,
        activities: Sequence[ActivityVisibility] = (),
        start_quiz: bool = False,
    ) -> StudentCourseView:
        """Login sebagai mahasiswa, baca struktur course, lalu buka setiap activity.

        Activity dibuka lewat web service ``mod_*_view_*`` dengan token milik
        mahasiswa. Untuk quiz, izin memulai attempt dibaca dari
        ``mod_quiz_get_quiz_access_information``; dengan ``start_quiz`` attempt
        benar-benar dimulai lalu langsung diselesaikan tanpa jawaban. Opsi ini
        meninggalkan satu attempt pada quiz, jadi gunakan pada course uji.
        """
        token = await self._student_token(username, password)
        async with MoodleClient(
            self._base_url, token, timeout=self._timeout, transport=self._transport
        ) as client:
            try:
                sections = await client.call(
                    "core_course_get_contents", {"courseid": moodle_course_id}
                )
            except MoodlePermissionError as exc:
                can_open, error_code, sections = False, exc.code, None
            else:
                can_open, error_code = True, None
            opened = tuple(
                [
                    await self._open_activity(client, item, start_quiz=start_quiz)
                    for item in activities
                    if item.checked
                ]
            )
        weekly = tuple(
            (int(raw["section"]), str(raw.get("name") or ""))
            for raw in sections or []
            if int(raw.get("section", 0)) > 0 and raw.get("uservisible", True)
        )
        return StudentCourseView(
            username=username,
            can_open=can_open,
            weekly_sections=weekly,
            error_code=error_code,
            activities=opened,
        )

    async def _open_activity(
        self, client: MoodleClient, activity: ActivityVisibility, *, start_quiz: bool
    ) -> ActivityAccess:
        function, parameter = ACTIVITY_VIEW_FUNCTIONS[activity.modname]
        base = {
            "moodle_module_id": activity.moodle_module_id,
            "modname": activity.modname,
            "name": activity.name,
            "section_number": activity.section_number,
            "attempt_requested": start_quiz and activity.modname == "quiz",
        }
        try:
            await client.call(function, {parameter: activity.instance_id})
        except MoodleError as exc:
            return ActivityAccess(opened=False, error_code=exc.code, **base)
        if activity.modname != "quiz":
            return ActivityAccess(opened=True, **base)

        can_attempt: bool | None = None
        try:
            info = await client.call(
                "mod_quiz_get_quiz_access_information", {"quizid": activity.instance_id}
            )
            can_attempt = bool((info or {}).get("canattempt"))
            if not start_quiz:
                return ActivityAccess(opened=True, can_attempt=can_attempt, **base)
            started = await client.call(
                "mod_quiz_start_attempt", {"quizid": activity.instance_id}
            )
            attempt_id = int(started["attempt"]["id"])
            await client.call(
                "mod_quiz_process_attempt",
                {"attemptid": attempt_id, "finishattempt": True},
            )
        except MoodleError as exc:
            return ActivityAccess(
                opened=True, can_attempt=can_attempt, error_code=exc.code, **base
            )
        return ActivityAccess(
            opened=True, can_attempt=can_attempt, attempt_started=True, **base
        )

    async def verify(
        self,
        moodle_course_id: int,
        *,
        enrolled: tuple[str, str],
        not_enrolled: tuple[str, str],
        check_activities: bool = True,
        start_quiz: bool = False,
    ) -> StudentAccessReport:
        """Bandingkan akses mahasiswa terdaftar dan tidak terdaftar pada course target.

        ``enrolled`` dan ``not_enrolled`` berisi ``(username, password)``. Akun
        ``not_enrolled`` harus benar-benar tidak terdaftar di course; bila
        terdaftar, verifikasi dihentikan karena hasilnya tidak bermakna.

        Dengan ``check_activities`` (bawaan), setiap activity page/url/assign/quiz
        di section mingguan dibuka oleh kedua akun. ``start_quiz`` hanya berlaku
        untuk mahasiswa terdaftar.
        """
        if await self.is_enrolled(moodle_course_id, not_enrolled[0]):
            raise StudentAccessSetupError(
                f"Akun '{not_enrolled[0]}' terdaftar di course {moodle_course_id}; "
                "pakai akun mahasiswa lain yang tidak terdaftar."
            )
        visibility = await self.check_visibility(moodle_course_id)
        activities = visibility.activities if check_activities else ()
        return StudentAccessReport(
            moodle_course_id=moodle_course_id,
            visibility=visibility,
            enrolled=await self.open_course_as(
                *enrolled,
                moodle_course_id,
                activities=activities,
                start_quiz=start_quiz,
            ),
            not_enrolled=await self.open_course_as(
                *not_enrolled, moodle_course_id, activities=activities
            ),
            activities_checked=check_activities,
        )

    async def _student_token(self, username: str, password: str) -> str:
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport
            ) as http:
                response = await http.post(
                    f"{self._base_url}/login/token.php",
                    data={
                        "username": username,
                        "password": password,
                        "service": STUDENT_TOKEN_SERVICE,
                    },
                )
        except httpx.TimeoutException as exc:
            raise MoodleTimeoutError(
                "Moodle tidak menjawab saat login mahasiswa"
            ) from exc
        except httpx.HTTPError as exc:
            raise MoodleConnectionError(
                "Moodle tidak dapat dihubungi saat login mahasiswa"
            ) from exc
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if not isinstance(payload, dict):
            payload = {}
        token = payload.get("token")
        if not token:
            raise StudentLoginError(
                username,
                str(payload.get("errorcode") or "invalid_response"),
                str(payload.get("error") or "Moodle tidak memberikan token"),
            )
        return str(token)