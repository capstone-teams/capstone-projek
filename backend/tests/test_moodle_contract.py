import asyncio
import inspect
from urllib.parse import parse_qs

import httpx
import pytest

from src.services.moodle_adapter import MoodleAdapter
from src.services.moodle_adapter_exceptions import (
    MoodleEntityNotFoundError,
    MoodleValidationFailedError,
)
from src.services.moodle_client import MoodleClient
from src.services.moodle_integration_interface import IMoodleIntegration
from src.services.moodle_mapping import InMemoryMoodleMappingRepository
from src.services.moodle_mock import MockMoodleIntegration
from src.services.moodle_tracked_integration import TrackedMoodleIntegration

TOKEN = "test-token"
BASE_URL = "http://moodle.test"


def run(coro):
    return asyncio.run(coro)


class FakeMoodleServer:
    def __init__(self):
        self.courses = {}
        self.next_id = 1

    def handler(self, request):
        form = {key: values[0] for key, values in parse_qs(request.content.decode()).items()}
        function = form["wsfunction"]
        return getattr(self, function)(form)

    def error(self, code):
        return httpx.Response(
            200, json={"exception": "moodle_exception", "errorcode": code, "message": code}
        )

    def core_course_create_courses(self, form):
        shortname = form["courses[0][shortname]"]
        if any(course["shortname"] == shortname for course in self.courses.values()):
            return self.error("shortnametaken")
        course = {
            "id": self.next_id,
            "fullname": form["courses[0][fullname]"],
            "shortname": shortname,
            "visible": 1,
        }
        self.courses[course["id"]] = course
        self.next_id += 1
        return httpx.Response(200, json=[{"id": course["id"], "shortname": shortname}])

    def core_course_get_courses(self, form):
        course = self.courses.get(int(form["options[ids][0]"]))
        return httpx.Response(200, json=[course] if course else [])

    def core_course_get_courses_by_field(self, form):
        matches = [c for c in self.courses.values() if c["shortname"] == form["value"]]
        return httpx.Response(200, json={"courses": matches, "warnings": []})

    def core_course_update_courses(self, form):
        course = self.courses[int(form["courses[0][id]"])]
        if "courses[0][fullname]" in form:
            course["fullname"] = form["courses[0][fullname]"]
        if "courses[0][visible]" in form:
            course["visible"] = int(form["courses[0][visible]"])
        return httpx.Response(200, json={"warnings": []})

    def core_course_get_contents(self, form):
        section = {"id": 1000 + int(form["courseid"]), "name": "General", "section": 0, "modules": []}
        return httpx.Response(200, json=[section])


def build_mock():
    return MockMoodleIntegration(), None


def build_adapter():
    server = FakeMoodleServer()
    client = MoodleClient(BASE_URL, TOKEN, transport=httpx.MockTransport(server.handler))
    return MoodleAdapter(client, InMemoryMoodleMappingRepository()), client


async def exercise_shared_contract(integration):
    created = await integration.create_course("course_1", "CS 101", "cs101")
    repeated = await integration.create_course("course_1", "CS 101", "cs101")
    assert repeated.moodle_id == created.moodle_id

    fetched = await integration.get_course("course_1")
    assert (fetched.internal_id, fetched.fullname, fetched.shortname) == ("course_1", "CS 101", "cs101")

    found = await integration.find_course("cs101")
    assert found.internal_id == "course_1"
    assert found.moodle_id == created.moodle_id
    assert await integration.find_course("tidak-ada") is None

    updated = await integration.update_course("course_1", fullname="Judul Baru", visible=False)
    assert updated.fullname == "Judul Baru"
    assert updated.visible is False

    contents = await integration.get_course_contents("course_1")
    assert [section.section_number for section in contents] == [0]
    assert await integration.get_weekly_sections("course_1") == []

    with pytest.raises(MoodleEntityNotFoundError):
        await integration.get_course("belum-ada")
    with pytest.raises(MoodleValidationFailedError):
        await integration.create_course("course_2", "Other", "cs101")
    with pytest.raises(ValueError):
        await integration.update_course("course_1")
    with pytest.raises(ValueError):
        await integration.find_course("  ")


def test_mock_and_real_adapter_follow_the_same_contract_for_course_operations():
    async def scenario():
        mock, _ = build_mock()
        await exercise_shared_contract(mock)

        adapter, client = build_adapter()
        await exercise_shared_contract(adapter)
        await client.aclose()

    run(scenario())


def public_methods(cls):
    return {
        name: list(inspect.signature(member).parameters)
        for name, member in inspect.getmembers(cls, inspect.isfunction)
        if not name.startswith("_")
    }


@pytest.mark.parametrize("implementation", [MoodleAdapter, MockMoodleIntegration, TrackedMoodleIntegration])
def test_every_implementation_exposes_the_full_integration_interface(implementation):
    expected = public_methods(IMoodleIntegration)
    actual = public_methods(implementation)

    for name, parameters in expected.items():
        assert name in actual, f"{implementation.__name__} tidak memiliki {name}"
        assert actual[name] == parameters, f"signature {name} berbeda pada {implementation.__name__}"