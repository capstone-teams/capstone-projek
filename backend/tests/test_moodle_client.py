import asyncio
import json
import logging
from types import SimpleNamespace
from urllib.parse import parse_qs

import httpx
import pytest

from src.services.moodle_client import MoodleClient, flatten_params
from src.services.moodle_exceptions import (
    MoodleAPIError,
    MoodleAuthenticationError,
    MoodleConnectionError,
    MoodleError,
    MoodlePermissionError,
    MoodleTimeoutError,
)

TOKEN = "s3cr3t-token-abc123"
BASE_URL = "http://moodle.test/moodle"
ENDPOINT = "http://moodle.test/moodle/webservice/rest/server.php"


def run(coro):
    return asyncio.run(coro)


async def call_moodle(handler, wsfunction="core_webservice_get_site_info", params=None, **kwargs):
    client = MoodleClient(BASE_URL, TOKEN, transport=httpx.MockTransport(handler), **kwargs)
    try:
        return await client.call(wsfunction, params)
    finally:
        await client.aclose()


def json_response(payload, status=200):
    return httpx.Response(status, json=payload)


def moodle_exception(errorcode, message="error", exception="moodle_exception"):
    return {"exception": exception, "errorcode": errorcode, "message": message}


def test_successful_authenticated_request_returns_parsed_data():
    seen = []

    def handler(request):
        seen.append(request)
        return json_response({"sitename": "Moodle ITK", "functions": [{"name": "core_course_get_courses"}]})

    result = run(call_moodle(handler))

    assert result == {"sitename": "Moodle ITK", "functions": [{"name": "core_course_get_courses"}]}
    assert len(seen) == 1
    request = seen[0]
    assert request.method == "POST"
    assert str(request.url) == ENDPOINT
    body = parse_qs(request.content.decode())
    assert body["wstoken"] == [TOKEN]
    assert body["wsfunction"] == ["core_webservice_get_site_info"]
    assert body["moodlewsrestformat"] == ["json"]


def test_token_is_sent_in_body_and_never_in_url():
    seen = []

    def handler(request):
        seen.append(request)
        return json_response([])

    run(call_moodle(handler, params={"ids": [1]}))

    assert TOKEN not in str(seen[0].url)
    assert TOKEN in seen[0].content.decode()


def test_base_url_trailing_slash_is_normalized():
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return json_response({})

    async def scenario():
        client = MoodleClient(BASE_URL + "/", TOKEN, transport=httpx.MockTransport(handler))
        try:
            await client.call("core_webservice_get_site_info")
        finally:
            await client.aclose()

    run(scenario())
    assert seen == [ENDPOINT]


def test_null_json_response_is_returned_as_none():
    assert run(call_moodle(lambda request: httpx.Response(200, content=b"null"))) is None


def test_client_is_reusable_for_different_functions_without_business_logic():
    functions = []

    def handler(request):
        functions.append(parse_qs(request.content.decode())["wsfunction"][0])
        return json_response({"ok": True})

    async def scenario():
        async with MoodleClient(BASE_URL, TOKEN, transport=httpx.MockTransport(handler)) as client:
            await client.call("core_course_get_courses")
            await client.call("core_enrol_get_enrolled_users", {"courseid": 3})
            await client.call("mod_quiz_get_quizzes_by_courses", {"courseids": [3]})

    run(scenario())
    assert functions == [
        "core_course_get_courses",
        "core_enrol_get_enrolled_users",
        "mod_quiz_get_quizzes_by_courses",
    ]


def test_flatten_params_uses_moodle_array_syntax():
    assert flatten_params({"courseids": [1, 2]}) == {"courseids[0]": "1", "courseids[1]": "2"}
    assert flatten_params(
        {"courses": [{"fullname": "API Test", "shortname": "api-test", "visible": True, "summary": None}]}
    ) == {
        "courses[0][fullname]": "API Test",
        "courses[0][shortname]": "api-test",
        "courses[0][visible]": "1",
    }
    assert flatten_params({"flag": False, "id": 5}) == {"flag": "0", "id": "5"}


def test_nested_params_are_encoded_in_request_body():
    seen = []

    def handler(request):
        seen.append(parse_qs(request.content.decode()))
        return json_response([])

    run(call_moodle(handler, "core_user_get_users", {"criteria": [{"key": "email", "value": "a@b.id"}]}))

    assert seen[0]["criteria[0][key]"] == ["email"]
    assert seen[0]["criteria[0][value]"] == ["a@b.id"]


def test_caller_cannot_override_client_owned_params():
    def handler(request):
        raise AssertionError("request must not be sent")

    for reserved in ("wstoken", "wsfunction", "moodlewsrestformat"):
        with pytest.raises(ValueError):
            run(call_moodle(handler, params={reserved: "x"}))


def test_invalid_token_raises_authentication_error():
    def handler(request):
        return json_response(moodle_exception("invalidtoken", "Invalid token - token not found"))

    with pytest.raises(MoodleAuthenticationError) as info:
        run(call_moodle(handler))

    error = info.value
    assert error.code == "invalidtoken"
    assert error.wsfunction == "core_webservice_get_site_info"
    assert error.retryable is False
    assert isinstance(error, MoodleError)


def test_expired_token_raises_authentication_error():
    def handler(request):
        return json_response(moodle_exception("invalidtimedtoken", "Invalid token - token expired"))

    with pytest.raises(MoodleAuthenticationError):
        run(call_moodle(handler))


def test_http_401_raises_authentication_error():
    with pytest.raises(MoodleAuthenticationError):
        run(call_moodle(lambda request: httpx.Response(401)))


def test_access_exception_raises_permission_error():
    def handler(request):
        return json_response(
            moodle_exception("accessexception", "Access control exception", "webservice_access_exception")
        )

    with pytest.raises(MoodlePermissionError) as info:
        run(call_moodle(handler, "core_course_create_courses"))

    assert info.value.retryable is False


def test_http_403_raises_permission_error():
    with pytest.raises(MoodlePermissionError):
        run(call_moodle(lambda request: httpx.Response(403)))


def test_other_moodle_exception_raises_api_error_with_extracted_details():
    def handler(request):
        return json_response(
            {
                "exception": "invalid_parameter_exception",
                "errorcode": "invalidparameter",
                "message": "Invalid parameter value detected",
                "debuginfo": "internal server path /var/www/moodle/secret.php",
            }
        )

    with pytest.raises(MoodleAPIError) as info:
        run(call_moodle(handler))

    error = info.value
    assert error.code == "invalidparameter"
    assert error.message == "Invalid parameter value detected"
    assert "debuginfo" not in json.dumps(error.to_dict())
    assert "/var/www" not in json.dumps(error.to_dict())


def test_http_503_is_api_error_and_marked_retryable():
    with pytest.raises(MoodleAPIError) as info:
        run(call_moodle(lambda request: httpx.Response(503)))

    assert info.value.http_status == 503
    assert info.value.retryable is True


def test_http_500_is_api_error_and_not_marked_retryable():
    with pytest.raises(MoodleAPIError) as info:
        run(call_moodle(lambda request: httpx.Response(500)))

    assert info.value.http_status == 500
    assert info.value.retryable is False


def test_non_json_response_raises_api_error():
    def handler(request):
        return httpx.Response(200, content=b"<html>Login page</html>")

    with pytest.raises(MoodleAPIError) as info:
        run(call_moodle(handler))

    assert info.value.code == "invalid_response"


def test_timeout_raises_moodle_timeout_error():
    def handler(request):
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(MoodleTimeoutError) as info:
        run(call_moodle(handler, timeout=0.5))

    assert info.value.retryable is True


def test_connection_failure_raises_moodle_connection_error():
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(MoodleConnectionError) as info:
        run(call_moodle(handler))

    assert info.value.retryable is True


def test_credential_never_appears_in_repr_or_str():
    client = MoodleClient(BASE_URL, TOKEN)

    assert TOKEN not in repr(client)
    assert TOKEN not in str(client)
    assert BASE_URL in repr(client)
    run(client.aclose())


def test_token_echoed_by_moodle_is_redacted_from_error_message():
    def handler(request):
        return json_response(moodle_exception("invalidtoken", f"Invalid token {TOKEN}"))

    with pytest.raises(MoodleAuthenticationError) as info:
        run(call_moodle(handler))

    error = info.value
    assert TOKEN not in str(error)
    assert TOKEN not in json.dumps(error.to_dict())
    assert "***" in error.message


def test_error_dict_is_json_serializable_and_credential_free():
    def handler(request):
        return json_response(moodle_exception("invalidtoken", "Invalid token - token not found"))

    with pytest.raises(MoodleAuthenticationError) as info:
        run(call_moodle(handler))

    payload = info.value.to_dict()
    assert payload["error"] == "authentication_error"
    assert payload["code"] == "invalidtoken"
    assert TOKEN not in json.dumps(payload)


def test_credential_never_written_to_logs(caplog):
    caplog.set_level(logging.DEBUG)

    def ok_handler(request):
        return json_response({"ok": True})

    def auth_handler(request):
        return json_response(moodle_exception("invalidtoken", f"Invalid token {TOKEN}"))

    def timeout_handler(request):
        raise httpx.ReadTimeout("timed out", request=request)

    def connect_handler(request):
        raise httpx.ConnectError(f"cannot connect with {TOKEN}", request=request)

    run(call_moodle(ok_handler))
    for handler in (auth_handler, timeout_handler, connect_handler):
        with pytest.raises(MoodleError):
            run(call_moodle(handler))

    assert caplog.records, "the client is expected to log something"
    assert TOKEN not in caplog.text
    for record in caplog.records:
        assert TOKEN not in record.getMessage()


def test_connection_error_message_redacts_token_from_underlying_error():
    def handler(request):
        raise httpx.ConnectError(f"cannot connect with {TOKEN}", request=request)

    with pytest.raises(MoodleConnectionError) as info:
        run(call_moodle(handler))

    assert TOKEN not in str(info.value)


def test_invalid_construction_arguments_are_rejected():
    with pytest.raises(ValueError):
        MoodleClient("moodle.test/moodle", TOKEN)
    with pytest.raises(ValueError):
        MoodleClient(BASE_URL, "")
    with pytest.raises(ValueError):
        MoodleClient(BASE_URL, "   ")
    with pytest.raises(ValueError):
        MoodleClient(BASE_URL, TOKEN, timeout=0)


def test_empty_wsfunction_is_rejected():
    with pytest.raises(ValueError):
        run(call_moodle(lambda request: json_response({}), wsfunction=""))


def test_from_settings_reads_moodle_configuration():
    settings = SimpleNamespace(MOODLE_BASE_URL=BASE_URL, MOODLE_WEB_SERVICE_TOKEN=TOKEN)
    seen = []

    def handler(request):
        seen.append(parse_qs(request.content.decode())["wstoken"][0])
        return json_response({})

    async def scenario():
        client = MoodleClient.from_settings(settings, transport=httpx.MockTransport(handler))
        try:
            await client.call("core_webservice_get_site_info")
        finally:
            await client.aclose()

    run(scenario())
    assert seen == [TOKEN]