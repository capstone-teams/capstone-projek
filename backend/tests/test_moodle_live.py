import os
import uuid

import pytest
import pytest_asyncio

from src.config.settings import settings
from src.services.moodle_adapter import MoodleAdapter
from src.services.moodle_adapter_exceptions import MoodleAuthenticationFailedError
from src.services.moodle_client import MoodleClient
from src.services.moodle_mapping import InMemoryMoodleMappingRepository

pytestmark = pytest.mark.skipif(
    os.getenv("MOODLE_LIVE_TESTS") != "1",
    reason="Set MOODLE_LIVE_TESTS=1 untuk menjalankan test terhadap Moodle yang sedang menyala",
)


@pytest_asyncio.fixture
async def live():
    client = MoodleClient(settings.MOODLE_BASE_URL, settings.MOODLE_WEB_SERVICE_TOKEN, timeout=60)
    adapter = MoodleAdapter(client, InMemoryMoodleMappingRepository())
    try:
        yield client, adapter
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_authentication_succeeds_with_the_configured_token(live):
    client, _ = live

    info = await client.call("core_webservice_get_site_info")

    assert "release" in info


@pytest.mark.asyncio
async def test_invalid_token_is_normalized_as_authentication_failure():
    client = MoodleClient(settings.MOODLE_BASE_URL, "token-yang-salah", timeout=60)
    adapter = MoodleAdapter(client, InMemoryMoodleMappingRepository())
    try:
        with pytest.raises(MoodleAuthenticationFailedError):
            await adapter.find_course("apa-saja")
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_course_lifecycle_against_moodle(live):
    _, adapter = live
    suffix = uuid.uuid4().hex[:8]
    internal_id = f"it_{suffix}"
    shortname = f"it-{suffix}"

    created = await adapter.create_course(internal_id, "Integration Test", shortname)
    repeated = await adapter.create_course(internal_id, "Integration Test", shortname)
    found = await adapter.find_course(shortname)
    updated = await adapter.update_course(internal_id, fullname="Integration Test Updated")
    contents = await adapter.get_course_contents(internal_id)

    assert created.moodle_id > 0
    assert repeated.moodle_id == created.moodle_id
    assert found.moodle_id == created.moodle_id
    assert found.internal_id == internal_id
    assert updated.fullname == "Integration Test Updated"
    assert contents