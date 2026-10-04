import asyncio
from urllib.parse import parse_qs

import httpx
import pytest

from src.services.moodle_adapter import MoodleAdapter
from src.services.moodle_adapter_exceptions import (
    MoodleAuthenticationFailedError,
    MoodlePermissionDeniedError,
    MoodleTransientError,
    MoodleValidationFailedError,
)
from src.services.moodle_client import MoodleClient
from src.services.moodle_mapping import InMemoryMoodleMappingRepository, MoodleMapping
from src.services.moodle_retry import RetryPolicy

TOKEN = "test-token"
BASE_URL = "http://moodle.test"
COURSE = {"id": 42, "fullname": "Computer Science 101", "shortname": "cs101", "visible": 1}


def run(coro):
    return asyncio.run(coro)


class Recorder:
    def __init__(self, responder):
        self.responder = responder
        self.calls = []
        self.delays = []

    def handler(self, request):
        function = parse_qs(request.content.decode())["wsfunction"][0]
        self.calls.append(function)
        return self.responder(function, self.calls.count(function), request)

    async def sleep(self, seconds):
        self.delays.append(seconds)

    def count(self, function):
        return self.calls.count(function)


def make_adapter(responder, policy=None):
    recorder = Recorder(responder)
    client = MoodleClient(BASE_URL, TOKEN, transport=httpx.MockTransport(recorder.handler))
    repo = InMemoryMoodleMappingRepository()
    adapter = MoodleAdapter(client, repo, retry_policy=policy, sleep=recorder.sleep)
    return adapter, repo, client, recorder


def timeout(request):
    raise httpx.ReadTimeout("timeout", request=request)


def moodle_exception(errorcode):
    return httpx.Response(
        200, json={"exception": "moodle_exception", "errorcode": errorcode, "message": "error"}
    )


def test_read_is_retried_after_transient_failure_and_then_succeeds():
    def responder(function, number, request):
        if number < 3:
            timeout(request)
        return httpx.Response(200, json=[COURSE])

    adapter, repo, client, recorder = make_adapter(responder)

    async def scenario():
        await repo.save(MoodleMapping("course", "course_1", 42))
        dto = await adapter.get_course("course_1")
        assert dto.moodle_id == 42
        assert recorder.count("core_course_get_courses") == 3
        assert recorder.delays == [0.5, 1.0]
        await client.aclose()

    run(scenario())


def test_read_gives_up_after_max_attempts():
    adapter, repo, client, recorder = make_adapter(lambda function, number, request: timeout(request))

    async def scenario():
        await repo.save(MoodleMapping("course", "course_1", 42))
        with pytest.raises(MoodleTransientError):
            await adapter.get_course("course_1")
        assert recorder.count("core_course_get_courses") == 3
        assert len(recorder.delays) == 2
        await client.aclose()

    run(scenario())


def test_retry_respects_custom_policy():
    adapter, repo, client, recorder = make_adapter(
        lambda function, number, request: timeout(request), RetryPolicy(max_attempts=2)
    )

    async def scenario():
        await repo.save(MoodleMapping("course", "course_1", 42))
        with pytest.raises(MoodleTransientError):
            await adapter.get_course("course_1")
        assert recorder.count("core_course_get_courses") == 2
        await client.aclose()

    run(scenario())


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (lambda function, number, request: moodle_exception("invalidtoken"), MoodleAuthenticationFailedError),
        (lambda function, number, request: httpx.Response(401), MoodleAuthenticationFailedError),
        (lambda function, number, request: moodle_exception("accessexception"), MoodlePermissionDeniedError),
        (lambda function, number, request: httpx.Response(403), MoodlePermissionDeniedError),
        (lambda function, number, request: moodle_exception("invalidparameter"), MoodleValidationFailedError),
    ],
)
def test_non_transient_failures_are_never_retried(response, expected):
    adapter, repo, client, recorder = make_adapter(response)

    async def scenario():
        await repo.save(MoodleMapping("course", "course_1", 42))
        with pytest.raises(expected):
            await adapter.get_course("course_1")
        assert recorder.count("core_course_get_courses") == 1
        assert recorder.delays == []
        await client.aclose()

    run(scenario())


def test_update_course_is_retried_after_transient_failure():
    def responder(function, number, request):
        if function == "core_course_update_courses":
            if number == 1:
                timeout(request)
            return httpx.Response(200, json={"warnings": []})
        return httpx.Response(200, json=[COURSE])

    adapter, repo, client, recorder = make_adapter(responder)

    async def scenario():
        await repo.save(MoodleMapping("course", "course_1", 42))
        await adapter.update_course("course_1", fullname="Judul Baru")
        assert recorder.count("core_course_update_courses") == 2
        await client.aclose()

    run(scenario())


def test_create_course_adopts_existing_course_after_timeout_instead_of_creating_again():
    def responder(function, number, request):
        if function == "core_course_create_courses":
            timeout(request)
        return httpx.Response(200, json={"courses": [{"id": 77, "shortname": "cs101"}], "warnings": []})

    adapter, repo, client, recorder = make_adapter(responder)

    async def scenario():
        dto = await adapter.create_course("course_1", "CS 101", "cs101")
        assert dto.moodle_id == 77
        assert recorder.count("core_course_create_courses") == 1
        assert await repo.get_moodle_id("course", "course_1") == 77
        await client.aclose()

    run(scenario())


def test_create_course_retries_when_the_timed_out_request_did_not_create_anything():
    def responder(function, number, request):
        if function == "core_course_create_courses":
            if number == 1:
                timeout(request)
            return httpx.Response(200, json=[{"id": 88, "shortname": "cs101"}])
        return httpx.Response(200, json={"courses": [], "warnings": []})

    adapter, repo, client, recorder = make_adapter(responder)

    async def scenario():
        dto = await adapter.create_course("course_1", "CS 101", "cs101")
        assert dto.moodle_id == 88
        assert recorder.count("core_course_create_courses") == 2
        assert await repo.get_moodle_id("course", "course_1") == 88
        await client.aclose()

    run(scenario())


def test_create_course_stops_after_max_attempts_without_saving_mapping():
    def responder(function, number, request):
        if function == "core_course_create_courses":
            timeout(request)
        return httpx.Response(200, json={"courses": [], "warnings": []})

    adapter, repo, client, recorder = make_adapter(responder)

    async def scenario():
        with pytest.raises(MoodleTransientError):
            await adapter.create_course("course_1", "CS 101", "cs101")
        assert recorder.count("core_course_create_courses") == 3
        assert await repo.exists("course", "course_1") is False
        await client.aclose()

    run(scenario())


def test_create_course_does_not_retry_validation_failure():
    def responder(function, number, request):
        return moodle_exception("shortnametaken")

    adapter, repo, client, recorder = make_adapter(responder)

    async def scenario():
        with pytest.raises(MoodleValidationFailedError):
            await adapter.create_course("course_1", "CS 101", "cs101")
        assert recorder.count("core_course_create_courses") == 1
        assert recorder.delays == []
        await client.aclose()

    run(scenario())


def test_retry_delay_grows_exponentially_up_to_the_cap():
    policy = RetryPolicy(base_delay=1.0, max_delay=3.0)

    assert [policy.delay_for(attempt) for attempt in (1, 2, 3, 4)] == [1.0, 2.0, 3.0, 3.0]


def test_retry_policy_rejects_invalid_values():
    with pytest.raises(ValueError):
        RetryPolicy(max_attempts=0)
    with pytest.raises(ValueError):
        RetryPolicy(base_delay=-1)