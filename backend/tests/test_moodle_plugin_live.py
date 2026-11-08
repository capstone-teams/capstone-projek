import os
import time
import uuid

import pytest
import pytest_asyncio

from src.config.settings import settings
from src.services.moodle_client import MoodleClient
from src.services.moodle_exceptions import MoodleAPIError

pytestmark = pytest.mark.skipif(
    os.getenv("MOODLE_LIVE_TESTS") != "1",
    reason="Set MOODLE_LIVE_TESTS=1 untuk menjalankan test terhadap Moodle yang sedang menyala",
)


@pytest_asyncio.fixture
async def client():
    moodle = MoodleClient(
        settings.MOODLE_BASE_URL, settings.MOODLE_WEB_SERVICE_TOKEN, timeout=60.0
    )
    try:
        yield moodle
    finally:
        await moodle.aclose()


async def create_course(client):
    suffix = uuid.uuid4().hex[:8]
    courses = await client.call(
        "core_course_create_courses",
        {"courses": [{"fullname": "Plugin Test", "shortname": f"pg-{suffix}", "categoryid": 1}]},
    )
    return courses[0]["id"]


def module_ids(contents):
    return [module["id"] for section in contents for module in section.get("modules", [])]


@pytest.mark.asyncio
async def test_page_is_created_through_the_capstone_bridge_plugin(client):
    course_id = await create_course(client)

    created = await client.call(
        "local_capstonebridge_create_page",
        {
            "courseid": course_id,
            "section": 0,
            "name": "Pengantar",
            "content": "<p>Isi materi</p>",
        },
    )

    contents = await client.call("core_course_get_contents", {"courseid": course_id})
    assert created["created"] == 1
    assert created["cmid"] in module_ids(contents)


@pytest.mark.asyncio
async def test_page_with_the_same_idnumber_is_not_created_twice(client):
    course_id = await create_course(client)
    arguments = {
        "courseid": course_id,
        "section": 1,
        "name": "Pengantar",
        "content": "<p>Isi materi</p>",
        "idnumber": "content_week_1",
    }

    first = await client.call("local_capstonebridge_create_page", arguments)
    second = await client.call("local_capstonebridge_create_page", arguments)

    contents = await client.call("core_course_get_contents", {"courseid": course_id})
    assert first["created"] == 1
    assert second["created"] == 0
    assert second["cmid"] == first["cmid"]
    assert module_ids(contents).count(first["cmid"]) == 1


@pytest.mark.asyncio
async def test_missing_section_is_created_by_moodle(client):
    course_id = await create_course(client)

    created = await client.call(
        "local_capstonebridge_create_page",
        {
            "courseid": course_id,
            "section": 5,
            "name": "Minggu 5",
            "content": "<p>Isi materi</p>",
        },
    )

    contents = await client.call("core_course_get_contents", {"courseid": course_id})
    section_five = next(section for section in contents if section["section"] == 5)
    assert created["cmid"] in [module["id"] for module in section_five["modules"]]


@pytest.mark.asyncio
async def test_assignment_is_created_through_the_capstone_bridge_plugin(client):
    course_id = await create_course(client)
    due_date = int(time.time()) + 7 * 24 * 3600

    created = await client.call(
        "local_capstonebridge_create_assign",
        {
            "courseid": course_id,
            "section": 1,
            "name": "Tugas 1",
            "intro": "<p>Kerjakan soal berikut</p>",
            "duedate": due_date,
            "idnumber": "assignment_week_1",
        },
    )
    repeated = await client.call(
        "local_capstonebridge_create_assign",
        {
            "courseid": course_id,
            "section": 1,
            "name": "Tugas 1",
            "idnumber": "assignment_week_1",
        },
    )

    contents = await client.call("core_course_get_contents", {"courseid": course_id})
    modules = [module for section in contents for module in section.get("modules", [])]
    assignment = next(module for module in modules if module["id"] == created["cmid"])
    assert created["created"] == 1
    assert repeated["created"] == 0
    assert repeated["cmid"] == created["cmid"]
    assert assignment["modname"] == "assign"
    assert [module["id"] for module in modules].count(created["cmid"]) == 1
    
    
def find_module(contents, cmid):
    for section in contents:
        for module in section.get("modules", []):
            if module["id"] == cmid:
                return section["section"], module
    raise AssertionError(f"module {cmid} tidak ditemukan pada course")


@pytest.mark.asyncio
async def test_page_is_updated_in_place_and_can_move_section(client):
    course_id = await create_course(client)
    created = await client.call(
        "local_capstonebridge_create_page",
        {
            "courseid": course_id,
            "section": 1,
            "name": "Pengantar",
            "content": "<p>Versi 1</p>",
            "idnumber": "page_week_1",
        },
    )

    updated = await client.call(
        "local_capstonebridge_update_page",
        {
            "courseid": course_id,
            "cmid": created["cmid"],
            "name": "Pengantar (revisi)",
            "content": "<p>Versi 2</p>",
            "section": 2,
        },
    )

    contents = await client.call("core_course_get_contents", {"courseid": course_id})
    pages = await client.call("mod_page_get_pages_by_courses", {"courseids": [course_id]})
    page = next(item for item in pages["pages"] if item["coursemodule"] == created["cmid"])
    section_number, module = find_module(contents, created["cmid"])
    assert updated == {
        "cmid": created["cmid"],
        "instanceid": created["instanceid"],
        "section": 2,
        "updated": 1,
    }
    assert section_number == 2
    assert module["name"] == "Pengantar (revisi)"
    assert page["content"] == "<p>Versi 2</p>"
    assert module_ids(contents).count(created["cmid"]) == 1


@pytest.mark.asyncio
async def test_page_update_keeps_section_when_not_given(client):
    course_id = await create_course(client)
    created = await client.call(
        "local_capstonebridge_create_page",
        {"courseid": course_id, "section": 3, "name": "Minggu 3", "content": "<p>A</p>"},
    )

    updated = await client.call(
        "local_capstonebridge_update_page",
        {"courseid": course_id, "cmid": created["cmid"], "name": "Minggu 3", "content": "<p>B</p>"},
    )

    assert updated["section"] == 3


@pytest.mark.asyncio
async def test_page_update_rejects_a_module_from_another_course(client):
    course_id = await create_course(client)
    other_course_id = await create_course(client)
    created = await client.call(
        "local_capstonebridge_create_page",
        {"courseid": course_id, "section": 1, "name": "Pengantar", "content": "<p>A</p>"},
    )

    with pytest.raises(MoodleAPIError):
        await client.call(
            "local_capstonebridge_update_page",
            {"courseid": other_course_id, "cmid": created["cmid"], "name": "X", "content": "<p>X</p>"},
        )


@pytest.mark.asyncio
async def test_url_resource_is_created_once_in_the_requested_section(client):
    course_id = await create_course(client)
    arguments = {
        "courseid": course_id,
        "section": 2,
        "name": "Dokumentasi PostgreSQL",
        "externalurl": "https://www.postgresql.org/docs/",
        "intro": "<p>Bacaan pendukung minggu 2</p>",
        "idnumber": "resource_week_2_1",
    }

    first = await client.call("local_capstonebridge_create_url", arguments)
    second = await client.call("local_capstonebridge_create_url", arguments)

    contents = await client.call("core_course_get_contents", {"courseid": course_id})
    urls = await client.call("mod_url_get_urls_by_courses", {"courseids": [course_id]})
    url = next(item for item in urls["urls"] if item["coursemodule"] == first["cmid"])
    section_number, module = find_module(contents, first["cmid"])
    assert first["created"] == 1
    assert second == {"cmid": first["cmid"], "instanceid": first["instanceid"], "created": 0}
    assert section_number == 2
    assert module["modname"] == "url"
    assert url["externalurl"] == "https://www.postgresql.org/docs/"
    assert module_ids(contents).count(first["cmid"]) == 1


@pytest.mark.asyncio
async def test_url_resource_is_updated_in_place(client):
    course_id = await create_course(client)
    created = await client.call(
        "local_capstonebridge_create_url",
        {
            "courseid": course_id,
            "section": 1,
            "name": "Referensi",
            "externalurl": "https://example.com/lama",
            "idnumber": "resource_week_1_1",
        },
    )

    updated = await client.call(
        "local_capstonebridge_update_url",
        {
            "courseid": course_id,
            "cmid": created["cmid"],
            "name": "Referensi baru",
            "externalurl": "https://example.com/baru",
            "section": 4,
        },
    )

    contents = await client.call("core_course_get_contents", {"courseid": course_id})
    urls = await client.call("mod_url_get_urls_by_courses", {"courseids": [course_id]})
    url = next(item for item in urls["urls"] if item["coursemodule"] == created["cmid"])
    section_number, module = find_module(contents, created["cmid"])
    assert updated["updated"] == 1
    assert section_number == 4
    assert module["name"] == "Referensi baru"
    assert url["externalurl"] == "https://example.com/baru"
    assert module_ids(contents).count(created["cmid"]) == 1


@pytest.mark.asyncio
async def test_url_resource_rejects_an_invalid_address(client):
    course_id = await create_course(client)

    with pytest.raises(MoodleAPIError):
        await client.call(
            "local_capstonebridge_create_url",
            {"courseid": course_id, "section": 1, "name": "Rusak", "externalurl": "bukan url"},
        )


@pytest.mark.asyncio
async def test_assignment_is_updated_without_disabling_online_text_submission(client):
    course_id = await create_course(client)
    created = await client.call(
        "local_capstonebridge_create_assign",
        {
            "courseid": course_id,
            "section": 1,
            "name": "Tugas 1",
            "intro": "<p>Versi 1</p>",
            "idnumber": "assignment_week_1_update",
        },
    )
    new_due_date = int(time.time()) + 14 * 24 * 3600

    updated = await client.call(
        "local_capstonebridge_update_assign",
        {
            "courseid": course_id,
            "cmid": created["cmid"],
            "name": "Tugas 1 (revisi)",
            "intro": "<p>Versi 2</p>",
            "duedate": new_due_date,
        },
    )

    result = await client.call(
        "mod_assign_get_assignments",
        {"courseids": [course_id], "includenotenrolledcourses": 1},
    )
    assignment = next(
        item
        for course in result["courses"]
        for item in course["assignments"]
        if item["cmid"] == created["cmid"]
    )
    configs = {
        (config["plugin"], config["subtype"], config["name"]): config["value"]
        for config in assignment["configs"]
    }
    assert updated["updated"] == 1
    assert updated["section"] == 1
    assert assignment["name"] == "Tugas 1 (revisi)"
    assert assignment["duedate"] == new_due_date
    assert "Versi 2" in assignment["intro"]
    assert configs[("onlinetext", "assignsubmission", "enabled")] == "1"


async def get_assignment(client, course_id, cmid):
    result = await client.call(
        "mod_assign_get_assignments",
        {"courseids": [course_id], "includenotenrolledcourses": 1},
    )
    return next(
        item
        for course in result["courses"]
        for item in course["assignments"]
        if item["cmid"] == cmid
    )


def submission_configs(assignment):
    """Config plugin submission; plugin nonaktif tidak dikembalikan Moodle sehingga dianggap "0"."""
    configs = {
        (config["plugin"], config["name"]): config["value"]
        for config in assignment["configs"]
        if config["subtype"] == "assignsubmission"
    }
    for plugin in ("onlinetext", "file"):
        configs.setdefault((plugin, "enabled"), "0")
    return configs


@pytest.mark.asyncio
async def test_assignment_is_created_with_grade_and_submission_settings(client):
    course_id = await create_course(client)

    created = await client.call(
        "local_capstonebridge_create_assign",
        {
            "courseid": course_id,
            "section": 2,
            "name": "Tugas ERD",
            "intro": "<p>Unggah ERD</p>",
            "grade": 80,
            "onlinetext": 0,
            "filesubmission": 1,
            "maxfiles": 3,
        },
    )

    assignment = await get_assignment(client, course_id, created["cmid"])
    configs = submission_configs(assignment)
    assert assignment["grade"] == 80
    assert configs[("onlinetext", "enabled")] == "0"
    assert configs[("file", "enabled")] == "1"
    assert configs[("file", "maxfilesubmissions")] == "3"


@pytest.mark.asyncio
async def test_assignment_update_changes_settings_and_keeps_what_is_not_given(client):
    course_id = await create_course(client)
    created = await client.call(
        "local_capstonebridge_create_assign",
        {
            "courseid": course_id,
            "section": 1,
            "name": "Tugas 1",
            "grade": 90,
            "onlinetext": 1,
            "filesubmission": 1,
            "maxfiles": 4,
        },
    )

    await client.call(
        "local_capstonebridge_update_assign",
        {"courseid": course_id, "cmid": created["cmid"], "name": "Tugas 1 (revisi)"},
    )
    kept = await get_assignment(client, course_id, created["cmid"])

    await client.call(
        "local_capstonebridge_update_assign",
        {
            "courseid": course_id,
            "cmid": created["cmid"],
            "name": "Tugas 1 (revisi 2)",
            "grade": 50,
            "onlinetext": 0,
            "maxfiles": 2,
        },
    )
    changed = await get_assignment(client, course_id, created["cmid"])

    assert kept["grade"] == 90
    assert submission_configs(kept)[("onlinetext", "enabled")] == "1"
    assert submission_configs(kept)[("file", "enabled")] == "1"
    assert submission_configs(kept)[("file", "maxfilesubmissions")] == "4"
    assert changed["grade"] == 50
    assert submission_configs(changed)[("onlinetext", "enabled")] == "0"
    assert submission_configs(changed)[("file", "enabled")] == "1"
    assert submission_configs(changed)[("file", "maxfilesubmissions")] == "2"


@pytest.mark.asyncio
async def test_assignment_rejects_an_invalid_grade(client):
    course_id = await create_course(client)

    with pytest.raises(MoodleAPIError):
        await client.call(
            "local_capstonebridge_create_assign",
            {"courseid": course_id, "section": 1, "name": "Tugas", "grade": 0},
        )
        

def quiz_question(text, correct_flags):
    return {
        "text": f"<p>{text}</p>",
        "answers": [{"text": f"Opsi {i}", "correct": flag} for i, flag in enumerate(correct_flags)],
    }


@pytest.mark.asyncio
async def test_quiz_rejects_a_question_without_exactly_one_correct_answer(client):
    course_id = await create_course(client)

    with pytest.raises(MoodleAPIError):
        await client.call(
            "local_capstonebridge_create_quiz",
            {
                "courseid": course_id,
                "section": 1,
                "name": "Kuis",
                "idnumber": "quiz_two_correct",
                "questions": [quiz_question("Soal", [1, 1, 0])],
            },
        )

    contents = await client.call("core_course_get_contents", {"courseid": course_id})
    assert all(module["modname"] != "quiz" for module in (m for s in contents for m in s.get("modules", [])))


@pytest.mark.asyncio
async def test_quiz_requires_an_idnumber(client):
    course_id = await create_course(client)

    with pytest.raises(MoodleAPIError):
        await client.call(
            "local_capstonebridge_create_quiz",
            {
                "courseid": course_id,
                "section": 1,
                "name": "Kuis",
                "idnumber": "",
                "questions": [quiz_question("Soal", [1, 0])],
            },
        )