import asyncio
import logging

import httpx
import pytest

from src.services.moodle_adapter import MoodleAdapter
from src.services.moodle_adapter_exceptions import (
    MoodleAuthenticationFailedError,
    MoodleErrorCategory,
    MoodleOperationFailedError,
    MoodlePermissionDeniedError,
    MoodleTransientError,
    MoodleValidationFailedError,
)
from src.services.moodle_client import MoodleClient
from src.services.moodle_mapping import InMemoryMoodleMappingRepository, MoodleMapping
from src.services.moodle_mock import MockMoodleIntegration

TOKEN = "super-secret-token"
BASE_URL = "http://moodle.test"


def run(coro):
    return asyncio.run(coro)


def make_adapter(handler):
    client = MoodleClient(BASE_URL, TOKEN, transport=httpx.MockTransport(handler))
    repo = InMemoryMoodleMappingRepository()
    return MoodleAdapter(client, repo), repo, client


def moodle_exception(errorcode, message="Moodle error", exception="moodle_exception"):
    return httpx.Response(
        200, json={"exception": exception, "errorcode": errorcode, "message": message}
    )


async def failing_read(adapter, repo):
    await repo.save(MoodleMapping("course", "course_1", 42))
    await adapter.get_course("course_1")


def assert_error(handler, expected_class, category, retryable):
    adapter, repo, client = make_adapter(handler)

    async def scenario():
        with pytest.raises(expected_class) as info:
            await failing_read(adapter, repo)
        error = info.value
        assert error.category is category
        assert error.retryable is retryable
        assert error.original_error is not None
        await client.aclose()

    run(scenario())


def test_invalid_token_is_normalized_as_authentication_error():
    assert_error(
        lambda request: moodle_exception("invalidtoken", "Invalid token"),
        MoodleAuthenticationFailedError,
        MoodleErrorCategory.AUTHENTICATION,
        False,
    )


def test_http_401_is_normalized_as_authentication_error():
    assert_error(
        lambda request: httpx.Response(401),
        MoodleAuthenticationFailedError,
        MoodleErrorCategory.AUTHENTICATION,
        False,
    )


def test_access_exception_is_normalized_as_permission_error():
    assert_error(
        lambda request: moodle_exception("accessexception", "Access control exception"),
        MoodlePermissionDeniedError,
        MoodleErrorCategory.PERMISSION,
        False,
    )


def test_http_403_is_normalized_as_permission_error():
    assert_error(
        lambda request: httpx.Response(403),
        MoodlePermissionDeniedError,
        MoodleErrorCategory.PERMISSION,
        False,
    )


def test_invalid_parameter_is_normalized_as_validation_error():
    assert_error(
        lambda request: moodle_exception("invalidparameter", "Invalid parameter value detected"),
        MoodleValidationFailedError,
        MoodleErrorCategory.VALIDATION,
        False,
    )


def test_timeout_is_normalized_as_retryable_transient_error():
    def handler(request):
        raise httpx.ReadTimeout("timeout", request=request)

    assert_error(handler, MoodleTransientError, MoodleErrorCategory.TRANSIENT, True)


def test_connection_failure_is_normalized_as_retryable_transient_error():
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    assert_error(handler, MoodleTransientError, MoodleErrorCategory.TRANSIENT, True)


def test_http_503_is_normalized_as_retryable_transient_error():
    assert_error(
        lambda request: httpx.Response(503),
        MoodleTransientError,
        MoodleErrorCategory.TRANSIENT,
        True,
    )


def test_unknown_moodle_error_is_normalized_as_execution_error():
    assert_error(
        lambda request: moodle_exception("somethingunexpected", "Boom"),
        MoodleOperationFailedError,
        MoodleErrorCategory.EXECUTION,
        False,
    )


def test_error_representation_is_json_safe_and_hides_raw_details():
    adapter, repo, client = make_adapter(lambda request: moodle_exception("invalidparameter", "Bad value"))

    async def scenario():
        with pytest.raises(MoodleValidationFailedError) as info:
            await failing_read(adapter, repo)
        assert info.value.to_dict() == {
            "error": "validation",
            "message": "Operasi Moodle 'core_course_get_courses' gagal: Bad value",
            "code": "invalidparameter",
            "retryable": False,
        }
        await client.aclose()

    run(scenario())


def test_token_never_appears_in_error_message_or_logs(caplog):
    def handler(request):
        return moodle_exception("invalidtoken", f"Token {TOKEN} ditolak")

    adapter, repo, client = make_adapter(handler)

    async def scenario():
        with caplog.at_level(logging.DEBUG):
            with pytest.raises(MoodleAuthenticationFailedError) as info:
                await failing_read(adapter, repo)
        assert TOKEN not in str(info.value)
        assert TOKEN not in str(info.value.to_dict())
        assert TOKEN not in caplog.text
        await client.aclose()

    run(scenario())


def test_mock_reports_validation_error_like_the_real_integration():
    mock = MockMoodleIntegration()

    async def scenario():
        await mock.create_course("course_1", "CS 101", "cs101")
        with pytest.raises(MoodleValidationFailedError):
            await mock.create_course("course_2", "Other", "cs101")

    run(scenario())