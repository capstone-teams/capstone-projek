"""Integration test BE-12.2 terhadap instance Moodle tim (opt-in).

Jalankan dengan ``MOODLE_LIVE_TESTS=1``. Butuh plugin ``local_capstonebridge``
minimal versi 0.4.0. Pemeriksaan akses mahasiswa ikut dijalankan bila
``MOODLE_STUDENT_USERNAME`` dan ``MOODLE_STUDENT_PASSWORD`` diisi (akun
mahasiswa uji yang sudah ada di Moodle).
"""

import os
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import pytest_asyncio

from src.config.settings import settings
from src.services.moodle_assignment_service import (
    ASSIGNMENT_ENTITY_TYPE,
    AssignmentContent,
    AssignmentSettings,
    MoodleAssignmentService,
    RubricItem,
)
from src.services.moodle_client import MoodleClient
from src.services.moodle_mapping import InMemoryMoodleMappingRepository

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
        {"courses": [{"fullname": "Assignment Test", "shortname": f"as-{suffix}", "categoryid": 1}]},
    )
    return courses[0]["id"]


def modules_in(contents, cmid):
    return [
        (section["section"], module)
        for section in contents
        for module in section.get("modules", [])
        if module["id"] == cmid
    ]


async def get_assignment(client, course_id, cmid, include_not_enrolled=True):
    params = {"courseids": [course_id]}
    if include_not_enrolled:
        params["includenotenrolledcourses"] = 1
    result = await client.call("mod_assign_get_assignments", params)
    return next(
        item for course in result["courses"] for item in course["assignments"] if item["cmid"] == cmid
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


def sample_assignment():
    return AssignmentContent(
        id=f"act-{uuid.uuid4().hex[:12]}",
        title="Normalisasi Studi Kasus Perpustakaan",
        instructions_markdown="Normalkan tabel peminjaman buku hingga **3NF**.",
        expected_outputs=("Dokumen PDF berisi tahapan normalisasi", "Diagram ERD akhir"),
        rubric=(
            RubricItem("Ketepatan 1NF-3NF", "Tahapan benar dan lengkap", 60),
            RubricItem("Kualitas ERD", "Relasi dan kardinalitas tepat", 40),
        ),
    )


@pytest.mark.asyncio
async def test_assignment_is_published_in_the_week_section_without_duplicates(client):
    course_id = await create_course(client)
    mappings = InMemoryMoodleMappingRepository()
    service = MoodleAssignmentService(client, mappings)
    item = sample_assignment()

    first = await service.publish(course_id, 3, item)
    second = await service.publish(course_id, 3, item)

    contents = await client.call("core_course_get_contents", {"courseid": course_id})
    assignment = await get_assignment(client, course_id, first.cmid)
    configs = submission_configs(assignment)
    found = modules_in(contents, first.cmid)
    assert first.created is True
    assert second.created is False
    assert second.cmid == first.cmid
    assert len(found) == 1
    section_number, module = found[0]
    assert section_number == 3
    assert module["modname"] == "assign"
    assert assignment["name"] == "Normalisasi Studi Kasus Perpustakaan"
    assert "Kriteria Penilaian" in assignment["intro"]
    assert "Ketepatan 1NF-3NF" in assignment["intro"]
    assert assignment["grade"] == 100
    assert assignment["duedate"] == 0
    assert configs[("onlinetext", "enabled")] == "1"
    assert configs[("file", "enabled")] == "1"
    assert configs[("file", "maxfilesubmissions")] == "5"
    assert await mappings.get_moodle_id(ASSIGNMENT_ENTITY_TYPE, item.id) == first.cmid


@pytest.mark.asyncio
async def test_assignment_update_changes_the_same_activity_and_its_settings(client):
    course_id = await create_course(client)
    service = MoodleAssignmentService(client, InMemoryMoodleMappingRepository())
    item = sample_assignment()
    first = await service.publish(course_id, 3, item)
    due = (datetime.now(timezone.utc) + timedelta(days=14)).replace(microsecond=0)

    changed = AssignmentContent(
        id=item.id,
        title="Normalisasi (revisi)",
        instructions_markdown="Normalkan tabel hingga **BCNF**.",
        rubric=(RubricItem("Ketepatan BCNF", "Tahapan benar", 100),),
    )
    second = await service.publish(
        course_id,
        4,
        changed,
        AssignmentSettings(submission_types=("file",), max_files=2, max_grade=80, due=due),
    )

    contents = await client.call("core_course_get_contents", {"courseid": course_id})
    assignment = await get_assignment(client, course_id, first.cmid)
    configs = submission_configs(assignment)
    found = modules_in(contents, first.cmid)
    assert second.cmid == first.cmid
    assert len(found) == 1
    assert found[0][0] == 4
    assert assignment["name"] == "Normalisasi (revisi)"
    assert "BCNF" in assignment["intro"]
    assert assignment["grade"] == 80
    assert assignment["duedate"] == int(due.timestamp())
    assert configs[("onlinetext", "enabled")] == "0"
    assert configs[("file", "enabled")] == "1"
    assert configs[("file", "maxfilesubmissions")] == "2"


@pytest.mark.skipif(
    not (STUDENT_USERNAME and STUDENT_PASSWORD),
    reason="Isi MOODLE_STUDENT_USERNAME dan MOODLE_STUDENT_PASSWORD untuk menguji akses mahasiswa",
)
@pytest.mark.asyncio
async def test_student_can_open_the_published_assignment(client):
    course_id = await create_course(client)
    users = await client.call(
        "core_user_get_users_by_field", {"field": "username", "values": [STUDENT_USERNAME]}
    )
    assert users, "akun mahasiswa uji tidak ditemukan di Moodle"
    await client.call(
        "enrol_manual_enrol_users",
        {"enrolments": [{"roleid": STUDENT_ROLE_ID, "userid": users[0]["id"], "courseid": course_id}]},
    )
    result = await MoodleAssignmentService(client, InMemoryMoodleMappingRepository()).publish(
        course_id, 3, sample_assignment()
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
        assignment = await get_assignment(student, course_id, result.cmid, include_not_enrolled=False)
        status = await student.call("mod_assign_get_submission_status", {"assignid": result.instance_id})

    found = modules_in(contents, result.cmid)
    assert len(found) == 1
    section_number, module = found[0]
    assert section_number == 3
    assert module["uservisible"] is True
    assert "Kriteria Penilaian" in assignment["intro"]
    assert status["lastattempt"]["canedit"] is True  # mahasiswa dapat menambahkan submission