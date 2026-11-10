"""Retry terbatas Moodle client dan skenario kegagalan tanpa objek duplikat (BE-04.5)."""

import asyncio
import logging
from urllib.parse import parse_qs

import httpx
import pytest

from src.services.moodle_adapter import COURSE_ENTITY_TYPE, MoodleAdapter
from src.services.moodle_adapter_exceptions import MoodleOperationFailedError
from src.services.moodle_client import MoodleClient, is_safe_to_retry
from src.services.moodle_error_category import MoodleErrorCategory, normalize_moodle_error
from src.services.moodle_exceptions import (
    MoodleAPIError,
    MoodleAuthenticationError,
    MoodleConnectionError,
    MoodlePermissionError,
    MoodleTimeoutError,
)
from src.services.moodle_mapping import InMemoryMoodleMappingRepository
from src.services.moodle_page_service import PAGE_ENTITY_TYPE, LearningMaterialPage, MoodlePageService

TOKEN = "retry-test-token-5d1e"


def run(coro):
    return asyncio.run(coro)


class Recorder:
    """Transport tiruan: menjalankan daftar respons berurutan dan mencatat jeda backoff."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []
        self.sleeps = []

    def handler(self, request):
        self.requests.append(request)
        response = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        if isinstance(response, Exception):
            raise response
        return response

    async def sleep(self, seconds):
        self.sleeps.append(seconds)

    def client(self, **kwargs):
        return MoodleClient(
            "http://moodle.test", TOKEN, transport=httpx.MockTransport(self.handler), sleep=self.sleep, **kwargs
        )


def call(recorder, wsfunction, params=None, **kwargs):
    async def scenario():
        async with recorder.client() as client:
            return await client.call(wsfunction, params, **kwargs)

    return run(scenario())


OK = httpx.Response(200, json={"ok": True})
UNAVAILABLE = httpx.Response(503)
TIMEOUT = httpx.ReadTimeout("timed out")
REFUSED = httpx.ConnectError("connection refused")


def test_transient_error_on_a_read_is_retried_with_exponential_backoff():
    recorder = Recorder(TIMEOUT, REFUSED, OK)

    assert call(recorder, "core_course_get_courses") == {"ok": True}

    assert len(recorder.requests) == 3
    assert recorder.sleeps == [0.5, 1.0]


def test_retries_are_bounded_and_the_last_error_is_raised():
    recorder = Recorder(UNAVAILABLE)

    with pytest.raises(MoodleAPIError) as caught:
        call(recorder, "core_course_get_contents", {"courseid": 2})

    assert caught.value.retryable is True
    assert len(recorder.requests) == 3  # 1 percobaan + 2 retry
    assert recorder.sleeps == [0.5, 1.0]


@pytest.mark.parametrize(
    ("payload", "error"),
    [
        ({"exception": "moodle_exception", "errorcode": "invalidtoken", "message": "x"}, MoodleAuthenticationError),
        ({"exception": "webservice_access_exception", "errorcode": "accessexception", "message": "x"},
         MoodlePermissionError),
        ({"exception": "invalid_parameter_exception", "errorcode": "invalidparameter", "message": "x"},
         MoodleAPIError),
    ],
)
def test_authentication_permission_and_validation_errors_are_never_retried(payload, error):
    recorder = Recorder(httpx.Response(200, json=payload))

    with pytest.raises(error):
        call(recorder, "core_course_get_courses")

    assert len(recorder.requests) == 1
    assert recorder.sleeps == []


@pytest.mark.parametrize(
    ("wsfunction", "params"),
    [
        ("core_course_create_courses", {"courses": [{"shortname": "BD101"}]}),
        ("core_courseformat_update_course", {"action": "section_add", "courseid": 2}),
        ("local_capstonebridge_create_page", {"courseid": 2, "section": 1, "name": "x", "content": "y"}),
    ],
)
def test_operations_that_are_not_safe_to_repeat_are_not_retried(wsfunction, params):
    recorder = Recorder(TIMEOUT)

    with pytest.raises(MoodleTimeoutError):
        call(recorder, wsfunction, params)

    assert len(recorder.requests) == 1


def test_retry_can_be_forced_on_or_off_by_the_caller():
    forced_off = Recorder(REFUSED)
    with pytest.raises(MoodleConnectionError):
        call(forced_off, "core_course_get_courses", retry=False)
    assert len(forced_off.requests) == 1

    forced_on = Recorder(REFUSED, OK)
    assert call(forced_on, "core_course_create_courses", retry=True) == {"ok": True}
    assert len(forced_on.requests) == 2


def test_max_retries_and_backoff_are_configurable():
    recorder = Recorder(UNAVAILABLE)

    async def scenario():
        async with recorder.client(max_retries=4, backoff_seconds=2.0) as client:
            await client.call("core_course_get_courses")

    with pytest.raises(MoodleAPIError):
        run(scenario())

    assert len(recorder.requests) == 5
    assert recorder.sleeps == [2.0, 4.0, 5.0, 5.0]  # dibatasi MAX_BACKOFF_SECONDS


@pytest.mark.parametrize("kwargs", [{"max_retries": -1}, {"backoff_seconds": -0.1}])
def test_invalid_retry_configuration_is_rejected(kwargs):
    with pytest.raises(ValueError):
        MoodleClient("http://moodle.test", TOKEN, **kwargs)


@pytest.mark.parametrize(
    ("wsfunction", "params", "expected"),
    [
        ("core_webservice_get_site_info", None, True),
        ("core_course_get_contents", {"courseid": 2}, True),
        ("mod_page_get_pages_by_courses", None, True),
        ("core_update_inplace_editable", None, True),
        ("enrol_manual_enrol_users", None, True),
        ("core_course_update_courses", None, True),
        ("local_capstonebridge_update_page", None, True),
        ("local_capstonebridge_create_quiz", {"idnumber": "capstone-quiz-1"}, True),
        ("local_capstonebridge_create_url", {"idnumber": ""}, False),
        ("core_course_create_courses", None, False),
        ("core_courseformat_update_course", None, False),
        ("core_user_create_users", None, False),
        ("mod_quiz_process_attempt", None, False),
    ],
)
def test_safe_to_retry_policy(wsfunction, params, expected):
    assert is_safe_to_retry(wsfunction, params) is expected


def test_retry_logs_never_contain_the_token(caplog):
    caplog.set_level(logging.DEBUG)
    recorder = Recorder(httpx.ConnectError(f"refused for token {TOKEN}"), OK)

    call(recorder, "core_course_get_courses")

    assert "retrying" in caplog.text
    assert TOKEN not in caplog.text


# --- Skenario kegagalan tanpa objek duplikat ----------------------------------


class FlakyBridgePlugin:
    """Plugin tiruan yang sudah menyimpan page, lalu koneksinya putus sebelum menjawab."""

    def __init__(self, drop_first_response):
        self.modules = {}
        self.drop_first_response = drop_first_response
        self.calls = []

    def handler(self, request):
        body = {key: values[0] for key, values in parse_qs(request.content.decode(), keep_blank_values=True).items()}
        function = body["wsfunction"]
        self.calls.append(function)
        if function == "local_capstonebridge_create_page":
            existing = next((cmid for cmid, m in self.modules.items() if m["idnumber"] == body["idnumber"]), None)
            if existing is None:
                existing = 900 + len(self.modules)
                self.modules[existing] = {"idnumber": body["idnumber"], "section": int(body["section"])}
                result = {"cmid": existing, "instanceid": existing + 1000, "created": 1}
            else:
                result = {"cmid": existing, "instanceid": existing + 1000, "created": 0}
        elif function == "local_capstonebridge_update_page":
            cmid = int(body["cmid"])
            self.modules[cmid]["section"] = int(body["section"])
            result = {"cmid": cmid, "instanceid": cmid + 1000, "section": int(body["section"]), "updated": 1}
        else:
            raise AssertionError(function)
        if self.drop_first_response:
            self.drop_first_response = False
            raise httpx.ReadTimeout("connection dropped after Moodle saved the page")
        return httpx.Response(200, json=result)


def test_timeout_after_moodle_created_the_page_does_not_create_a_duplicate():
    plugin = FlakyBridgePlugin(drop_first_response=True)
    mappings = InMemoryMoodleMappingRepository()
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    async def scenario():
        async with MoodleClient(
            "http://moodle.test", TOKEN, transport=httpx.MockTransport(plugin.handler), sleep=fake_sleep
        ) as client:
            return await MoodlePageService(client, mappings).publish(
                2, 1, LearningMaterialPage(id="content-1", title="Materi", content_html="<p>Isi</p>")
            )

    result = run(scenario())

    assert len(plugin.modules) == 1
    assert sleeps == [0.5]
    assert plugin.calls[:2] == ["local_capstonebridge_create_page", "local_capstonebridge_create_page"]
    assert run(mappings.get_moodle_id(PAGE_ENTITY_TYPE, "content-1")) == result.cmid


class FlakyCourseMoodle:
    """Moodle tiruan yang menyimpan course, lalu jawaban create pertama hilang."""

    def __init__(self):
        self.courses = {}
        self.drop_next_create_response = True

    def handler(self, request):
        body = {key: values[0] for key, values in parse_qs(request.content.decode()).items()}
        if body["wsfunction"] != "core_course_create_courses":
            raise AssertionError(body["wsfunction"])
        shortname = body["courses[0][shortname]"]
        if any(course == shortname for course in self.courses.values()):
            return httpx.Response(
                200, json={"exception": "moodle_exception", "errorcode": "shortnametaken", "message": "taken"}
            )
        course_id = 10 + len(self.courses)
        self.courses[course_id] = shortname
        if self.drop_next_create_response:
            self.drop_next_create_response = False
            raise httpx.ReadTimeout("connection dropped after Moodle created the course")
        return httpx.Response(200, json=[{"id": course_id, "shortname": shortname}])


def test_course_create_is_not_retried_and_a_rerun_cannot_duplicate_it():
    moodle = FlakyCourseMoodle()
    mappings = InMemoryMoodleMappingRepository()

    async def create():
        async with MoodleClient("http://moodle.test", TOKEN, transport=httpx.MockTransport(moodle.handler)) as client:
            return await MoodleAdapter(client, mappings).create_course("course-1", "Basis Data", "BD101")

    with pytest.raises(MoodleOperationFailedError) as first:
        run(create())
    with pytest.raises(MoodleOperationFailedError) as second:
        run(create())

    assert normalize_moodle_error(first.value).category == MoodleErrorCategory.TRANSIENT
    assert normalize_moodle_error(second.value).category == MoodleErrorCategory.VALIDATION
    assert list(moodle.courses.values()) == ["BD101"]
    assert run(mappings.exists(COURSE_ENTITY_TYPE, "course-1")) is False


@pytest.mark.parametrize("code", ["errorcoursecontextnotvalid", "requireloginerror"])
def test_not_enrolled_access_is_a_permission_error_and_not_retried(code):
    recorder = Recorder(httpx.Response(200, json={"exception": "moodle_exception", "errorcode": code, "message": "x"}))

    with pytest.raises(MoodlePermissionError) as caught:
        call(recorder, "core_course_get_contents", {"courseid": 2})

    assert normalize_moodle_error(caught.value).category == MoodleErrorCategory.PERMISSION
    assert len(recorder.requests) == 1