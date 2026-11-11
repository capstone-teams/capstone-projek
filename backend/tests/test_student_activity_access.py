"""Test akses mahasiswa ke activity hasil eksekusi FULL (BE-21.3) dengan Moodle tiruan.

Course tiruan (``tests.moodle_fakes.StudentActivityMoodle``) berisi page, url,
assignment, dan quiz pada minggu 1. Activity hanya terbuka bagi mahasiswa yang
terdaftar sebagai student, dan activity tersembunyi ditolak, seperti di Moodle.
Yang dibuktikan:

- visibilitas setiap activity diperiksa dan dapat ditampilkan kembali;
- mahasiswa terdaftar membuka page, url, dan assignment, membuka quiz beserta
  izin memulai attempt, dan (opsional) benar-benar memulai attempt quiz;
- mahasiswa tidak terdaftar ditolak pada course dan pada setiap activity;
- laporan dan script demo mencakup seluruh jenis activity.

Test live ada di ``test_moodle_student_activity_live.py``.
"""

from __future__ import annotations

import asyncio

import httpx

from scripts.verify_student_access import format_report, run
from src.services.moodle_client import MoodleClient
from src.services.moodle_integration_service import MoodleIntegrationService
from src.services.moodle_student_access import MoodleStudentAccessService
from tests.moodle_fakes import BASE_URL, TOKEN, StudentActivityMoodle, moodle_exception
from tests.moodle_fakes import OTHER_STUDENT_ACCOUNT as OTHER
from tests.moodle_fakes import STUDENT_ACCOUNT as STUDENT
from tests.moodle_fakes import STUDENT_COURSE_ID as COURSE_ID

MODULES = {501: "page", 502: "assign", 503: "url", 504: "quiz"}


def with_access(fake: StudentActivityMoodle, scenario):
    async def go():
        transport = httpx.MockTransport(fake.handler)
        async with MoodleClient(BASE_URL, TOKEN, transport=transport) as client:
            access = MoodleStudentAccessService(
                MoodleIntegrationService(client), base_url=BASE_URL, transport=transport
            )
            return await scenario(access)

    return asyncio.run(go())


def verify(fake: StudentActivityMoodle, **kwargs):
    return with_access(
        fake,
        lambda access: access.verify(
            COURSE_ID, enrolled=STUDENT, not_enrolled=OTHER, **kwargs
        ),
    )


def enrolled_fake() -> StudentActivityMoodle:
    fake = StudentActivityMoodle()
    fake.enrol(20)
    return fake


def test_activity_visibility_lists_every_weekly_activity():
    fake = StudentActivityMoodle()
    fake.module(503)["visible"] = 0

    visibility = with_access(fake, lambda access: access.check_visibility(COURSE_ID))

    assert {
        item.moodle_module_id: item.modname for item in visibility.activities
    } == MODULES
    assert {
        item.moodle_module_id: item.instance_id for item in visibility.activities
    } == {
        501: 41,
        502: 42,
        503: 43,
        504: 44,
    }
    assert visibility.hidden_activities == (503,)
    assert visibility.visible is False


def test_enrolled_student_opens_every_activity_and_others_are_rejected():
    fake = enrolled_fake()

    report = verify(fake)

    opened = {item.moodle_module_id: item for item in report.enrolled.activities}
    assert {cmid: item.opened for cmid, item in opened.items()} == dict.fromkeys(
        MODULES, True
    )
    assert opened[504].can_attempt is True
    assert opened[504].attempt_started is False
    assert [item.opened for item in report.not_enrolled.activities] == [False] * 4
    assert {item.error_code for item in report.not_enrolled.activities} == {
        "requireloginerror"
    }
    assert report.enrolled_opens_all_activities is True
    assert report.not_enrolled_rejected is True
    assert report.ok is True
    enrolled_calls = [
        function for user, function in fake.student_calls if user == STUDENT[0]
    ]
    assert enrolled_calls == [
        "mod_page_view_page",
        "mod_assign_view_assign",
        "mod_url_view_url",
        "mod_quiz_view_quiz",
        "mod_quiz_get_quiz_access_information",
    ]
    assert fake.attempts == {}


def test_quiz_attempt_can_really_be_started_and_is_finished_right_away():
    fake = enrolled_fake()

    report = verify(fake, start_quiz=True)

    quiz = next(item for item in report.enrolled.activities if item.modname == "quiz")
    assert quiz.attempt_started is True
    assert report.ok is True
    assert [
        (attempt["user"], attempt["state"]) for attempt in fake.attempts.values()
    ] == [(STUDENT[0], "finished")]
    assert not any(
        function == "mod_quiz_start_attempt"
        for user, function in fake.student_calls
        if user == OTHER[0]
    )


def test_quiz_that_cannot_be_started_fails_the_report():
    fake = enrolled_fake()
    fake.student_failures["mod_quiz_start_attempt"] = moodle_exception(
        "noquestions", "This quiz has no questions."
    )

    report = verify(fake, start_quiz=True)

    quiz = next(item for item in report.enrolled.activities if item.modname == "quiz")
    assert (quiz.opened, quiz.attempt_started, quiz.error_code) == (
        True,
        False,
        "noquestions",
    )
    assert report.enrolled_opens_all_activities is False
    assert report.ok is False


def test_hidden_activity_cannot_be_opened_until_it_is_shown_again():
    fake = enrolled_fake()
    fake.module(502)["visible"] = 0

    hidden = verify(fake)
    shown = with_access(fake, lambda access: access.ensure_visible(COURSE_ID))
    after = verify(fake)

    assignment = next(
        item for item in hidden.enrolled.activities if item.modname == "assign"
    )
    assert hidden.visibility.hidden_activities == (502,)
    assert (assignment.opened, assignment.error_code) == (False, "requireloginerror")
    assert hidden.ok is False
    assert shown.hidden_activities == ()
    assert fake.module(502)["visible"] == 1
    assert after.ok is True


def test_activity_checks_can_be_skipped_for_a_structure_only_course():
    fake = enrolled_fake()

    report = verify(fake, check_activities=False)

    assert report.enrolled.activities == ()
    assert report.not_enrolled.activities == ()
    assert [function for _, function in fake.student_calls] == []
    assert report.ok is True


def test_modules_that_are_not_execution_activities_are_not_opened():
    fake = enrolled_fake()
    fake.sections[COURSE_ID][1]["modules"].append(
        {"id": 599, "instance": 99, "name": "Forum", "modname": "forum", "visible": 1}
    )

    report = verify(fake)

    assert 599 in [item.moodle_module_id for item in report.visibility.activities]
    assert 599 not in [item.moodle_module_id for item in report.enrolled.activities]
    assert report.ok is True


def test_report_lists_activities_without_passwords():
    fake = enrolled_fake()

    data = verify(fake).to_dict()

    assert data["enrolled_opens_all_activities"] is True
    assert data["visibility"]["activities"] == 4
    assert data["enrolled"]["activities"][0] == {
        "moodle_module_id": 501,
        "modname": "page",
        "name": "Pengantar HTML",
        "section": 1,
        "opened": True,
        "error_code": None,
        "can_attempt": None,
        "attempt_started": False,
    }
    assert STUDENT[1] not in str(data) and OTHER[1] not in str(data)


def test_demo_script_reports_every_activity_type():
    fake = StudentActivityMoodle()

    async def scenario(access):
        return await run(
            access, COURSE_ID, enrolled=STUDENT, not_enrolled=OTHER, start_quiz=True
        )

    report, enrolled_now = with_access(fake, scenario)
    text = format_report(report, enrolled_now=enrolled_now)

    assert "[OK] Minggu 1 - Learning material (page) 'Pengantar HTML' dibuka" in text
    assert "[OK] Minggu 1 - Learning resource (url) 'Artikel HTML' dibuka" in text
    assert "[OK] Minggu 1 - Assignment 'Tugas 1' dibuka" in text
    assert (
        "[OK] Minggu 1 - Quiz 'Kuis 1' dibuka, attempt dimulai lalu diselesaikan"
        in text
    )
    assert "[OK] mhs.uji2 (tidak terdaftar) ditolak pada 4/4 activity" in text
    assert text.endswith("Hasil: student access TERBUKTI.")