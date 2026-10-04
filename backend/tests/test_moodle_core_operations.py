import asyncio
from urllib.parse import parse_qs

import httpx
import pytest

from src.services.moodle_adapter import MoodleAdapter
from src.services.moodle_adapter_exceptions import (
    MoodleCapabilityUnavailableError,
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


def contents_handler(sections):
    return lambda request: httpx.Response(200, json=sections)


def section_payload(section_id, number, name=""):
    return {"id": section_id, "section": number, "name": name or f"Section {number}", "modules": []}


UNSORTED_SECTIONS = [
    section_payload(10, 2),
    section_payload(8, 0, "General"),
    section_payload(9, 1),
]


def test_weekly_sections_skip_general_section_and_follow_week_order():
    adapter, repo, client = make_adapter(contents_handler(UNSORTED_SECTIONS))

    async def scenario():
        await repo.save(MoodleMapping("course", "course_1", 42))
        sections = await adapter.get_weekly_sections("course_1")
        assert [section.moodle_section_id for section in sections] == [9, 10]
        assert [section.section_number for section in sections] == [1, 2]
        await client.aclose()

    run(scenario())


def test_resolve_week_section_matches_by_week_number_and_saves_mapping():
    adapter, repo, client = make_adapter(contents_handler(UNSORTED_SECTIONS))

    async def scenario():
        await repo.save(MoodleMapping("course", "course_1", 42))
        section = await adapter.resolve_week_section("course_1", "week_a", 2)
        assert section.moodle_section_id == 10
        assert await repo.get_moodle_id("course_plan_week", "week_a") == 10
        await client.aclose()

    run(scenario())


def test_resolve_week_section_is_idempotent_on_retry():
    adapter, repo, client = make_adapter(contents_handler(UNSORTED_SECTIONS))

    async def scenario():
        await repo.save(MoodleMapping("course", "course_1", 42))
        first = await adapter.resolve_week_section("course_1", "week_a", 1)
        second = await adapter.resolve_week_section("course_1", "week_a", 1)
        assert first == second
        assert await repo.get_internal_id("course_plan_week", 9) == "week_a"
        await client.aclose()

    run(scenario())


def test_resolve_week_section_keeps_existing_link_when_section_moves():
    adapter, repo, client = make_adapter(contents_handler(UNSORTED_SECTIONS))

    async def scenario():
        await repo.save(MoodleMapping("course", "course_1", 42))
        await repo.save(MoodleMapping("course_plan_week", "week_a", 10))
        section = await adapter.resolve_week_section("course_1", "week_a", 1)
        assert section.moodle_section_id == 10
        await client.aclose()

    run(scenario())


def test_resolve_week_section_fails_when_week_has_no_section():
    adapter, repo, client = make_adapter(contents_handler(UNSORTED_SECTIONS))

    async def scenario():
        await repo.save(MoodleMapping("course", "course_1", 42))
        with pytest.raises(MoodleEntityNotFoundError):
            await adapter.resolve_week_section("course_1", "week_x", 5)
        assert await repo.exists("course_plan_week", "week_x") is False
        await client.aclose()

    run(scenario())


def test_resolve_week_section_fails_when_linked_section_no_longer_exists():
    adapter, repo, client = make_adapter(contents_handler(UNSORTED_SECTIONS))

    async def scenario():
        await repo.save(MoodleMapping("course", "course_1", 42))
        await repo.save(MoodleMapping("course_plan_week", "week_a", 777))
        with pytest.raises(MoodleEntityNotFoundError):
            await adapter.resolve_week_section("course_1", "week_a", 1)
        await client.aclose()

    run(scenario())


def test_resolve_week_section_rejects_week_number_below_one():
    adapter, repo, client = make_adapter(contents_handler(UNSORTED_SECTIONS))

    async def scenario():
        await repo.save(MoodleMapping("course", "course_1", 42))
        with pytest.raises(ValueError):
            await adapter.resolve_week_section("course_1", "week_a", 0)
        await client.aclose()

    run(scenario())


def test_weekly_sections_require_a_mapped_course():
    adapter, _, client = make_adapter(contents_handler(UNSORTED_SECTIONS))

    async def scenario():
        with pytest.raises(MoodleEntityNotFoundError):
            await adapter.get_weekly_sections("belum-ada")
        await client.aclose()

    run(scenario())
    
    
def test_create_section_reports_capability_as_unavailable():
    calls = []
    adapter, _, client = make_adapter(update_handler({"warnings": []}, calls))

    async def scenario():
        with pytest.raises(MoodleCapabilityUnavailableError) as info:
            await adapter.create_section("course_1", "week_a", 1, "Minggu 1")
        assert info.value.operation == "create_section"
        assert calls == []
        await client.aclose()

    run(scenario())


def test_update_section_reports_capability_as_unavailable():
    calls = []
    adapter, _, client = make_adapter(update_handler({"warnings": []}, calls))

    async def scenario():
        with pytest.raises(MoodleCapabilityUnavailableError) as info:
            await adapter.update_section("course_1", "week_a", name="Pengantar")
        assert info.value.operation == "update_section"
        assert calls == []
        await client.aclose()

    run(scenario())