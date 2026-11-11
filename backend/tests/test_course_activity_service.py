"""Aktivitas dari halaman kursus: pembuatan lewat plugin dan draf AI dari referensi."""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.schemas.course_activity import ActivityModname, CreateActivityRequest
from src.services.course_activity_service import (
    ActivityGenerationError,
    CourseActivityService,
    ReferenceFile,
    UnsupportedReferenceFileError,
    extract_reference_text,
)


class FakeClient:
    def __init__(self):
        self.calls = []

    async def call(self, function, params=None, **kwargs):
        self.calls.append((function, params))
        return {"cmid": 77, "instanceid": 5, "created": 1}


class FakeMoodle:
    def __init__(self, sections=()):
        self.client = FakeClient()
        self._sections = list(sections)

    async def get_course(self, moodle_course_id):
        return SimpleNamespace(moodle_course_id=moodle_course_id)

    async def get_course_contents(self, moodle_course_id, *, with_intros=False):
        return SimpleNamespace(sections=self._sections)


class FakeLLM:
    def __init__(self, data):
        self.data = data
        self.calls = []

    async def execute_prompt(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(data=self.data)


def _section(number, modules):
    return SimpleNamespace(section_number=number, name=f"Pertemuan {number}", summary="<p>Sub-CPMK 1</p>", modules=modules)


def _module(modname, name, content=None, description=""):
    return SimpleNamespace(modname=modname, name=name, content=content, description=description)


@pytest.mark.asyncio
async def test_create_assignment_maps_form_to_plugin_parameters():
    moodle = FakeMoodle()
    request = CreateActivityRequest(
        section=3,
        modname="assign",
        name="  Tugas ERD ",
        intro="<p>Buat ERD</p>",
        duedate=200,
        grade=80,
        onlinetext_enabled=True,
        file_enabled=False,
    )
    result = await CourseActivityService(moodle).create(48, request)
    assert result.cmid == 77 and result.created and result.section == 3
    function, params = moodle.client.calls[0]
    assert function == "local_capstonebridge_create_assign"
    assert params == {
        "courseid": 48,
        "section": 3,
        "name": "Tugas ERD",
        "intro": "<p>Buat ERD</p>",
        "duedate": 200,
        "grade": 80,
        "onlinetext": 1,
        "filesubmission": 0,
        "maxfiles": 1,
    }


@pytest.mark.asyncio
async def test_create_quiz_and_label():
    moodle = FakeMoodle()
    quiz = CreateActivityRequest(
        section=2,
        modname="quiz",
        name="Kuis SQL",
        timelimit_minutes=15,
        questions=[{"text": "Perintah membaca data?", "generalfeedback": "SELECT membaca.", "answers": [{"text": "INSERT"}, {"text": "SELECT", "correct": True}]}],
    )
    await CourseActivityService(moodle).create(48, quiz)
    function, params = moodle.client.calls[0]
    assert function == "local_capstonebridge_create_quiz"
    assert params["idnumber"].startswith("capstone-manual-quiz-")
    assert params["timelimit"] == 900
    assert params["questions"] == [
        {
            "text": "<p>Perintah membaca data?</p>",
            "generalfeedback": "<p>SELECT membaca.</p>",
            "answers": [{"text": "INSERT", "correct": 0}, {"text": "SELECT", "correct": 1}],
        }
    ]

    # Text and media area dibuat sebagai Page lewat function plugin yang sudah terpasang; nama dari awal teks.
    await CourseActivityService(moodle).create(48, CreateActivityRequest(section=1, modname="label", text="<p>Halo semua</p>"))
    assert moodle.client.calls[1] == (
        "local_capstonebridge_create_page",
        {"courseid": 48, "section": 1, "name": "Halo semua", "content": "<p>Halo semua</p>"},
    )


def test_request_validation_per_kind():
    with pytest.raises(ValidationError, match="minimal satu soal"):
        CreateActivityRequest(section=1, modname="quiz", name="Kuis")
    with pytest.raises(ValidationError, match="tepat satu jawaban benar"):
        CreateActivityRequest(
            section=1, modname="quiz", name="Kuis",
            questions=[{"text": "x", "answers": [{"text": "a", "correct": True}, {"text": "b", "correct": True}]}],
        )
    with pytest.raises(ValidationError, match="name wajib"):
        CreateActivityRequest(section=1, modname="assign")
    with pytest.raises(ValidationError, match="text wajib"):
        CreateActivityRequest(section=1, modname="label", text="  ")
    with pytest.raises(ValidationError, match="jenis pengumpulan"):
        CreateActivityRequest(section=1, modname="assign", name="T", file_enabled=False, onlinetext_enabled=False)


@pytest.mark.asyncio
async def test_generate_quiz_uses_week_material_rps_and_file_references():
    moodle = FakeMoodle([_section(4, [_module("page", "Materi JOIN", content="<h2>JOIN</h2><p>INNER JOIN menggabungkan baris.</p>"), _module("quiz", "Kuis lama")])])
    llm = FakeLLM(
        {
            "name": "Kuis JOIN",
            "description": "Kerjakan.",
            "questions": [
                {"question_text": f"Soal {n}", "options": [{"key": "A", "text": "a"}, {"key": "B", "text": "b"}], "correct_option_key": "A", "explanation": "karena"}
                for n in range(1, 8)
            ],
        }
    )

    async def references(moodle_course_id, owner_id, section):
        assert (moodle_course_id, owner_id, section) == (48, "dosen-1", 4)
        return {"minggu": 4, "judul": "SQL JOIN"}, '{"cpmk": ["CPMK-2"]}'

    service = CourseActivityService(moodle, llm=llm, references=references)
    draft = await service.generate(
        48,
        owner_id="dosen-1",
        modname=ActivityModname.QUIZ,
        section=4,
        instruction="Fokus LEFT JOIN",
        question_count=5,
        difficulty="sulit",
        reference_file=ReferenceFile("catatan.md", "Contoh tabel mahasiswa dan nilai.".encode()),
    )
    assert draft.name == "Kuis JOIN"
    assert len(draft.questions) == 5  # dipotong sesuai jumlah yang diminta
    assert draft.references_used == ["Materi minggu ini", "RPS kursus", "File: catatan.md"]
    variables = llm.calls[0]["variables"]
    assert llm.calls[0]["prompt_name"] == "course_activity"
    assert "INNER JOIN menggabungkan baris." in variables["week_reference"]
    assert '"judul": "SQL JOIN"' in variables["week_reference"]
    assert "CPMK-2" in variables["rps_reference"]
    assert "Contoh tabel mahasiswa" in variables["file_reference"]
    assert "quiz: Kuis lama" in variables["existing_activities"]
    assert variables["quiz_settings"] == "Jumlah soal: 5. Tingkat kesulitan: sulit."


@pytest.mark.asyncio
async def test_generate_assignment_renders_rubric_html_and_requires_some_reference():
    llm = FakeLLM(
        {
            "name": "Studi Kasus ERD",
            "instructions_markdown": "## Kasus\n\n1. Identifikasi entitas",
            "expected_outputs": ["Diagram ERD"],
            "rubric": [{"criterion": "Ketepatan <entitas>", "description": "Lengkap", "weight_percent": 100}],
        }
    )

    async def references(*args):
        return None, ""

    service = CourseActivityService(FakeMoodle([_section(2, [])]), llm=llm, references=references)
    draft = await service.generate(48, owner_id="d", modname=ActivityModname.ASSIGN, section=2, instruction="Topik ERD")
    assert "<h3>Kasus</h3><ol><li>Identifikasi entitas</li></ol>" in draft.intro
    assert "<td>Ketepatan &lt;entitas&gt;</td>" in draft.intro
    assert "<h3>Rubrik penilaian</h3>" in draft.intro

    empty = CourseActivityService(FakeMoodle([]), llm=llm, references=references)
    with pytest.raises(ActivityGenerationError, match="Belum ada referensi"):
        await empty.generate(48, owner_id="d", modname=ActivityModname.ASSIGN, section=9, use_rps=False)


def test_reference_file_formats():
    assert extract_reference_text(ReferenceFile("a.txt", b"halo")) == "halo"
    with pytest.raises(UnsupportedReferenceFileError, match="Format file"):
        extract_reference_text(ReferenceFile("a.exe", b"x"))
    with pytest.raises(UnsupportedReferenceFileError, match="15 MB"):
        extract_reference_text(ReferenceFile("a.txt", b"x" * (15 * 1024 * 1024 + 1)))
