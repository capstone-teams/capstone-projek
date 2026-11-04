import asyncio
import logging

import httpx

from src.services.moodle_client import MoodleClient
from src.services.moodle_health import REQUIRED_FUNCTIONS, MoodleHealth, MoodleHealthChecker

TOKEN = "super-secret-token"
BASE_URL = "http://moodle.test"


def site_info(function_names):
    return {
        "sitename": "Moodle Lokal",
        "release": "4.5.1+ (Build: 20250101)",
        "version": "2024100701",
        "functions": [{"name": name, "version": "2024100700"} for name in function_names],
    }


def run(coro):
    return asyncio.run(coro)


def check(handler, required=REQUIRED_FUNCTIONS):
    async def scenario():
        client = MoodleClient(BASE_URL, TOKEN, transport=httpx.MockTransport(handler))
        try:
            return await MoodleHealthChecker(client, required).check()
        finally:
            await client.aclose()

    return run(scenario())


def moodle_exception(errorcode, message="error", exception="moodle_exception"):
    return httpx.Response(
        200, json={"exception": exception, "errorcode": errorcode, "message": message}
    )


def test_health_reports_version_and_functions_when_everything_is_available():
    health = check(lambda request: httpx.Response(200, json=site_info(REQUIRED_FUNCTIONS)))

    assert health.available is True
    assert health.ready is True
    assert health.site_name == "Moodle Lokal"
    assert health.release == "4.5.1+ (Build: 20250101)"
    assert health.version == "2024100701"
    assert set(REQUIRED_FUNCTIONS) <= set(health.functions)
    assert health.missing_functions == ()
    assert health.latency_ms >= 0
    assert health.error_category is None


def test_health_lists_required_functions_that_are_missing():
    available = [name for name in REQUIRED_FUNCTIONS if name != "local_capstonebridge_create_page"]

    health = check(lambda request: httpx.Response(200, json=site_info(available)))

    assert health.available is True
    assert health.ready is False
    assert health.missing_functions == ("local_capstonebridge_create_page",)


def test_health_uses_the_given_required_function_list():
    health = check(
        lambda request: httpx.Response(200, json=site_info(["core_course_get_courses"])),
        required=("core_course_get_courses",),
    )

    assert health.ready is True


def test_health_reports_invalid_token_as_authentication_failure():
    health = check(lambda request: moodle_exception("invalidtoken", "Invalid token"))

    assert health.available is False
    assert health.ready is False
    assert health.error_category == "authentication"
    assert health.release is None


def test_health_reports_permission_failure():
    health = check(
        lambda request: moodle_exception(
            "accessexception", "Access control exception", "webservice_access_exception"
        )
    )

    assert health.available is False
    assert health.error_category == "permission"


def test_health_reports_connection_failure_as_transient():
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    health = check(handler)

    assert health.available is False
    assert health.error_category == "transient"


def test_health_check_calls_moodle_only_once():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503)

    health = check(handler)

    assert health.available is False
    assert len(calls) == 1


def test_health_reports_invalid_site_info_as_unavailable():
    health = check(lambda request: httpx.Response(200, json={"unexpected": True}))

    assert health.available is False
    assert health.error_category == "execution"


def test_health_never_exposes_the_token(caplog):
    caplog.set_level(logging.DEBUG)

    health = check(lambda request: moodle_exception("invalidtoken", f"Invalid token {TOKEN}"))

    assert TOKEN not in str(health.to_dict())
    assert TOKEN not in caplog.text


def test_health_to_dict_is_json_friendly():
    health = MoodleHealth(
        available=True,
        site_name="Moodle Lokal",
        release="4.5",
        version="2024100701",
        latency_ms=12,
        functions=("core_webservice_get_site_info",),
        missing_functions=("core_course_get_courses",),
    )

    assert health.to_dict() == {
        "available": True,
        "ready": False,
        "site_name": "Moodle Lokal",
        "release": "4.5",
        "version": "2024100701",
        "latency_ms": 12,
        "functions": ["core_webservice_get_site_info"],
        "missing_functions": ["core_course_get_courses"],
        "error_category": None,
        "message": None,
    }