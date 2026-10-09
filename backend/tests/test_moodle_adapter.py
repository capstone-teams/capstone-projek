import asyncio

import httpx
import pytest

from src.services.moodle_adapter import MoodleAdapter
from src.services.moodle_adapter_exceptions import (
    MoodleEntityNotFoundError,
    MoodleOperationFailedError,
)
from src.services.moodle_client import MoodleClient
from src.services.moodle_mapping import (
    DuplicateMappingError,
    InMemoryMoodleMappingRepository,
    MoodleMapping,
)

TOKEN = "test-token"
BASE_URL = "http://moodle.test"


def run(coro):
    return asyncio.run(coro)


def make_adapter(handler):
    client = MoodleClient(BASE_URL, TOKEN, transport=httpx.MockTransport(handler))
    repo = InMemoryMoodleMappingRepository()
    return MoodleAdapter(client, repo), repo, client


def test_create_course_calls_client_and_saves_mapping():
    def handler(request):
        return httpx.Response(200, json=[{"id": 42, "shortname": "cs101"}])

    adapter, repo, client = make_adapter(handler)

    async def scenario():
        dto = await adapter.create_course("internal-1", "Computer Science 101", "cs101")
        assert dto.internal_id == "internal-1"
        assert dto.moodle_id == 42
        assert await repo.get_moodle_id("course", "internal-1") == 42
        await client.aclose()

    run(scenario())


def test_create_course_is_idempotent_on_retry_no_duplicate():
    call_count = {"create": 0}

    def handler(request):
        body = request.content.decode()
        if "wsfunction=core_course_create_courses" in body:
            call_count["create"] += 1
            return httpx.Response(200, json=[{"id": 99, "shortname": "retry-test"}])
        return httpx.Response(200, json=[{"id": 99, "fullname": "Retry Test", "shortname": "retry-test"}])

    adapter, _, client = make_adapter(handler)

    async def scenario():
        first = await adapter.create_course("internal-retry", "Retry Test", "retry-test")
        second = await adapter.create_course("internal-retry", "Retry Test", "retry-test")
        assert first.moodle_id == second.moodle_id == 99
        assert call_count["create"] == 1
        await client.aclose()

    run(scenario())


def test_create_course_raises_operation_failed_on_empty_response():
    def handler(request):
        return httpx.Response(200, json=[])

    adapter, _, client = make_adapter(handler)

    async def scenario():
        with pytest.raises(MoodleOperationFailedError):
            await adapter.create_course("internal-x", "X", "x")
        await client.aclose()

    run(scenario())


def test_get_course_without_mapping_raises_not_found():
    adapter, _, client = make_adapter(lambda request: httpx.Response(200, json=[]))

    async def scenario():
        with pytest.raises(MoodleEntityNotFoundError):
            await adapter.get_course("never-created")
        await client.aclose()

    run(scenario())


def test_get_course_returns_dto_from_mapped_id():
    def handler(request):
        return httpx.Response(
            200, json=[{"id": 7, "fullname": "Existing Course", "shortname": "exist", "visible": 1}]
        )

    adapter, repo, client = make_adapter(handler)

    async def scenario():
        await repo.save(MoodleMapping(entity_type="course", internal_id="internal-7", moodle_id=7))
        dto = await adapter.get_course("internal-7")
        assert dto.moodle_id == 7
        assert dto.fullname == "Existing Course"
        assert dto.internal_id == "internal-7"
        await client.aclose()

    run(scenario())


def test_get_course_raises_not_found_when_moodle_returns_empty():
    def handler(request):
        return httpx.Response(200, json=[])

    adapter, repo, client = make_adapter(handler)

    async def scenario():
        await repo.save(MoodleMapping(entity_type="course", internal_id="ghost", moodle_id=404))
        with pytest.raises(MoodleEntityNotFoundError):
            await adapter.get_course("ghost")
        await client.aclose()

    run(scenario())


def test_get_course_contents_returns_section_dtos():
    def handler(request):
        return httpx.Response(
            200,
            json=[
                {"id": 1, "name": "General", "section": 0, "modules": [{"id": 10}]},
                {"id": 2, "name": "Week 1", "section": 1, "modules": []},
            ],
        )

    adapter, repo, client = make_adapter(handler)

    async def scenario():
        await repo.save(MoodleMapping(entity_type="course", internal_id="c1", moodle_id=5))
        sections = await adapter.get_course_contents("c1")
        assert len(sections) == 2
        assert sections[0].name == "General"
        assert sections[0].module_ids == [10]
        assert sections[1].section_number == 1
        await client.aclose()

    run(scenario())


def test_moodle_client_error_is_normalized_not_leaked():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "exception": "moodle_exception",
                "errorcode": "invalidtoken",
                "message": "Invalid token",
            },
        )

    adapter, _, client = make_adapter(handler)

    async def scenario():
        with pytest.raises(MoodleOperationFailedError) as info:
            await adapter.create_course("internal-err", "Err", "err")
        assert info.value.original_error is not None
        await client.aclose()

    run(scenario())


def test_mapping_repository_prevents_duplicate_relationship():
    repo = InMemoryMoodleMappingRepository()

    async def scenario():
        await repo.save(MoodleMapping(entity_type="course", internal_id="c1", moodle_id=1))
        with pytest.raises(DuplicateMappingError):
            await repo.save(MoodleMapping(entity_type="course", internal_id="c1", moodle_id=2))

    run(scenario())


def test_mapping_repository_save_same_value_twice_is_safe():
    repo = InMemoryMoodleMappingRepository()

    async def scenario():
        await repo.save(MoodleMapping(entity_type="course", internal_id="c1", moodle_id=1))
        await repo.save(MoodleMapping(entity_type="course", internal_id="c1", moodle_id=1))
        assert await repo.get_moodle_id("course", "c1") == 1

    run(scenario())


def test_mapping_repository_bidirectional_lookup():
    repo = InMemoryMoodleMappingRepository()

    async def scenario():
        await repo.save(MoodleMapping(entity_type="course", internal_id="c1", moodle_id=100))
        assert await repo.get_moodle_id("course", "c1") == 100
        assert await repo.get_internal_id("course", 100) == "c1"
        assert await repo.exists("course", "c1") is True
        assert await repo.exists("course", "unknown") is False

    run(scenario())


def test_mapping_repository_handles_entity_without_moodle_id_yet():
    repo = InMemoryMoodleMappingRepository()

    async def scenario():
        assert await repo.get_moodle_id("course", "not-yet-created") is None
        assert await repo.exists("course", "not-yet-created") is False

    run(scenario())
    
    
def test_get_course_sends_course_id_inside_options_parameter():
    seen = {}

    def handler(request):
        seen["body"] = request.content.decode()
        return httpx.Response(
            200, json=[{"id": 42, "fullname": "CS 101", "shortname": "cs101", "visible": 1}]
        )

    adapter, repo, client = make_adapter(handler)

    async def scenario():
        await repo.save(MoodleMapping("course", "internal-1", 42))
        await adapter.get_course("internal-1")
        assert "wsfunction=core_course_get_courses" in seen["body"]
        assert "options%5Bids%5D%5B0%5D=42" in seen["body"]
        await client.aclose()

    run(scenario())