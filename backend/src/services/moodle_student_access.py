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
    MoodlePermissionError,
    MoodleTimeoutError,
)
from src.services.moodle_integration_service import MoodleIntegrationService, MoodleUser

__all__ = [
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
class CourseVisibility:
    """Visibilitas course dan section mingguan menurut pengaturan course."""

    moodle_course_id: int
    course_visible: bool
    weekly_sections: WeeklySections
    hidden_sections: tuple[int, ...] = ()

    @property
    def visible(self) -> bool:
        return self.course_visible and not self.hidden_sections

    def to_dict(self) -> dict[str, Any]:
        return {
            "moodle_course_id": self.moodle_course_id,
            "course_visible": self.course_visible,
            "weekly_sections": len(self.weekly_sections),
            "hidden_sections": list(self.hidden_sections),
            "visible": self.visible,
        }


@dataclass(frozen=True)
class StudentCourseView:
    """Apa yang dilihat satu akun mahasiswa ketika membuka course."""

    username: str
    can_open: bool
    weekly_sections: WeeklySections = ()
    error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "username": self.username,
            "can_open": self.can_open,
            "weekly_sections": [
                {"section": number, "name": name}
                for number, name in self.weekly_sections
            ],
            "error_code": self.error_code,
        }


@dataclass(frozen=True)
class StudentAccessReport:
    """Hasil verifikasi student access pada satu course."""

    moodle_course_id: int
    visibility: CourseVisibility
    enrolled: StudentCourseView
    not_enrolled: StudentCourseView

    @property
    def enrolled_sees_all_sections(self) -> bool:
        return (
            self.enrolled.can_open
            and bool(self.visibility.weekly_sections)
            and self.enrolled.weekly_sections == self.visibility.weekly_sections
        )

    @property
    def not_enrolled_rejected(self) -> bool:
        return not self.not_enrolled.can_open

    @property
    def ok(self) -> bool:
        return (
            self.visibility.visible
            and self.enrolled_sees_all_sections
            and self.not_enrolled_rejected
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "moodle_course_id": self.moodle_course_id,
            "ok": self.ok,
            "visibility": self.visibility.to_dict(),
            "enrolled": self.enrolled.to_dict(),
            "enrolled_sees_all_sections": self.enrolled_sees_all_sections,
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
        if visibility.visible:
            return visibility
        return await self.check_visibility(moodle_course_id)

    # --- Akses sebagai mahasiswa ---------------------------------------------

    async def open_course_as(
        self, username: str, password: str, moodle_course_id: int
    ) -> StudentCourseView:
        """Login sebagai mahasiswa lalu baca struktur course dengan token miliknya."""
        token = await self._student_token(username, password)
        async with MoodleClient(
            self._base_url, token, timeout=self._timeout, transport=self._transport
        ) as client:
            try:
                sections = await client.call(
                    "core_course_get_contents", {"courseid": moodle_course_id}
                )
            except MoodlePermissionError as exc:
                return StudentCourseView(
                    username=username, can_open=False, error_code=exc.code
                )
        weekly = tuple(
            (int(raw["section"]), str(raw.get("name") or ""))
            for raw in sections or []
            if int(raw.get("section", 0)) > 0 and raw.get("uservisible", True)
        )
        return StudentCourseView(
            username=username, can_open=True, weekly_sections=weekly
        )

    async def verify(
        self,
        moodle_course_id: int,
        *,
        enrolled: tuple[str, str],
        not_enrolled: tuple[str, str],
    ) -> StudentAccessReport:
        """Bandingkan akses mahasiswa terdaftar dan tidak terdaftar pada course target.

        ``enrolled`` dan ``not_enrolled`` berisi ``(username, password)``. Akun
        ``not_enrolled`` harus benar-benar tidak terdaftar di course; bila
        terdaftar, verifikasi dihentikan karena hasilnya tidak bermakna.
        """
        if await self.is_enrolled(moodle_course_id, not_enrolled[0]):
            raise StudentAccessSetupError(
                f"Akun '{not_enrolled[0]}' terdaftar di course {moodle_course_id}; "
                "pakai akun mahasiswa lain yang tidak terdaftar."
            )
        visibility = await self.check_visibility(moodle_course_id)
        return StudentAccessReport(
            moodle_course_id=moodle_course_id,
            visibility=visibility,
            enrolled=await self.open_course_as(*enrolled, moodle_course_id),
            not_enrolled=await self.open_course_as(*not_enrolled, moodle_course_id),
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