import asyncio

import httpx

from src.services.moodle_client import MoodleClient
from src.services.moodle_health import MoodleHealth, MoodleHealthChecker

TOKEN = "super-secret-token"
BASE_URL = "http://moodle.test"
SITE_INFO = {"sitename": "Moodle Lokal", "release": "4.5.14 (Build: 20260916)"}


def run(coro):
    return asyncio.run(coro)


def make_checker(handler):
    client = MoodleClient(BASE_URL, TOKEN, transport=httpx.MockTransport(handler))
    return MoodleHealthChecker(client), client


def moodle_exception(errorcode, message="error"):
    return httpx.Response(
        200, json={"exception": "moodle_exception", "errorcode": errorcode, "message": message}
    )


def test_health_reports_available_with_moodle_release():
    checker, client = make_checker(lambda request: httpx.Response(200, json=SITE_INFO))

    async def scenario():
        health = await checker.check()
        assert health.available is True
        assert health.release == "4.5.14 (Build: 20260916)"
        assert health.latency_ms >= 0
        assert health.error_category is None
        assert health.message is None
        await client.aclose()

    run(scenario())


def test_health_reports_authentication_failure_without_raising():
    checker, client = make_checker(lambda request: moodle_exception("invalidtoken", "Invalid token"))

    async def scenario():
        health = await checker.check()
        assert health.available is False
        assert health.error_category == "authentication"
        assert health.release is None
        await client.aclose()

    run(scenario())


def test_health_reports_connection_failure_as_transient():
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    checker, client = make_checker(handler)

    async def scenario():
        health = await checker.check()
        assert health.available is False
        assert health.error_category == "transient"
        await client.aclose()

    run(scenario())


def test_health_check_does_not_retry():
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("timeout", request=request)

    checker, client = make_checker(handler)

    async def scenario():
        health = await checker.check()
        assert health.available is False
        assert len(calls) == 1
        await client.aclose()

    run(scenario())


def test_health_reports_invalid_site_info_as_unavailable():
    checker, client = make_checker(lambda request: httpx.Response(200, json={"sitename": "tanpa release"}))

    async def scenario():
        health = await checker.check()
        assert health.available is False
        assert health.error_category == "execution"
        await client.aclose()

    run(scenario())


def test_health_never_exposes_the_token():
    checker, client = make_checker(
        lambda request: moodle_exception("invalidtoken", f"Token {TOKEN} ditolak")
    )

    async def scenario():
        health = await checker.check()
        assert TOKEN not in str(health.to_dict())
        await client.aclose()

    run(scenario())


def test_health_to_dict_is_json_friendly():
    health = MoodleHealth(available=True, release="4.5", latency_ms=12)

    assert health.to_dict() == {
        "available": True,
        "release": "4.5",
        "latency_ms": 12,
        "error_category": None,
        "message": None,
    }