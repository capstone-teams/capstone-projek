import asyncio
from urllib.parse import parse_qs

import httpx
import pytest

from src.services.moodle_adapter import MoodleAdapter
from src.services.moodle_adapter_exceptions import (
    MoodleEntityNotFoundError,
    MoodleOperationFailedError,
)
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


def update_handler(update_response, calls):
    def handler(request):
        form = parse_qs(request.content.decode())
        function = form["wsfunction"][0]
        calls.append((function, form))
        if function == "core_course_update_courses":
            return httpx.Response(200, json=update_response)
        return httpx.Response(200, json=[{"id": 42, "fullname": "Judul Baru", "shortname": "cs101", "visible": 1}])

    return handler


def test_update_course_sends_only_changed_fields_and_returns_fresh_course():
    calls = []
    adapter, repo, client = make_adapter(update_handler({"warnings": []}, calls))

    async def scenario():
        await repo.save(MoodleMapping("course", "course_1", 42))
        dto = await adapter.update_course("course_1", fullname="Judul Baru")
        function, form = calls[0]
        assert function == "core_course_update_courses"
        assert form["courses[0][id]"] == ["42"]
        assert form["courses[0][fullname]"] == ["Judul Baru"]
        assert "courses[0][shortname]" not in form
        assert "courses[0][visible]" not in form
        assert dto.fullname == "Judul Baru"
        assert dto.internal_id == "course_1"
        await client.aclose()

    run(scenario())


def test_update_course_can_hide_a_course():
    calls = []
    adapter, repo, client = make_adapter(update_handler({"warnings": []}, calls))

    async def scenario():
        await repo.save(MoodleMapping("course", "course_1", 42))
        await adapter.update_course("course_1", visible=False)
        assert calls[0][1]["courses[0][visible]"] == ["0"]
        await client.aclose()

    run(scenario())


def test_update_course_requires_at_least_one_change():
    adapter, repo, client = make_adapter(update_handler({"warnings": []}, []))

    async def scenario():
        await repo.save(MoodleMapping("course", "course_1", 42))
        with pytest.raises(ValueError):
            await adapter.update_course("course_1")
        await client.aclose()

    run(scenario())


def test_update_course_without_mapping_raises_not_found():
    calls = []
    adapter, _, client = make_adapter(update_handler({"warnings": []}, calls))

    async def scenario():
        with pytest.raises(MoodleEntityNotFoundError):
            await adapter.update_course("belum-ada", fullname="X")
        assert calls == []
        await client.aclose()

    run(scenario())


def test_update_course_treats_moodle_warnings_as_failure():
    warning = {
        "warnings": [
            {
                "item": "course",
                "itemid": 42,
                "warningcode": "shortnametaken",
                "message": "Shortname sudah dipakai",
            }
        ]
    }
    adapter, repo, client = make_adapter(update_handler(warning, []))

    async def scenario():
        await repo.save(MoodleMapping("course", "course_1", 42))
        with pytest.raises(MoodleOperationFailedError) as info:
            await adapter.update_course("course_1", shortname="dipakai")
        assert "Shortname sudah dipakai" in str(info.value)
        await client.aclose()

    run(scenario())


def test_update_course_normalizes_moodle_errors():
    def handler(request):
        return httpx.Response(
            200,
            json={"exception": "moodle_exception", "errorcode": "invalidtoken", "message": "Invalid token"},
        )

    adapter, repo, client = make_adapter(handler)

    async def scenario():
        await repo.save(MoodleMapping("course", "course_1", 42))
        with pytest.raises(MoodleOperationFailedError):
            await adapter.update_course("course_1", fullname="X")
        await client.aclose()

    run(scenario())