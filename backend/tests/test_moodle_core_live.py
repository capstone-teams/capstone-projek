"""Integration test BE-04.4 (operasi inti Moodle) terhadap instance Moodle tim (opt-in).

Jalankan dengan ``MOODLE_LIVE_TESTS=1``. Membuat course uji baru di setiap test.
"""

import os
import uuid

import pytest
import pytest_asyncio

from src.config.settings import settings
from src.services.moodle_adapter import COURSE_ENTITY_TYPE, MoodleAdapter
from src.services.moodle_client import MoodleClient
from src.services.moodle_integration_service import MoodleIntegrationService
from src.services.moodle_mapping import InMemoryMoodleMappingRepository
from src.services.moodle_page_service import PAGE_ENTITY_TYPE, LearningMaterialPage, MoodlePageService

pytestmark = pytest.mark.skipif(
    os.getenv("MOODLE_LIVE_TESTS") != "1",
    reason="Set MOODLE_LIVE_TESTS=1 untuk menjalankan test terhadap Moodle yang sedang menyala",
)


@pytest_asyncio.fixture
async def client():
    moodle = MoodleClient.from_settings(settings)
    try:
        yield moodle
    finally:
        await moodle.aclose()


def unique_shortname(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


@pytest.mark.asyncio
async def test_course_is_created_once_and_can_be_read_by_id_shortname_and_list(client):
    mappings = InMemoryMoodleMappingRepository()
    adapter = MoodleAdapter(client, mappings)
    service = MoodleIntegrationService(client)
    shortname = unique_shortname("core")
    internal_id = f"course-{uuid.uuid4().hex[:8]}"

    first = await adapter.create_course(internal_id, "Core Operations Test", shortname)
    second = await adapter.create_course(internal_id, "Core Operations Test", shortname)

    by_id = await service.get_course(first.moodle_id)
    by_shortname = await service.get_course_by_shortname(shortname)
    listed = [course.moodle_course_id for course in await service.list_courses()]
    contents = await service.get_course_contents(first.moodle_id)
    assert second.moodle_id == first.moodle_id
    assert await mappings.get_moodle_id(COURSE_ENTITY_TYPE, internal_id) == first.moodle_id
    assert by_id.shortname == shortname
    assert by_shortname.moodle_course_id == first.moodle_id
    assert listed.count(first.moodle_id) == 1
    assert contents.sections[0].section_number == 0


@pytest.mark.asyncio
async def test_course_can_be_updated(client):
    service = MoodleIntegrationService(client)
    course = await service.create_course("Core Update Test", unique_shortname("upd"), 1)
    new_shortname = unique_shortname("upd2")

    updated = await service.update_course(
        course.moodle_course_id,
        fullname="Core Update Test (revisi)",
        shortname=new_shortname,
        summary="<p>Ringkasan baru</p>",
    )

    assert updated.moodle_course_id == course.moodle_course_id
    assert updated.fullname == "Core Update Test (revisi)"
    assert updated.shortname == new_shortname
    assert "Ringkasan baru" in updated.summary


@pytest.mark.asyncio
async def test_weekly_sections_keep_order_and_are_not_duplicated(client):
    service = MoodleIntegrationService(client)
    course = await service.create_course("Core Section Test", unique_shortname("sec"), 1)
    course_id = course.moodle_course_id

    first_run = [await service.save_section(course_id, f"Minggu {week}", week) for week in (1, 2, 3)]
    second_run = [await service.save_section(course_id, f"Minggu {week} - revisi", week) for week in (1, 2, 3)]

    sections = (await service.get_course_contents(course_id)).sections
    weekly = [(section.section_number, section.name) for section in sections if section.section_number > 0]
    assert [result.created for result in first_run] == [True, True, True]
    assert [result.created for result in second_run] == [False, False, False]
    assert [r.section.moodle_section_id for r in second_run] == [r.section.moodle_section_id for r in first_run]
    assert weekly == [(1, "Minggu 1 - revisi"), (2, "Minggu 2 - revisi"), (3, "Minggu 3 - revisi")]


@pytest.mark.asyncio
async def test_page_is_created_and_updated_without_duplicates(client):
    service = MoodleIntegrationService(client)
    course = await service.create_course("Core Page Test", unique_shortname("pg"), 1)
    course_id = course.moodle_course_id
    await service.save_section(course_id, "Minggu 1 - Pengantar", 1)
    mappings = InMemoryMoodleMappingRepository()
    pages = MoodlePageService(client, mappings)
    content_id = f"content-{uuid.uuid4().hex[:8]}"

    first = await pages.publish(
        course_id, 1, LearningMaterialPage.from_markdown(content_id, "Pengantar Basis Data", "## Apa itu basis data?\n\nVersi 1")
    )
    second = await pages.publish(
        course_id, 1, LearningMaterialPage.from_markdown(content_id, "Pengantar Basis Data", "## Apa itu basis data?\n\nVersi 2")
    )

    contents = await service.get_course_contents(course_id)
    found = [
        (section.section_number, module)
        for section in contents.sections
        for module in section.modules
        if module.moodle_module_id == first.cmid
    ]
    assert first.created is True
    assert second.created is False
    assert second.cmid == first.cmid
    assert await mappings.get_moodle_id(PAGE_ENTITY_TYPE, content_id) == first.cmid
    assert len(found) == 1
    section_number, module = found[0]
    assert section_number == 1
    assert module.modname == "page"
    assert "Versi 2" in (module.content or "")
    assert "<h3>Apa itu basis data?</h3>" in (module.content or "")