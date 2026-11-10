"""Test script demo student access ``scripts.verify_student_access`` (BE-16.3)."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from scripts.verify_student_access import format_report, main, run, student_credentials
from src.services.moodle_client import MoodleClient
from src.services.moodle_integration_service import MoodleIntegrationService
from src.services.moodle_student_access import (
    MoodleStudentAccessService,
    StudentAccessSetupError,
)
from tests.moodle_fakes import BASE_URL, TOKEN, StudentMoodle
from tests.moodle_fakes import OTHER_STUDENT_ACCOUNT as OTHER
from tests.moodle_fakes import STUDENT_ACCOUNT as STUDENT
from tests.moodle_fakes import STUDENT_COURSE_ID as COURSE_ID

ENV = {"MOODLE_STUDENT_PASSWORD": STUDENT[1], "MOODLE_STUDENT2_PASSWORD": OTHER[1]}


def demo(fake, **kwargs):
    async def go():
        transport = httpx.MockTransport(fake.handler)
        async with MoodleClient(BASE_URL, TOKEN, transport=transport) as client:
            access = MoodleStudentAccessService(
                MoodleIntegrationService(client), base_url=BASE_URL, transport=transport
            )
            return await run(
                access, COURSE_ID, enrolled=STUDENT, not_enrolled=OTHER, **kwargs
            )

    return asyncio.run(go())


def test_credentials_default_to_the_test_accounts():
    assert student_credentials(ENV) == (STUDENT, OTHER)


@pytest.mark.parametrize(
    "env",
    [
        {},
        {"MOODLE_STUDENT_PASSWORD": "x"},
        {**ENV, "MOODLE_STUDENT_USERNAME": "mhs.uji2"},
    ],
)
def test_incomplete_credentials_are_rejected(env):
    with pytest.raises(StudentAccessSetupError):
        student_credentials(env)


def test_demo_enrols_the_student_and_proves_access():
    fake = StudentMoodle()

    report, enrolled_now = demo(fake)
    text = format_report(report, enrolled_now=enrolled_now)

    assert report.ok is True
    assert enrolled_now is True
    assert "[OK] mhs.uji didaftarkan sebagai student" in text
    assert "[OK] mhs.uji membuka course dan melihat 3/3 section mingguan" in text
    assert "[OK] mhs.uji2 (tidak terdaftar) ditolak Moodle: requireloginerror" in text
    assert text.endswith("Hasil: student access TERBUKTI.")
    assert STUDENT[1] not in text and OTHER[1] not in text


def test_hidden_section_fails_the_demo_unless_it_is_shown():
    hidden = StudentMoodle()
    hidden.sections[COURSE_ID][2]["visible"] = 0
    shown = StudentMoodle()
    shown.sections[COURSE_ID][2]["visible"] = 0

    failed, _ = demo(hidden)
    fixed, _ = demo(shown, show_hidden=True)

    assert failed.ok is False
    assert "[GAGAL] 3 section mingguan, tersembunyi: minggu 2" in format_report(
        failed, enrolled_now=True
    )
    assert fixed.ok is True


def test_without_enrolment_the_student_is_rejected_and_the_demo_fails():
    fake = StudentMoodle()

    report, enrolled_now = demo(fake, enrol=False)
    text = format_report(report, enrolled_now=enrolled_now)

    assert report.ok is False
    assert "[GAGAL] mhs.uji ditolak Moodle (requireloginerror)" in text
    assert fake.called("enrol_manual_enrol_users") == []


def test_main_stops_before_calling_moodle_when_passwords_are_missing(capsys):
    assert asyncio.run(main(["--course-id", "2"], env={})) == 2
    assert "MOODLE_STUDENT_PASSWORD" in capsys.readouterr().err