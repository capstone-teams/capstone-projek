import asyncio

import httpx
import pytest

from scripts.setup_moodle_test_accounts import (
    ENV_STUDENT_PASSWORD,
    ENV_TEACHER_PASSWORD,
    SetupConfigurationError,
    format_report,
    generate_password,
    setup_test_environment,
)
from src.services.moodle_client import MoodleClient
from src.services.moodle_integration_service import MoodleIntegrationService
from tests.moodle_fakes import BASE_URL, TOKEN, FakeMoodle

ENV = {ENV_TEACHER_PASSWORD: "Dosen#12345", ENV_STUDENT_PASSWORD: "Mhs#12345"}


def run_setup(fake, **kwargs):
    async def scenario():
        async with MoodleClient(BASE_URL, TOKEN, transport=httpx.MockTransport(fake.handler)) as client:
            return await setup_test_environment(MoodleIntegrationService(client), **kwargs)

    return asyncio.run(scenario())


def test_course_accounts_and_enrolments_are_created():
    fake = FakeMoodle()

    result = run_setup(fake, env=ENV)

    assert result.course_created is True
    assert [(item.account.username, item.account.role, item.created) for item in result.accounts] == [
        ("dosen.uji", "teacher", True),
        ("mhs.uji", "student", True),
        ("mhs.uji2", "student", True),
    ]
    enrolled = fake.enrolments[result.moodle_course_id]
    roles = {fake.users[user_id]["username"]: roles for user_id, roles in enrolled.items()}
    assert roles == {"dosen.uji": {3}, "mhs.uji": {5}, "mhs.uji2": {5}}
    assert [params["users[0][password]"] for params in fake.called("core_user_create_users")] == [
        "Dosen#12345", "Mhs#12345", "Mhs#12345"
    ]
    assert all(item.password is None for item in result.accounts)


def test_running_twice_reuses_everything_and_creates_no_duplicates():
    fake = FakeMoodle()
    first = run_setup(fake, env=ENV)

    second = run_setup(fake, env={})  # password tidak dibutuhkan lagi

    assert second.course_created is False
    assert second.moodle_course_id == first.moodle_course_id
    assert all(item.created is False for item in second.accounts)
    assert len(fake.called("core_user_create_users")) == 3
    assert len(fake.called("core_course_create_courses")) == 1
    assert sum(1 for course in fake.courses.values() if course["shortname"] == "capstone-uji") == 1
    assert len(fake.enrolments[first.moodle_course_id]) == 3


def test_generated_passwords_are_shown_once_in_the_report():
    fake = FakeMoodle()

    result = run_setup(fake, generate_passwords=True, env={})
    report = format_report(result)

    passwords = [item.password for item in result.accounts]
    assert all(passwords) and len(set(passwords)) == 3
    for password in passwords:
        assert password in report


def test_missing_password_for_a_new_account_is_reported_before_creating_users():
    fake = FakeMoodle()

    with pytest.raises(SetupConfigurationError):
        run_setup(fake, env={ENV_TEACHER_PASSWORD: "Dosen#12345"})

    assert [p["users[0][username]"] for p in fake.called("core_user_create_users")] == ["dosen.uji"]


def test_generated_password_meets_the_default_moodle_policy():
    for _ in range(20):
        password = generate_password()
        assert len(password) >= 8
        assert any(c.isdigit() for c in password)
        assert any(c.islower() for c in password)
        assert any(c.isupper() for c in password)
        assert any(not c.isalnum() for c in password)