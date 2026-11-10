"""Test student access pada course hasil eksekusi (BE-16.3) dengan Moodle tiruan.

Moodle tiruan (``tests.moodle_fakes.StudentMoodle``) membedakan token integrasi
dan token milik mahasiswa (``login/token.php``): dengan token mahasiswa,
``core_course_get_contents`` hanya berhasil bila mahasiswa terdaftar sebagai
student dan course terlihat, seperti perilaku Moodle. Test live ada di
``test_moodle_student_access_live.py``.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from src.services.moodle_client import MoodleClient
from src.services.moodle_integration_service import MoodleIntegrationService
from src.services.moodle_student_access import (
    MoodleStudentAccessService,
    StudentAccessSetupError,
    StudentAccountNotFoundError,
    StudentLoginError,
)
from tests.moodle_fakes import BASE_URL, STUDENT_ROLE_ID, TOKEN, StudentMoodle
from tests.moodle_fakes import OTHER_STUDENT_ACCOUNT as OTHER
from tests.moodle_fakes import STUDENT_ACCOUNT as STUDENT
from tests.moodle_fakes import STUDENT_COURSE_ID as COURSE_ID


def run(coro):
    return asyncio.run(coro)


def with_access(fake: StudentMoodle, scenario):
    async def go():
        transport = httpx.MockTransport(fake.handler)
        async with MoodleClient(BASE_URL, TOKEN, transport=transport) as client:
            access = MoodleStudentAccessService(
                MoodleIntegrationService(client), base_url=BASE_URL, transport=transport
            )
            return await scenario(access)

    return run(go())


WEEKLY = ((1, "Minggu 1"), (2, "Minggu 2"), (3, "Minggu 3"))


def test_students_are_enrolled_as_student_and_reenrolling_is_safe():
    fake = StudentMoodle()

    async def scenario(access):
        await access.enrol_students(COURSE_ID, [STUDENT[0]])
        users = await access.enrol_students(COURSE_ID, [STUDENT[0]])
        return (
            users,
            await access.is_enrolled(COURSE_ID, STUDENT[0]),
            await access.is_enrolled(COURSE_ID, OTHER[0]),
        )

    users, student_enrolled, other_enrolled = with_access(fake, scenario)

    assert [user.username for user in users] == [STUDENT[0]]
    assert fake.enrolments[COURSE_ID] == {20: {STUDENT_ROLE_ID}}
    assert (student_enrolled, other_enrolled) == (True, False)


def test_missing_student_account_is_reported_before_enrolling():
    fake = StudentMoodle()

    with pytest.raises(StudentAccountNotFoundError, match="setup_moodle_test_accounts"):
        with_access(
            fake, lambda access: access.enrol_students(COURSE_ID, ["belum.ada"])
        )

    assert fake.called("enrol_manual_enrol_users") == []


def test_visibility_reports_a_hidden_course_and_hidden_weekly_sections():
    fake = StudentMoodle()
    fake.courses[COURSE_ID]["visible"] = 0
    fake.sections[COURSE_ID][2]["visible"] = 0

    visibility = with_access(fake, lambda access: access.check_visibility(COURSE_ID))

    assert visibility.course_visible is False
    assert visibility.weekly_sections == WEEKLY
    assert visibility.hidden_sections == (2,)
    assert visibility.visible is False


def test_ensure_visible_shows_the_course_and_the_hidden_sections():
    fake = StudentMoodle()
    fake.courses[COURSE_ID]["visible"] = 0
    fake.sections[COURSE_ID][2]["visible"] = 0
    fake.sections[COURSE_ID][3]["visible"] = 0

    visibility = with_access(fake, lambda access: access.ensure_visible(COURSE_ID))

    assert visibility.visible is True
    assert fake.courses[COURSE_ID]["visible"] == 1
    shown = fake.called("core_courseformat_update_course")
    assert [
        (params["action"], params["ids[0]"], params["ids[1]"]) for params in shown
    ] == [("section_show", "203", "204")]


def test_ensure_visible_changes_nothing_when_everything_is_visible():
    fake = StudentMoodle()

    visibility = with_access(fake, lambda access: access.ensure_visible(COURSE_ID))

    assert visibility.visible is True
    assert fake.called("core_course_update_courses") == []
    assert fake.called("core_courseformat_update_course") == []


def test_enrolled_student_sees_every_weekly_section_and_others_are_rejected():
    fake = StudentMoodle()
    fake.enrol(20)

    report = with_access(
        fake,
        lambda access: access.verify(COURSE_ID, enrolled=STUDENT, not_enrolled=OTHER),
    )

    assert report.enrolled.can_open is True
    assert report.enrolled.weekly_sections == WEEKLY
    assert report.enrolled_sees_all_sections is True
    assert report.not_enrolled.can_open is False
    assert report.not_enrolled.error_code == "requireloginerror"
    assert report.ok is True
    assert [body["service"] for body in fake.login_requests] == [
        "moodle_mobile_app",
        "moodle_mobile_app",
    ]


def test_hidden_section_is_not_seen_by_the_student_and_fails_the_report():
    fake = StudentMoodle()
    fake.enrol(20)
    fake.sections[COURSE_ID][3]["visible"] = 0

    report = with_access(
        fake,
        lambda access: access.verify(COURSE_ID, enrolled=STUDENT, not_enrolled=OTHER),
    )

    assert report.enrolled.weekly_sections == WEEKLY[:2]
    assert report.visibility.hidden_sections == (3,)
    assert report.ok is False


def test_unenrolled_student_used_as_enrolled_is_rejected_and_fails_the_report():
    fake = StudentMoodle()

    report = with_access(
        fake,
        lambda access: access.verify(COURSE_ID, enrolled=STUDENT, not_enrolled=OTHER),
    )

    assert report.enrolled.can_open is False
    assert report.ok is False


def test_verification_stops_when_the_not_enrolled_account_is_enrolled():
    fake = StudentMoodle()
    fake.enrol(20)
    fake.enrol(21)

    with pytest.raises(StudentAccessSetupError, match="mhs.uji2"):
        with_access(
            fake,
            lambda access: access.verify(
                COURSE_ID, enrolled=STUDENT, not_enrolled=OTHER
            ),
        )

    assert fake.login_requests == []


def test_wrong_password_is_a_login_error_without_the_password():
    fake = StudentMoodle()

    with pytest.raises(StudentLoginError) as caught:
        with_access(
            fake,
            lambda access: access.open_course_as(STUDENT[0], "salah-total", COURSE_ID),
        )

    assert caught.value.code == "invalidlogin"
    assert "salah-total" not in str(caught.value)


def test_report_can_be_serialized():
    fake = StudentMoodle()
    fake.enrol(20)

    report = with_access(
        fake,
        lambda access: access.verify(COURSE_ID, enrolled=STUDENT, not_enrolled=OTHER),
    )

    data = report.to_dict()
    assert data["ok"] is True
    assert data["visibility"] == {
        "moodle_course_id": COURSE_ID,
        "course_visible": True,
        "weekly_sections": 3,
        "hidden_sections": [],
        "visible": True,
    }
    assert data["enrolled"]["weekly_sections"][0] == {"section": 1, "name": "Minggu 1"}
    assert data["not_enrolled"]["error_code"] == "requireloginerror"
    assert STUDENT[1] not in str(data) and OTHER[1] not in str(data)