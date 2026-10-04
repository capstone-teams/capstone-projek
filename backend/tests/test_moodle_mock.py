import asyncio

import pytest

from src.services.moodle_adapter_exceptions import (
    MoodleEntityNotFoundError,
    MoodleOperationFailedError,
)
from src.services.moodle_mock import MockMoodleIntegration


def run(coro):
    return asyncio.run(coro)


def test_create_course_is_idempotent_for_the_same_internal_id():
    mock = MockMoodleIntegration()

    async def scenario():
        first = await mock.create_course("course_1", "CS 101", "cs101")
        second = await mock.create_course("course_1", "CS 101", "cs101")
        assert first == second
        assert first.moodle_id == 1

    run(scenario())


def test_create_course_rejects_shortname_used_by_another_course():
    mock = MockMoodleIntegration()

    async def scenario():
        await mock.create_course("course_1", "CS 101", "cs101")
        with pytest.raises(MoodleOperationFailedError):
            await mock.create_course("course_2", "Other", "cs101")

    run(scenario())


def test_get_course_for_unknown_course_raises_not_found():
    mock = MockMoodleIntegration()

    async def scenario():
        with pytest.raises(MoodleEntityNotFoundError):
            await mock.get_course("belum-ada")

    run(scenario())


def test_update_course_changes_fields_and_validates_input():
    mock = MockMoodleIntegration()

    async def scenario():
        await mock.create_course("course_1", "CS 101", "cs101")
        await mock.create_course("course_2", "CS 102", "cs102")
        updated = await mock.update_course("course_1", fullname="Judul Baru", visible=False)
        assert updated.fullname == "Judul Baru"
        assert updated.visible is False
        with pytest.raises(ValueError):
            await mock.update_course("course_1")
        with pytest.raises(MoodleOperationFailedError):
            await mock.update_course("course_1", shortname="cs102")

    run(scenario())


def test_find_course_matches_by_shortname():
    mock = MockMoodleIntegration()

    async def scenario():
        created = await mock.create_course("course_1", "CS 101", "cs101")
        assert await mock.find_course(" cs101 ") == created
        assert await mock.find_course("tidak-ada") is None
        with pytest.raises(ValueError):
            await mock.find_course("  ")

    run(scenario())


def test_new_course_has_only_general_section():
    mock = MockMoodleIntegration()

    async def scenario():
        await mock.create_course("course_1", "CS 101", "cs101")
        contents = await mock.get_course_contents("course_1")
        assert [section.section_number for section in contents] == [0]
        assert await mock.get_weekly_sections("course_1") == []

    run(scenario())


def test_create_section_links_week_and_is_idempotent():
    mock = MockMoodleIntegration()

    async def scenario():
        await mock.create_course("course_1", "CS 101", "cs101")
        first = await mock.create_section("course_1", "week_a", 1, "Minggu 1")
        second = await mock.create_section("course_1", "week_a", 1, "Minggu 1")
        assert first == second
        assert await mock.resolve_week_section("course_1", "week_a", 1) == first
        assert len(await mock.get_weekly_sections("course_1")) == 1

    run(scenario())


def test_weekly_sections_follow_week_order_regardless_of_creation_order():
    mock = MockMoodleIntegration()

    async def scenario():
        await mock.create_course("course_1", "CS 101", "cs101")
        await mock.create_section("course_1", "week_b", 2, "Minggu 2")
        await mock.create_section("course_1", "week_a", 1, "Minggu 1")
        weekly = await mock.get_weekly_sections("course_1")
        assert [section.name for section in weekly] == ["Minggu 1", "Minggu 2"]

    run(scenario())


def test_resolve_week_section_without_section_raises_not_found():
    mock = MockMoodleIntegration()

    async def scenario():
        await mock.create_course("course_1", "CS 101", "cs101")
        with pytest.raises(MoodleEntityNotFoundError):
            await mock.resolve_week_section("course_1", "week_a", 3)

    run(scenario())


def test_update_section_renames_linked_section():
    mock = MockMoodleIntegration()

    async def scenario():
        await mock.create_course("course_1", "CS 101", "cs101")
        await mock.create_section("course_1", "week_a", 1, "Minggu 1")
        renamed = await mock.update_section("course_1", "week_a", name="Pengantar")
        assert renamed.name == "Pengantar"
        weekly = await mock.get_weekly_sections("course_1")
        assert [section.name for section in weekly] == ["Pengantar"]

    run(scenario())


def test_update_section_for_unlinked_week_raises_not_found():
    mock = MockMoodleIntegration()

    async def scenario():
        await mock.create_course("course_1", "CS 101", "cs101")
        with pytest.raises(MoodleEntityNotFoundError):
            await mock.update_section("course_1", "week_x", name="X")

    run(scenario())


def test_section_inputs_are_validated():
    mock = MockMoodleIntegration()

    async def scenario():
        await mock.create_course("course_1", "CS 101", "cs101")
        with pytest.raises(ValueError):
            await mock.create_section("course_1", "week_a", 0, "Minggu 0")
        with pytest.raises(ValueError):
            await mock.create_section("course_1", "week_a", 1, "  ")

    run(scenario())