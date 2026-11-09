"""Integration test BE-12.1 terhadap instance Moodle tim (opt-in).

Jalankan dengan ``MOODLE_LIVE_TESTS=1``. Pemeriksaan akses mahasiswa ikut
dijalankan bila ``MOODLE_STUDENT_USERNAME`` dan ``MOODLE_STUDENT_PASSWORD``
diisi (akun mahasiswa uji yang sudah ada di Moodle).
"""

import os
import uuid

import httpx
import pytest
import pytest_asyncio

from src.config.settings import settings
from src.services.moodle_client import MoodleClient
from src.services.moodle_mapping import InMemoryMoodleMappingRepository
from src.services.moodle_resource_service import (
    RESOURCE_ENTITY_TYPE,
    LearningResource,
    MoodleResourceService,
)

pytestmark = pytest.mark.skipif(
    os.getenv("MOODLE_LIVE_TESTS") != "1",
    reason="Set MOODLE_LIVE_TESTS=1 untuk menjalankan test terhadap Moodle yang sedang menyala",
)

STUDENT_USERNAME = os.getenv("MOODLE_STUDENT_USERNAME")
STUDENT_PASSWORD = os.getenv("MOODLE_STUDENT_PASSWORD")
STUDENT_ROLE_ID = int(os.getenv("MOODLE_STUDENT_ROLE_ID", "5"))  # role "student" bawaan Moodle


@pytest_asyncio.fixture
async def client():
    moodle = MoodleClient.from_settings(settings)
    try:
        yield moodle
    finally:
        await moodle.aclose()


async def create_course(client):
    suffix = uuid.uuid4().hex[:8]
    courses = await client.call(
        "core_course_create_courses",
        {"courses": [{"fullname": "Resource Test", "shortname": f"rs-{suffix}", "categoryid": 1}]},
    )
    return courses[0]["id"]


def modules_in(contents, cmid):
    return [
        (section["section"], module)
        for section in contents
        for module in section.get("modules", [])
        if module["id"] == cmid
    ]


def sample_resource():
    return LearningResource(
        id=f"res-{uuid.uuid4().hex[:12]}",
        title="Dokumentasi PostgreSQL",
        url="https://www.postgresql.org/docs/",
        description="Bacaan pendukung minggu 2",
    )


@pytest.mark.asyncio
async def test_resource_is_published_in_the_week_section_without_duplicates(client):
    course_id = await create_course(client)
    mappings = InMemoryMoodleMappingRepository()
    service = MoodleResourceService(client, mappings)
    item = sample_resource()

    first = await service.publish(course_id, 2, item)
    second = await service.publish(course_id, 2, item)

    contents = await client.call("core_course_get_contents", {"courseid": course_id})
    found = modules_in(contents, first.cmid)
    assert first.created is True
    assert second.created is False
    assert second.cmid == first.cmid
    assert len(found) == 1
    section_number, module = found[0]
    assert section_number == 2
    assert module["modname"] == "url"
    assert module["name"] == "Dokumentasi PostgreSQL"
    assert await mappings.get_moodle_id(RESOURCE_ENTITY_TYPE, item.id) == first.cmid


@pytest.mark.asyncio
async def test_resource_update_changes_the_same_activity(client):
    course_id = await create_course(client)
    service = MoodleResourceService(client, InMemoryMoodleMappingRepository())
    item = sample_resource()
    first = await service.publish(course_id, 2, item)

    changed = LearningResource(
        id=item.id,
        title="Dokumentasi PostgreSQL 17",
        url="https://www.postgresql.org/docs/17/",
    )
    second = await service.publish(course_id, 3, changed)

    contents = await client.call("core_course_get_contents", {"courseid": course_id})
    urls = await client.call("mod_url_get_urls_by_courses", {"courseids": [course_id]})
    url = next(entry for entry in urls["urls"] if entry["coursemodule"] == first.cmid)
    found = modules_in(contents, first.cmid)
    assert second.cmid == first.cmid
    assert len(found) == 1
    assert found[0][0] == 3
    assert found[0][1]["name"] == "Dokumentasi PostgreSQL 17"
    assert url["externalurl"] == "https://www.postgresql.org/docs/17/"


@pytest.mark.skipif(
    not (STUDENT_USERNAME and STUDENT_PASSWORD),
    reason="Isi MOODLE_STUDENT_USERNAME dan MOODLE_STUDENT_PASSWORD untuk menguji akses mahasiswa",
)
@pytest.mark.asyncio
async def test_student_can_open_the_published_resource(client):
    course_id = await create_course(client)
    users = await client.call(
        "core_user_get_users_by_field", {"field": "username", "values": [STUDENT_USERNAME]}
    )
    assert users, "akun mahasiswa uji tidak ditemukan di Moodle"
    await client.call(
        "enrol_manual_enrol_users",
        {"enrolments": [{"roleid": STUDENT_ROLE_ID, "userid": users[0]["id"], "courseid": course_id}]},
    )
    result = await MoodleResourceService(client, InMemoryMoodleMappingRepository()).publish(
        course_id, 2, sample_resource()
    )

    async with httpx.AsyncClient(timeout=settings.moodle_timeout_seconds) as http:
        response = await http.post(
            f"{settings.MOODLE_BASE_URL.rstrip('/')}/login/token.php",
            data={
                "username": STUDENT_USERNAME,
                "password": STUDENT_PASSWORD,
                "service": "moodle_mobile_app",
            },
        )
    student_token = response.json().get("token")
    assert student_token, "token mahasiswa tidak didapat (cek service Mobile app aktif)"

    async with MoodleClient(
        settings.MOODLE_BASE_URL, student_token, timeout=settings.moodle_timeout_seconds
    ) as student:
        contents = await student.call("core_course_get_contents", {"courseid": course_id})

    found = modules_in(contents, result.cmid)
    assert len(found) == 1
    section_number, module = found[0]
    assert section_number == 2
    assert module["uservisible"] is True
    assert any(
        entry.get("fileurl") == "https://www.postgresql.org/docs/" for entry in module.get("contents", [])
    )