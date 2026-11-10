"""Integration test BE-12.3 terhadap instance Moodle tim (opt-in).

Jalankan dengan ``MOODLE_LIVE_TESTS=1``. Butuh plugin ``local_capstonebridge``
minimal versi 0.5.0. Pemeriksaan pengerjaan quiz oleh mahasiswa ikut dijalankan
bila ``MOODLE_STUDENT_USERNAME`` dan ``MOODLE_STUDENT_PASSWORD`` diisi (akun
mahasiswa uji yang sudah ada di Moodle).
"""

import os
import uuid

import httpx
import pytest
import pytest_asyncio

from src.config.settings import settings
from src.services.moodle_client import MoodleClient
from src.services.moodle_mapping import InMemoryMoodleMappingRepository
from src.services.moodle_quiz_service import (
    QUIZ_ENTITY_TYPE,
    MoodleQuizService,
    QuizContent,
    QuizOption,
    QuizQuestion,
    QuizSettings,
)

pytestmark = pytest.mark.skipif(
    os.getenv("MOODLE_LIVE_TESTS") != "1",
    reason="Set MOODLE_LIVE_TESTS=1 untuk menjalankan test terhadap Moodle yang sedang menyala",
)

STUDENT_USERNAME = os.getenv("MOODLE_STUDENT_USERNAME")
STUDENT_PASSWORD = os.getenv("MOODLE_STUDENT_PASSWORD")
STUDENT_ROLE_ID = int(os.getenv("MOODLE_STUDENT_ROLE_ID", "5"))  # role "student" bawaan Moodle

CORRECT_ANSWERS = ("Semua kolom bernilai atomik", "Bergantung penuh pada primary key", "Tidak ada dependensi transitif")


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
        {"courses": [{"fullname": "Quiz Test", "shortname": f"qz-{suffix}", "categoryid": 1}]},
    )
    return courses[0]["id"]


def modules_in(contents, cmid):
    return [
        (section["section"], module)
        for section in contents
        for module in section.get("modules", [])
        if module["id"] == cmid
    ]


async def get_quiz(client, course_id, cmid):
    result = await client.call("mod_quiz_get_quizzes_by_courses", {"courseids": [course_id]})
    return next(item for item in result["quizzes"] if item["coursemodule"] == cmid)


def sample_quiz():
    questions = tuple(
        QuizQuestion(
            question_text=text,
            options=(
                QuizOption("A", correct),
                QuizOption("B", "Boleh ada grup berulang"),
                QuizOption("C", "Semua kolom boleh kosong"),
            ),
            correct_option_key="A",
            explanation=f"Jawaban yang benar: {correct}.",
        )
        for text, correct in zip(
            (
                "Tabel disebut memenuhi 1NF jika...",
                "Syarat utama 2NF adalah setiap atribut non-key...",
                "Tabel memenuhi 3NF jika sudah 2NF dan...",
            ),
            CORRECT_ANSWERS,
        )
    )
    return QuizContent(
        id=f"quiz-{uuid.uuid4().hex[:12]}",
        title="Kuis Normalisasi",
        description="Kuis singkat pemahaman 1NF-3NF.",
        questions=questions,
        settings=QuizSettings(time_limit_minutes=15, max_attempts=2, shuffle_questions=True,
                              passing_score_percent=60),
    )


@pytest.mark.asyncio
async def test_quiz_with_questions_is_published_in_the_week_section_without_duplicates(client):
    course_id = await create_course(client)
    mappings = InMemoryMoodleMappingRepository()
    service = MoodleQuizService(client, mappings)
    item = sample_quiz()

    first = await service.publish(course_id, 4, item)
    second = await service.publish(course_id, 4, item)

    contents = await client.call("core_course_get_contents", {"courseid": course_id})
    quiz = await get_quiz(client, course_id, first.cmid)
    found = modules_in(contents, first.cmid)
    assert first.created is True
    assert second.created is False
    assert second.cmid == first.cmid
    assert first.question_count == second.question_count == 3
    assert len(found) == 1
    section_number, module = found[0]
    assert section_number == 4
    assert module["modname"] == "quiz"
    assert quiz["name"] == "Kuis Normalisasi"
    assert quiz["timelimit"] == 15 * 60
    assert quiz["attempts"] == 2
    assert quiz["sumgrades"] == 3
    assert quiz["hasquestions"] == 1
    assert await mappings.get_moodle_id(QUIZ_ENTITY_TYPE, item.id) == first.cmid


@pytest.mark.asyncio
async def test_quiz_update_replaces_questions_and_moves_the_same_activity(client):
    course_id = await create_course(client)
    service = MoodleQuizService(client, InMemoryMoodleMappingRepository())
    item = sample_quiz()
    first = await service.publish(course_id, 4, item)

    changed = QuizContent(
        id=item.id,
        title="Kuis Normalisasi (revisi)",
        description=item.description,
        questions=item.questions + item.questions[:1],
        settings=QuizSettings(),
    )
    second = await service.publish(course_id, 5, changed)

    contents = await client.call("core_course_get_contents", {"courseid": course_id})
    quiz = await get_quiz(client, course_id, first.cmid)
    found = modules_in(contents, first.cmid)
    assert second.cmid == first.cmid
    assert second.questions_replaced is True
    assert second.question_count == 4
    assert len(found) == 1
    assert found[0][0] == 5
    assert quiz["name"] == "Kuis Normalisasi (revisi)"
    assert quiz["timelimit"] == 0
    assert quiz["attempts"] == 1
    assert quiz["sumgrades"] == 4


async def student_token():
    async with httpx.AsyncClient(timeout=settings.moodle_timeout_seconds) as http:
        response = await http.post(
            f"{settings.MOODLE_BASE_URL.rstrip('/')}/login/token.php",
            data={"username": STUDENT_USERNAME, "password": STUDENT_PASSWORD, "service": "moodle_mobile_app"},
        )
    token = response.json().get("token")
    assert token, "token mahasiswa tidak didapat (cek service Mobile app aktif)"
    return token


@pytest.mark.skipif(
    not (STUDENT_USERNAME and STUDENT_PASSWORD),
    reason="Isi MOODLE_STUDENT_USERNAME dan MOODLE_STUDENT_PASSWORD untuk menguji pengerjaan quiz",
)
@pytest.mark.asyncio
async def test_student_can_take_the_quiz_and_questions_are_kept_after_attempts(client):
    course_id = await create_course(client)
    users = await client.call(
        "core_user_get_users_by_field", {"field": "username", "values": [STUDENT_USERNAME]}
    )
    assert users, "akun mahasiswa uji tidak ditemukan di Moodle"
    await client.call(
        "enrol_manual_enrol_users",
        {"enrolments": [{"roleid": STUDENT_ROLE_ID, "userid": users[0]["id"], "courseid": course_id}]},
    )
    service = MoodleQuizService(client, InMemoryMoodleMappingRepository())
    item = sample_quiz()
    result = await service.publish(course_id, 4, item)

    async with MoodleClient(
        settings.MOODLE_BASE_URL, await student_token(), timeout=settings.moodle_timeout_seconds
    ) as student:
        contents = await student.call("core_course_get_contents", {"courseid": course_id})
        attempt = (await student.call("mod_quiz_start_attempt", {"quizid": result.instance_id}))["attempt"]
        answers = []
        for page in range(3):
            data = await student.call(
                "mod_quiz_get_attempt_data", {"attemptid": attempt["id"], "page": page}
            )
            for question in data["questions"]:
                prefix = f"q{attempt['uniqueid']}:{question['slot']}_"
                answers.append({"name": prefix + "answer", "value": "0"})
                answers.append({"name": prefix + ":sequencecheck", "value": str(question["sequencecheck"])})
        finished = await student.call(
            "mod_quiz_process_attempt",
            {"attemptid": attempt["id"], "data": answers, "finishattempt": 1},
        )
        review = await student.call("mod_quiz_get_attempt_review", {"attemptid": attempt["id"]})

    found = modules_in(contents, result.cmid)
    assert len(found) == 1
    section_number, module = found[0]
    assert section_number == 4
    assert module["uservisible"] is True
    assert len(answers) == 6
    assert finished["state"] == "finished"
    assert review["attempt"]["state"] == "finished"
    assert len(review["questions"]) == 3
    review_html = " ".join(question["html"] for question in review["questions"])
    for correct in CORRECT_ANSWERS:
        assert f"The correct answer is: {correct}" in review_html  # kunci jawaban tersimpan benar

    # Setelah ada attempt, soal dipertahankan; hanya judul dan konfigurasi yang berubah.
    updated = await service.publish(
        course_id,
        4,
        QuizContent(id=item.id, title="Kuis Normalisasi (revisi)", description=item.description,
                    questions=item.questions[:1], settings=item.settings),
    )
    quiz = await get_quiz(client, course_id, result.cmid)
    assert updated.has_attempts is True
    assert updated.questions_replaced is False
    assert updated.question_count == 3
    assert quiz["name"] == "Kuis Normalisasi (revisi)"