"""Test live opt-in terhadap instance Moodle tim.

Dilewati secara default. Jalankan dengan ``MOODLE_LIVE_TESTS=1`` setelah
``MOODLE_BASE_URL`` dan ``MOODLE_WEB_SERVICE_TOKEN`` pada ``backend/.env``
mengarah ke Moodle yang aktif.
"""

import asyncio
import logging
import os

import pytest

from src.config.settings import Settings
from src.services.moodle_client import MoodleClient
from src.services.moodle_exceptions import MoodleAuthenticationError
from src.services.moodle_health import MoodleHealthChecker

pytestmark = pytest.mark.skipif(
    os.getenv("MOODLE_LIVE_TESTS") != "1",
    reason="Set MOODLE_LIVE_TESTS=1 untuk menjalankan test terhadap Moodle asli",
)


def run(coro):
    return asyncio.run(coro)


def test_site_info_succeeds_against_the_team_moodle(caplog):
    caplog.set_level(logging.DEBUG)
    settings = Settings()

    async def scenario():
        async with MoodleClient.from_settings(settings) as client:
            return await MoodleHealthChecker(client).check()

    health = run(scenario())

    print(f"\nMoodle {health.release} | missing: {list(health.missing_functions)}")
    assert health.available is True
    assert health.release
    assert "core_webservice_get_site_info" in health.functions
    assert settings.MOODLE_WEB_SERVICE_TOKEN not in caplog.text


def test_wrong_token_raises_structured_authentication_error():
    settings = Settings()
    wrong_token = "token-yang-salah-0000"

    async def scenario():
        async with MoodleClient(
            settings.MOODLE_BASE_URL, wrong_token, timeout=settings.moodle_timeout_seconds
        ) as client:
            await client.call("core_webservice_get_site_info")

    with pytest.raises(MoodleAuthenticationError) as caught:
        run(scenario())

    assert caught.value.code == "invalidtoken"
    assert wrong_token not in str(caught.value.to_dict())