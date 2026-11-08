import asyncio
import re
from urllib.parse import parse_qs

import httpx
import pytest
from sqlalchemy import select

from src.models.moodle_entity_mapping import MoodleEntityMapping
from src.services.moodle_client import MoodleClient
from src.services.moodle_exceptions import MoodleAPIError
from src.services.moodle_mapping import InMemoryMoodleMappingRepository
from src.services.moodle_mapping_sql import SqlMoodleMappingRepository
from src.services.moodle_quiz_service import (
    QUIZ_ENTITY_TYPE,
    InvalidQuizError,
    MoodleQuizService,
    QuizContent,
    QuizOption,
    QuizQuestion,
    QuizSettings,
    quiz_idempotency_key,
)

COURSE_ID = 7
SETTING_FIELDS = ("timelimit", "attempts", "passpercent", "shufflequestions")


def unflatten_questions(body):
    """Susun ulang questions[i][answers][j][field] dari form Moodle REST."""
    questions = {}
    pattern = re.compile(r"questions\[(\d+)\]\[(\w+)\](?:\[(\d+)\]\[(\w+)\])?")
    for name, value in body.items():
        match = pattern.fullmatch(name)
        if not match:
            continue
        index, field, answer_index, answer_field = match.groups()
        question = questions.setdefault(int(index), {"answers": {}})
        if answer_index is None:
            question[field] = value
        else:
            question["answers"].setdefault(int(answer_index), {})[answer_field] = value
    return [
        {**question, "answers": [question["answers"][i] for i in sorted(question["answers"])]}
        for _, question in sorted(questions.items())
    ]


class FakeBridgePlugin:
    """Meniru local_capstonebridge_create_quiz / update_quiz pada satu course."""

    def __init__(self):
        self.modules = {}
        self.calls = []
        self.fail_with = None
        self.attempted = set()
        self._next_cmid = 300

    def handler(self, request):
        body = {key: values[0] for key, values in parse_qs(request.content.decode()).items()}
        function = body.pop("wsfunction")
        for reserved in ("wstoken", "moodlewsrestformat"):
            body.pop(reserved, None)
        body["questions"] = unflatten_questions(body)
        self.calls.append((function, body))
        if self.fail_with:
            return httpx.Response(200, json=self.fail_with)
        if function == "local_capstonebridge_create_quiz":
            return httpx.Response(200, json=self._create(body))
        if function == "local_capstonebridge_update_quiz":
            return httpx.Response(200, json=self._update(body))
        raise AssertionError(f"function tidak terduga: {function}")

    def _create(self, body):
        for cmid, module in self.modules.items():
            if module["idnumber"] == body["idnumber"]:
                return {"cmid": cmid, "instanceid": module["instanceid"], "created": 0,
                        "questioncount": len(module["questions"])}
        cmid = self._next_cmid
        self._next_cmid += 1
        self.modules[cmid] = {"instanceid": cmid + 1000, "idnumber": body["idnumber"]}
        self._apply(self.modules[cmid], body, replace_questions=True)
        return {"cmid": cmid, "instanceid": cmid + 1000, "created": 1,
                "questioncount": len(self.modules[cmid]["questions"])}

    def _update(self, body):
        cmid = int(body["cmid"])
        module = self.modules[cmid]
        has_attempts = cmid in self.attempted
        self._apply(module, body, replace_questions=not has_attempts)
        return {"cmid": cmid, "instanceid": module["instanceid"], "section": module["section"],
                "updated": 1, "hasattempts": int(has_attempts), "questionsreplaced": int(not has_attempts),
                "questioncount": len(module["questions"])}

    @staticmethod
    def _apply(module, body, replace_questions):
        module.update(
            section=int(body["section"]),
            name=body["name"],
            intro=body.get("intro", ""),
            **{name: int(body[name]) for name in SETTING_FIELDS},
        )
        if replace_questions:
            module["questions"] = body["questions"]

    def function_names(self):
        return [function for function, _ in self.calls]


def question(number, correct="B"):
    return QuizQuestion(
        question_text=f"Soal {number}: tabel disebut memenuhi 1NF jika...",
        options=(
            QuizOption("A", "Tidak ada primary key"),
            QuizOption("B", "Semua kolom bernilai atomik"),
            QuizOption("C", "Semua kolom nullable"),
        ),
        correct_option_key=correct,
        explanation="1NF mensyaratkan nilai atomik.",
    )


def quiz(**overrides):
    values = {
        "id": "act-quiz-001",
        "title": "Kuis Normalisasi",
        "description": "Kuis singkat pemahaman 1NF-3NF.",
        "questions": (question(1), question(2), question(3)),
        "settings": QuizSettings(time_limit_minutes=15, max_attempts=2, shuffle_questions=True,
                                 passing_score_percent=70),
    }
    values.update(overrides)
    return QuizContent(**values)


def run(coro):
    return asyncio.run(coro)


def publish_all(plugin, mappings, *steps):
    async def scenario():
        client = MoodleClient("http://moodle.test", "token", transport=httpx.MockTransport(plugin.handler))
        try:
            service = MoodleQuizService(client, mappings)
            return [await service.publish(COURSE_ID, week, item) for week, item in steps]
        finally:
            await client.aclose()

    return run(scenario())


def test_first_publish_creates_the_quiz_with_questions_in_the_week_section():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()

    [result] = publish_all(plugin, mappings, (4, quiz()))

    module = plugin.modules[result.cmid]
    assert result.created is True
    assert result.question_count == 3
    assert result.questions_replaced is True
    assert result.idempotency_key == "capstone-quiz-act-quiz-001"
    assert module["idnumber"] == result.idempotency_key
    assert module["section"] == 4
    assert module["timelimit"] == 900
    assert module["attempts"] == 2
    assert module["passpercent"] == 70
    assert module["shufflequestions"] == 1
    assert plugin.function_names() == ["local_capstonebridge_create_quiz"]
    assert run(mappings.get_moodle_id(QUIZ_ENTITY_TYPE, "act-quiz-001")) == result.cmid


def test_answer_key_and_explanation_are_sent_for_each_question():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()

    [result] = publish_all(plugin, mappings, (4, quiz(questions=(question(1, correct="C"),))))

    [sent] = plugin.modules[result.cmid]["questions"]
    assert sent["text"] == "<p>Soal 1: tabel disebut memenuhi 1NF jika...</p>"
    assert sent["generalfeedback"] == "<p>1NF mensyaratkan nilai atomik.</p>"
    assert sent["answers"] == [
        {"text": "Tidak ada primary key", "correct": "0"},
        {"text": "Semua kolom bernilai atomik", "correct": "0"},
        {"text": "Semua kolom nullable", "correct": "1"},
    ]


def test_republishing_updates_the_same_quiz_without_duplicates():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()

    first, second = publish_all(plugin, mappings, (4, quiz()), (4, quiz()))

    assert second.created is False
    assert second.cmid == first.cmid
    assert second.question_count == 3
    assert len(plugin.modules) == 1
    assert plugin.function_names() == [
        "local_capstonebridge_create_quiz",
        "local_capstonebridge_update_quiz",
    ]


def test_changed_quiz_replaces_questions_and_moves_to_the_new_week():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()
    changed = quiz(
        title="Kuis Normalisasi (revisi)",
        questions=(question(1), question(2), question(3), question(4)),
        settings=QuizSettings(),
    )

    first, second = publish_all(plugin, mappings, (4, quiz()), (5, changed))

    module = plugin.modules[first.cmid]
    assert second.cmid == first.cmid
    assert second.question_count == 4
    assert second.questions_replaced is True
    assert module["section"] == 5
    assert module["name"] == "Kuis Normalisasi (revisi)"
    assert module["timelimit"] == 0
    assert module["attempts"] == 1
    assert module["passpercent"] == 0
    assert module["shufflequestions"] == 0


def test_questions_are_kept_when_students_already_attempted_the_quiz():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()
    [first] = publish_all(plugin, mappings, (4, quiz()))
    plugin.attempted.add(first.cmid)

    [second] = publish_all(plugin, mappings, (4, quiz(title="Judul baru", questions=(question(9),))))

    assert second.has_attempts is True
    assert second.questions_replaced is False
    assert second.question_count == 3
    assert plugin.modules[first.cmid]["name"] == "Judul baru"


def test_quiz_left_in_moodle_without_mapping_is_reused_and_mapped():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()
    publish_all(plugin, InMemoryMoodleMappingRepository(), (4, quiz()))  # mapping hilang
    plugin.calls.clear()

    [result] = publish_all(plugin, mappings, (6, quiz(title="Judul baru")))

    assert result.created is False
    assert len(plugin.modules) == 1
    assert plugin.modules[result.cmid]["section"] == 6
    assert plugin.function_names() == [
        "local_capstonebridge_create_quiz",
        "local_capstonebridge_update_quiz",
    ]
    assert run(mappings.get_moodle_id(QUIZ_ENTITY_TYPE, "act-quiz-001")) == result.cmid


def test_text_is_escaped_before_it_is_sent():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()
    risky = QuizQuestion(
        question_text="Apa arti <script>alert(1)</script>?",
        options=(QuizOption("A", "x"), QuizOption("B", "y")),
        correct_option_key="A",
        explanation="Baris 1\nBaris 2",
    )

    [result] = publish_all(plugin, mappings, (1, quiz(description="A & B", questions=(risky,))))

    module = plugin.modules[result.cmid]
    [sent] = module["questions"]
    assert module["intro"] == "<p>A &amp; B</p>"
    assert sent["text"] == "<p>Apa arti &lt;script&gt;alert(1)&lt;/script&gt;?</p>"
    assert sent["generalfeedback"] == "<p>Baris 1<br>Baris 2</p>"


@pytest.mark.parametrize(
    ("week", "overrides"),
    [
        (-1, {}),
        (1, {"id": ""}),
        (1, {"id": "x" * 100}),
        (1, {"title": "  "}),
        (1, {"title": "x" * 256}),
        (1, {"questions": ()}),
        (1, {"questions": (QuizQuestion(" ", (QuizOption("A", "x"), QuizOption("B", "y")), "A"),)}),
        (1, {"questions": (QuizQuestion("Soal", (QuizOption("A", "x"),), "A"),)}),
        (1, {"questions": (QuizQuestion("Soal", (QuizOption("A", "x"), QuizOption("A", "y")), "A"),)}),
        (1, {"questions": (QuizQuestion("Soal", (QuizOption("A", "x"), QuizOption("B", "y")), "C"),)}),
        (1, {"questions": (QuizQuestion("Soal", (QuizOption("A", "x"), QuizOption("B", " ")), "A"),)}),
        (1, {"settings": QuizSettings(time_limit_minutes=0)}),
        (1, {"settings": QuizSettings(max_attempts=0)}),
        (1, {"settings": QuizSettings(passing_score_percent=101)}),
    ],
)
def test_invalid_quiz_is_rejected_before_calling_moodle(week, overrides):
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()

    with pytest.raises(InvalidQuizError):
        publish_all(plugin, mappings, (week, quiz(**overrides)))

    assert plugin.calls == []


def test_moodle_error_is_raised_and_no_mapping_is_saved():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()
    plugin.fail_with = {
        "exception": "invalid_parameter_exception",
        "errorcode": "invalidparameter",
        "message": "Invalid parameter value detected",
    }

    with pytest.raises(MoodleAPIError):
        publish_all(plugin, mappings, (1, quiz()))

    assert run(mappings.exists(QUIZ_ENTITY_TYPE, "act-quiz-001")) is False


def test_quiz_is_built_from_activity_data():
    activity_data = {
        "description": "Kuis singkat pemahaman 1NF-3NF.",
        "config": {
            "time_limit_minutes": 15,
            "max_attempts": 2,
            "shuffle_questions": True,
            "passing_score_percent": 70,
        },
        "questions": [
            {
                "question_text": f"Soal {number}: tabel disebut memenuhi 1NF jika...",
                "options": [
                    {"key": "A", "text": "Tidak ada primary key"},
                    {"key": "B", "text": "Semua kolom bernilai atomik"},
                    {"key": "C", "text": "Semua kolom nullable"},
                ],
                "correct_option_key": "B",
                "explanation": "1NF mensyaratkan nilai atomik.",
            }
            for number in (1, 2, 3)
        ],
        "traceability": {
            "week_number": 4,
            "sub_cpmk_codes": ["Sub-CPMK-3.1"],
            "weekly_plan_ref": "week-4",
        },
    }

    built = QuizContent.from_activity("act-quiz-001", "Kuis Normalisasi", activity_data)

    assert built == quiz()


def test_invalid_activity_data_is_rejected():
    with pytest.raises(InvalidQuizError):
        QuizContent.from_activity("act-quiz-001", "Kuis", {"description": "x", "questions": []})


def test_idempotency_key_is_stable():
    assert quiz_idempotency_key("act-1") == quiz_idempotency_key("act-1")
    assert quiz_idempotency_key("act-1") != quiz_idempotency_key("act-2")


def test_result_can_be_serialized():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()

    [result] = publish_all(plugin, mappings, (4, quiz()))

    assert result.to_dict() == {
        "quiz_id": "act-quiz-001",
        "moodle_course_id": COURSE_ID,
        "week": 4,
        "cmid": result.cmid,
        "instance_id": result.instance_id,
        "idempotency_key": "capstone-quiz-act-quiz-001",
        "created": True,
        "question_count": 3,
        "questions_replaced": True,
        "has_attempts": False,
    }


@pytest.mark.asyncio
async def test_moodle_object_id_is_stored_in_the_mapping_table(db_session):
    plugin = FakeBridgePlugin()
    repository = SqlMoodleMappingRepository(db_session)
    client = MoodleClient("http://moodle.test", "token", transport=httpx.MockTransport(plugin.handler))
    try:
        service = MoodleQuizService(client, repository)
        first = await service.publish(COURSE_ID, 4, quiz())
        second = await service.publish(COURSE_ID, 4, quiz())
    finally:
        await client.aclose()

    rows = (
        await db_session.execute(
            select(MoodleEntityMapping).where(MoodleEntityMapping.entity_type == QUIZ_ENTITY_TYPE)
        )
    ).scalars().all()
    assert [(row.internal_id, row.moodle_id) for row in rows] == [("act-quiz-001", first.cmid)]
    assert second.cmid == first.cmid