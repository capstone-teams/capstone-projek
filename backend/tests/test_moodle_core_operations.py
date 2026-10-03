import asyncio

import httpx
import pytest

from src.services.moodle_adapter import MoodleAdapter
from src.services.moodle_adapter_exceptions import MoodleOperationFailedError
from src.services.moodle_client import MoodleClient
from src.services.moodle_mapping import InMemoryMoodleMappingRepository, MoodleMapping

TOKEN = "test-token"
BASE_URL = "http://moodle.test"


def run(coro):
    return asyncio.run(coro)


def make_adapter(handler):
    client = MoodleClient(BASE_URL, TOKEN, transport=httpx.MockTransport(handler))
    repo = InMemoryMoodleMappingRepository()
    return MoodleAdapter(client, repo), repo, client


def course_payload(moodle_id=42, shortname="cs101"):
    return {
        "courses": [
            {"id": moodle_id, "fullname": "Computer Science 101", "shortname": shortname, "visible": 1}
        ],
        "warnings": [],
    }


def test_find_course_returns_internal_id_when_course_is_mapped():
    adapter, repo, client = make_adapter(lambda request: httpx.Response(200, json=course_payload()))

    async def scenario():
        await repo.save(MoodleMapping("course", "course_1", 42))
        dto = await adapter.find_course("cs101")
        assert dto.internal_id == "course_1"
        assert dto.moodle_id == 42
        assert dto.shortname == "cs101"
        await client.aclose()

    run(scenario())


def test_find_course_without_mapping_has_no_internal_id():
    adapter, _, client = make_adapter(lambda request: httpx.Response(200, json=course_payload()))

    async def scenario():
        dto = await adapter.find_course("cs101")
        assert dto.internal_id is None
        assert dto.moodle_id == 42
        await client.aclose()

    run(scenario())


def test_find_course_returns_none_when_moodle_has_no_match():
    adapter, _, client = make_adapter(
        lambda request: httpx.Response(200, json={"courses": [], "warnings": []})
    )

    async def scenario():
        assert await adapter.find_course("tidak-ada") is None
        await client.aclose()

    run(scenario())


def test_find_course_queries_moodle_by_shortname():
    seen = {}

    def handler(request):
        seen["body"] = request.content.decode()
        return httpx.Response(200, json={"courses": [], "warnings": []})

    adapter, _, client = make_adapter(handler)

    async def scenario():
        await adapter.find_course("  cs101  ")
        assert "wsfunction=core_course_get_courses_by_field" in seen["body"]
        assert "field=shortname" in seen["body"]
        assert "value=cs101" in seen["body"]
        await client.aclose()

    run(scenario())


def test_find_course_rejects_blank_shortname():
    adapter, _, client = make_adapter(lambda request: httpx.Response(200, json={}))

    async def scenario():
        with pytest.raises(ValueError):
            await adapter.find_course("   ")
        await client.aclose()

    run(scenario())


def test_find_course_normalizes_moodle_errors():
    def handler(request):
        return httpx.Response(
            200,
            json={"exception": "moodle_exception", "errorcode": "invalidtoken", "message": "Invalid token"},
        )

    adapter, _, client = make_adapter(handler)

    async def scenario():
        with pytest.raises(MoodleOperationFailedError):
            await adapter.find_course("cs101")
        await client.aclose()

    run(scenario())