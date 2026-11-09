"""Tes alur generate + review konten, TANPA database dan TANPA panggilan OpenAI.

Yang diganti (fake):
  - LLM         : LLMService / OpenAIProvider di generate_service
  - Repository  : ContentGenerationRepository (penyimpanan in-memory)
  - DB session  : objek kecil dengan commit / rollback / get

Yang dipakai asli: schema Pydantic, registry, mapper to_row, validasi, retry,
transisi status, ContentReviewService, ActivityReviewService.

Letak file: tests/services/content/test_content_workflow.py
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from types import SimpleNamespace as NS

# Agar `python tests/test_content_workflow.py` bisa menemukan paket `src`:
# naik dari lokasi file ini sampai ketemu folder yang berisi `src/`.
_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir())
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
import pytest_asyncio

from src.models.activity import ActivityStatus
from src.models.content import ContentStatus
from src.schemas.content import OUTPUT_EXAMPLES
from src.services.content import generate_service as gen
from src.services.content import review_service as rev

pytestmark = pytest.mark.asyncio

PROMPT_TO_KEY = {
    "learning_material": "LEARNING_MATERIAL",
    "learning_resource": "RESOURCE",
    "quiz": "QUIZ",
    "assignment": "ASSIGNMENT",
}


# ==========================================
# FAKE: DATA MINGGU
# ==========================================
def make_week(number: int, week_type: str):
    return NS(
        id=f"week-{number}",
        course_plan_id="plan-1",
        week_number=number,
        title=f"Minggu {number}",
        metadata_={"week_type": week_type},
        learning_outcomes=["Sub-CPMK-3.1"],
        topics={"items": ["Normalisasi"]},
        methods={"items": ["Ceramah"]},
        assessment=None,
    )


WEEKS = [
    make_week(1, "regular"),
    make_week(2, "quiz"),
    make_week(3, "assignment"),
    make_week(4, "uts"),  # tidak punya jenis konten -> dilewati
]


# ==========================================
# FAKE: DB SESSION
# ==========================================
class FakeDB:
    def __init__(self, weeks):
        self.weeks = {w.id: w for w in weeks}
        self.commits = 0
        self.rollbacks = 0

    async def get(self, model, key):
        return self.weeks.get(key)

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


# ==========================================
# FAKE: REPOSITORY (in-memory)
# ==========================================
def make_fake_repository(weeks):
    contents: list = []
    activities: list = []

    class FakeRepository:
        @staticmethod
        async def get_context(db, course_plan_id):
            if course_plan_id != "plan-1":
                return None
            return NS(id="plan-1"), weeks

        # ---- contents ----
        @staticmethod
        async def get_by_week_id(db, course_plan_week_id, content_type=None):
            rows = [
                c
                for c in contents
                if c.course_plan_week_id == course_plan_week_id
                and (content_type is None or c.content_type == content_type)
            ]
            return max(rows, key=lambda c: c.version, default=None)

        @staticmethod
        async def get_by_id(db, content_id):
            return next((c for c in contents if c.id == content_id), None)

        @staticmethod
        async def update_status(db, content, status):
            content.status = status
            return content

        @staticmethod
        async def update_content(db, content, **fields):
            content.__dict__.update(fields)
            content.version += 1
            content.status = ContentStatus.DRAFT
            return content

        @staticmethod
        async def create(db, **fields):
            row = NS(
                id=f"content-{len(contents) + 1}",
                version=1,
                status=ContentStatus.DRAFT,
                **fields,
            )
            contents.append(row)
            return row

        # ---- activities ----
        @staticmethod
        async def get_activity_by_week_id(db, course_plan_week_id, activity_type):
            rows = [
                a
                for a in activities
                if a.course_plan_week_id == course_plan_week_id
                and a.type == activity_type
            ]
            return max(rows, key=lambda a: a.version, default=None)

        @staticmethod
        async def get_activity_by_id(db, activity_id):
            return next((a for a in activities if a.id == activity_id), None)

        @staticmethod
        async def update_activity_status(db, activity, status):
            activity.status = status
            return activity

        @staticmethod
        async def update_activity(db, activity, **fields):
            activity.__dict__.update(fields)
            activity.version += 1
            activity.status = ActivityStatus.DRAFT
            return activity

        @staticmethod
        async def create_activity(db, **fields):
            row = NS(
                id=f"activity-{len(activities) + 1}",
                version=1,
                status=ActivityStatus.DRAFT,
                **fields,
            )
            activities.append(row)
            return row

    return FakeRepository, contents, activities


# ==========================================
# FAKE: LLM
# ==========================================
class FakeLLM:
    """Mengembalikan contoh valid per prompt. `script[prompt]` bisa diisi antrean
    respons (dict / str / Exception) untuk mengatur skenario gagal-lalu-berhasil."""

    def __init__(self):
        self.calls: list = []
        self.script: dict[str, list] = {}

    def install(self, monkeypatch):
        llm = self

        class _Service:
            def __init__(self, provider):
                pass

            async def execute_prompt(self, *, prompt_name, version, variables, output_schema):
                llm.calls.append(
                    NS(
                        prompt=prompt_name,
                        version=version,
                        variables=variables,
                        schema=output_schema,
                    )
                )
                queue = llm.script.get(prompt_name)
                if queue:
                    item = queue.pop(0)
                else:
                    item = copy.deepcopy(OUTPUT_EXAMPLES[PROMPT_TO_KEY[prompt_name]])
                if isinstance(item, Exception):
                    raise item
                return NS(
                    data=item,
                    metadata=NS(prompt_tokens=10, completion_tokens=20),
                )

        monkeypatch.setattr(gen, "LLMService", _Service)
        monkeypatch.setattr(gen, "OpenAIProvider", lambda: NS(model="fake-model"))

    def prompts(self) -> list[str]:
        return [c.prompt for c in self.calls]


# ==========================================
# FIXTURES
# ==========================================
@pytest.fixture
def env(monkeypatch):
    repo, contents, activities = make_fake_repository(WEEKS)
    monkeypatch.setattr(gen, "ContentGenerationRepository", repo)
    monkeypatch.setattr(rev, "ContentGenerationRepository", repo)

    llm = FakeLLM()
    llm.install(monkeypatch)

    return NS(
        db=FakeDB(WEEKS),
        llm=llm,
        contents=contents,
        activities=activities,
    )


async def generate_all(env, **kwargs):
    """Default include_resources=False agar tes lama tetap fokus pada satu hal.
    Perilaku asli (resource dibuat dulu lalu masuk materi) dites lewat generate_linked."""
    kwargs.setdefault("include_resources", False)
    return await gen.generate_contents(
        env.db, "plan-1", max_fix_attempts=1, **kwargs
    )


async def generate_linked(env, **kwargs):
    """Perilaku default sebenarnya: include_resources=True."""
    return await gen.generate_contents(
        env.db, "plan-1", max_fix_attempts=1, **kwargs
    )


def calls_of(env, prompt):
    return [c for c in env.llm.calls if c.prompt == prompt]


RESOURCE_TITLE = OUTPUT_EXAMPLES["RESOURCE"]["title"]
NO_RESOURCES_TEXT = "Tidak ada sumber belajar yang tersedia."


def invalid_assignment():
    """Total bobot rubrik 90 -> ditolak validator (harus 100)."""
    data = copy.deepcopy(OUTPUT_EXAMPLES["ASSIGNMENT"])
    data["rubric"][1]["weight_percent"] = 30
    return data


# ==========================================
# 1. GENERATE
# ==========================================
async def test_generate_all_weeks_picks_content_type_by_week_type(env):
    results = await generate_all(env)

    got = {(r.ctx.week_number, r.content_type) for r in results}
    assert got == {
        (1, "LEARNING_MATERIAL"),
        (2, "QUIZ"),
        (3, "ASSIGNMENT"),
    }  # minggu 4 (uts) dilewati
    assert all(r.error is None and r.material is not None for r in results)
    assert sorted(env.llm.prompts()) == ["assignment", "learning_material", "quiz"]


async def test_generate_saves_to_the_right_table(env):
    await generate_all(env)

    assert [c.content_type for c in env.contents] == ["LEARNING_MATERIAL"]
    assert sorted(a.type for a in env.activities) == ["ASSIGNMENT", "QUIZ"]
    assert env.db.commits == 3


async def test_generate_selected_weeks_only(env):
    results = await generate_all(env, week_numbers=[2])

    assert [(r.ctx.week_number, r.content_type) for r in results] == [(2, "QUIZ")]
    assert env.llm.prompts() == ["quiz"]
    assert env.contents == []


async def test_generate_save_false_does_not_touch_storage(env):
    results = await generate_all(env, save=False)

    assert len(results) == 3
    assert env.contents == [] and env.activities == []


@pytest.mark.parametrize(
    "week_numbers",
    [[], [0], [1, 1], [4], [99]],
    ids=["kosong", "nol", "duplikat", "week-uts", "tidak-ada"],
)
async def test_generate_rejects_invalid_week_numbers(env, week_numbers):
    with pytest.raises(ValueError):
        await generate_all(env, week_numbers=week_numbers)


async def test_generate_unknown_course_plan(env):
    with pytest.raises(gen.ContentGenerationError):
        await gen.generate_contents(env.db, "tidak-ada")


async def test_generate_unknown_content_type_filter(env):
    with pytest.raises(ValueError):
        await generate_all(env, content_types=["PODCAST"])


# ==========================================
# 2. ISI HASIL GENERATE
# ==========================================
async def test_material_markdown_is_rendered_from_sections(env):
    await generate_all(env, week_numbers=[1])

    md = env.contents[0].content_markdown
    assert md.startswith("## Tujuan Pembelajaran")
    assert "## Pengantar" in md
    assert "TODO" not in md


async def test_traceability_is_filled_by_backend(env):
    await generate_all(env)

    trace = env.contents[0].content_data["traceability"]
    assert trace == {
        "week_number": 1,
        "sub_cpmk_codes": ["Sub-CPMK-3.1"],
        "weekly_plan_ref": "week-1",
    }
    for a in env.activities:
        assert a.activity_data["traceability"]["weekly_plan_ref"] == a.course_plan_week_id


async def test_stored_json_has_no_title_or_llm_only_fields(env):
    await generate_all(env)

    assert "title" not in env.contents[0].content_data
    assert "sub_cpmk_codes" not in env.contents[0].content_data
    quiz = next(a for a in env.activities if a.type == "QUIZ")
    assert quiz.title == "Kuis Normalisasi"
    assert quiz.activity_data["questions"][0]["correct_option_key"] == "A"


async def test_output_schema_sent_to_llm_is_strict(env):
    await generate_all(env, week_numbers=[3])

    schema = env.llm.calls[0].schema
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])


# ==========================================
# 3. RETRY OTOMATIS (validasi gagal -> perbaiki)
# ==========================================
async def test_invalid_output_triggers_fix_attempt_with_feedback(env):
    env.llm.script["assignment"] = [invalid_assignment()]  # percobaan 1 gagal, 2 berhasil

    results = await generate_all(env, week_numbers=[3])

    assert results[0].error is None
    assert len(env.llm.calls) == 2
    assert env.llm.calls[0].variables["validation_feedback"] == ""
    assert env.llm.calls[1].variables["validation_feedback"] != ""
    assert len(env.activities) == 1


async def test_output_not_json_is_retried(env):
    env.llm.script["quiz"] = ["bukan json {"]

    results = await generate_all(env, week_numbers=[2])

    assert results[0].error is None
    assert len(env.llm.calls) == 2


async def test_generation_fails_after_max_attempts(env):
    env.llm.script["assignment"] = [invalid_assignment(), invalid_assignment()]

    results = await generate_all(env, week_numbers=[3])

    err = results[0].error
    assert results[0].material is None
    assert err.reason_code == "SCHEMA_VALIDATION_FAILED"
    assert err.attempts == 2
    assert "tugas" in str(err)
    assert env.activities == []


async def test_provider_error_is_reported_not_raised(env):
    env.llm.script["quiz"] = [RuntimeError("boom")]

    results = await generate_all(env, week_numbers=[2])

    assert results[0].material is None
    assert results[0].error is not None
    assert env.activities == []


async def test_one_failed_week_does_not_block_others(env):
    env.llm.script["quiz"] = [RuntimeError("boom")]

    results = await generate_all(env)

    by_type = {r.content_type: r for r in results}
    assert by_type["QUIZ"].error is not None
    assert by_type["LEARNING_MATERIAL"].error is None
    assert by_type["ASSIGNMENT"].error is None
    assert len(env.contents) == 1 and len(env.activities) == 1


async def test_event_and_trace_handlers_are_called(env):
    events, traces = [], []

    async def on_event(*args, **fields):
        events.append((args, fields))

    async def on_trace(**fields):
        traces.append(fields)

    await generate_all(
        env, week_numbers=[1], emit_event=on_event, record_trace=on_trace
    )

    assert events
    assert [t["validation"] for t in traces] == ["success"]


# ==========================================
# 4. GENERATE ULANG & KONTEN APPROVED
# ==========================================
async def test_regenerate_updates_same_row_and_bumps_version(env):
    await generate_all(env, week_numbers=[1])
    await generate_all(env, week_numbers=[1])

    assert len(env.contents) == 1
    assert env.contents[0].version == 2
    assert env.contents[0].status == ContentStatus.DRAFT


async def test_approved_content_is_not_overwritten(env):
    await generate_all(env, week_numbers=[1])
    env.contents[0].status = ContentStatus.APPROVED

    results = await generate_all(env, week_numbers=[1])

    assert results[0].material is None
    assert results[0].error.reason_code == "ALREADY_APPROVED"
    assert env.contents[0].version == 1


async def test_approved_activity_is_not_overwritten(env):
    await generate_all(env, week_numbers=[2])
    env.activities[0].status = ActivityStatus.APPROVED

    results = await generate_all(env, week_numbers=[2])

    assert results[0].error.reason_code == "ALREADY_APPROVED"
    assert env.activities[0].version == 1


async def test_resource_is_optional_and_does_not_overwrite_material(env):
    await generate_all(env, week_numbers=[1])
    results = await generate_all(env, week_numbers=[1], content_types=["RESOURCE"])

    assert [(r.content_type, r.error) for r in results] == [("RESOURCE", None)]
    assert sorted(c.content_type for c in env.contents) == ["LEARNING_MATERIAL", "RESOURCE"]
    material = next(c for c in env.contents if c.content_type == "LEARNING_MATERIAL")
    assert material.version == 1


async def test_resource_with_unknown_url_is_accepted(env):
    resource = copy.deepcopy(OUTPUT_EXAMPLES["RESOURCE"])
    resource["url"] = None
    env.llm.script["learning_resource"] = [resource]

    results = await generate_all(env, week_numbers=[1], content_types=["RESOURCE"])

    assert results[0].error is None
    assert env.contents[0].content_data["url"] is None


async def test_resource_cannot_be_generated_in_quiz_week(env):
    with pytest.raises(ValueError):
        await generate_all(env, week_numbers=[2], content_types=["RESOURCE"])


# ==========================================
# 5. REVIEW KONTEN (contents)
# ==========================================
async def make_content(env):
    await generate_all(env, week_numbers=[1])
    return env.contents[0]


async def test_content_review_happy_path(env):
    content = await make_content(env)
    service = rev.ContentReviewService()

    await service.validate_content(env.db, content.id)
    assert content.status == ContentStatus.VALIDATED
    await service.submit_for_review(env.db, content.id)
    assert content.status == ContentStatus.PENDING_REVIEW
    await service.approve_content(env.db, content.id)
    assert content.status == ContentStatus.APPROVED


async def test_content_cannot_skip_steps_from_draft(env):
    content = await make_content(env)
    service = rev.ContentReviewService()

    with pytest.raises(rev.InvalidStatusTransition):
        await service.submit_for_review(env.db, content.id)
    with pytest.raises(rev.InvalidStatusTransition):
        await service.approve_content(env.db, content.id)


async def test_content_approved_is_final(env):
    content = await make_content(env)
    service = rev.ContentReviewService()
    await service.validate_content(env.db, content.id)
    await service.submit_for_review(env.db, content.id)
    await service.approve_content(env.db, content.id)

    with pytest.raises(rev.InvalidStatusTransition):
        await service.reject_content(env.db, content.id, "terlambat")
    with pytest.raises(rev.InvalidStatusTransition):
        await service.retry_content(env.db, content.id)


async def test_content_reject_then_retry_returns_to_draft(env):
    content = await make_content(env)
    service = rev.ContentReviewService()
    await service.validate_content(env.db, content.id)
    await service.submit_for_review(env.db, content.id)
    await service.reject_content(env.db, content.id, "kurang contoh")
    assert content.status == ContentStatus.REJECTED

    await service.retry_content(env.db, content.id, additional_prompt="tambah contoh")

    assert content.status == ContentStatus.DRAFT
    assert content.version == 2
    assert "tambah contoh" in env.llm.calls[-1].variables["additional_prompt"]


async def test_content_retry_passes_handlers_to_generation(env):
    content = await make_content(env)
    traces = []

    async def on_trace(**fields):
        traces.append(fields)

    await rev.ContentReviewService().retry_content(
        env.db, content.id, record_trace=on_trace
    )

    assert [t["validation"] for t in traces] == ["success"]


async def test_content_retry_failure_keeps_existing_content(env):
    content = await make_content(env)
    old_data = copy.deepcopy(content.content_data)
    env.llm.script["learning_material"] = [RuntimeError("boom")]

    with pytest.raises(gen.ContentGenerationError):
        await rev.ContentReviewService().retry_content(env.db, content.id)

    assert content.content_data == old_data
    assert content.version == 1


async def test_content_not_found(env):
    with pytest.raises(rev.ContentNotFoundError):
        await rev.ContentReviewService().validate_content(env.db, "tidak-ada")


# ==========================================
# 6. REVIEW AKTIVITAS (activities: kuis & assignment)
# ==========================================
@pytest_asyncio.fixture(params=[(2, "QUIZ", "quiz"), (3, "ASSIGNMENT", "assignment")], ids=["quiz", "assignment"])
async def activity_case(env, request):
    week, key, prompt = request.param
    await generate_all(env, week_numbers=[week])
    return NS(activity=env.activities[0], key=key, prompt=prompt)


async def test_activity_review_happy_path(env, activity_case):
    a = activity_case.activity
    service = rev.ActivityReviewService()

    await service.validate_activity(env.db, a.id)
    assert a.status == ActivityStatus.VALIDATED
    await service.approve_activity(env.db, a.id)
    assert a.status == ActivityStatus.APPROVED
    await service.mark_executed(env.db, a.id)
    assert a.status == ActivityStatus.EXECUTED


async def test_activity_cannot_skip_validation(env, activity_case):
    service = rev.ActivityReviewService()

    with pytest.raises(rev.InvalidStatusTransition):
        await service.approve_activity(env.db, activity_case.activity.id)
    with pytest.raises(rev.InvalidStatusTransition):
        await service.mark_executed(env.db, activity_case.activity.id)


async def test_activity_executed_is_final(env, activity_case):
    a = activity_case.activity
    service = rev.ActivityReviewService()
    await service.validate_activity(env.db, a.id)
    await service.approve_activity(env.db, a.id)
    await service.mark_executed(env.db, a.id)

    with pytest.raises(rev.InvalidStatusTransition):
        await service.validate_activity(env.db, a.id)
    with pytest.raises(rev.InvalidStatusTransition):
        await service.retry_activity(env.db, a.id)


async def test_activity_retry_resets_to_draft_and_bumps_version(env, activity_case):
    a = activity_case.activity
    service = rev.ActivityReviewService()
    await service.validate_activity(env.db, a.id)

    await service.retry_activity(env.db, a.id, additional_prompt="lebih sulit")

    assert a.status == ActivityStatus.DRAFT
    assert a.version == 2
    assert env.llm.calls[-1].prompt == activity_case.prompt
    assert "lebih sulit" in env.llm.calls[-1].variables["additional_prompt"]


async def test_approved_activity_cannot_be_retried(env, activity_case):
    a = activity_case.activity
    service = rev.ActivityReviewService()
    await service.validate_activity(env.db, a.id)
    await service.approve_activity(env.db, a.id)

    with pytest.raises(rev.InvalidStatusTransition):
        await service.retry_activity(env.db, a.id)


async def test_activity_has_no_reject_flow():
    service = rev.ActivityReviewService()
    assert not hasattr(service, "reject_activity")
    assert not hasattr(service, "submit_for_review")


async def test_activity_not_found(env):
    with pytest.raises(rev.ContentNotFoundError):
        await rev.ActivityReviewService().validate_activity(env.db, "tidak-ada")


# ==========================================
# 7. OPSI TAMBAH ASSIGNMENT (dosen)
# ==========================================
async def test_assignment_is_off_by_default_in_regular_week(env):
    results = await generate_all(env, week_numbers=[1])

    assert [r.content_type for r in results] == ["LEARNING_MATERIAL"]
    assert env.activities == []


async def test_include_assignment_generates_it_together_with_material(env):
    results = await generate_all(env, week_numbers=[1], include_assignment=True)

    assert {r.content_type for r in results} == {"LEARNING_MATERIAL", "ASSIGNMENT"}
    assert sorted(env.llm.prompts()) == ["assignment", "learning_material"]
    assert [c.content_type for c in env.contents] == ["LEARNING_MATERIAL"]
    assert [a.type for a in env.activities] == ["ASSIGNMENT"]
    assert env.activities[0].course_plan_week_id == "week-1"


async def test_include_assignment_does_not_duplicate_or_affect_other_weeks(env):
    results = await generate_all(env, include_assignment=True)

    got = sorted((r.ctx.week_number, r.content_type) for r in results)
    assert got == [
        (1, "ASSIGNMENT"),
        (1, "LEARNING_MATERIAL"),
        (2, "QUIZ"),
        (3, "ASSIGNMENT"),
    ]


async def test_assignment_failure_does_not_block_material(env):
    env.llm.script["assignment"] = [RuntimeError("boom")]

    results = await generate_all(env, week_numbers=[1], include_assignment=True)

    by_type = {r.content_type: r for r in results}
    assert by_type["ASSIGNMENT"].error is not None
    assert by_type["LEARNING_MATERIAL"].error is None
    assert len(env.contents) == 1 and env.activities == []


async def test_assignment_in_regular_week_can_be_retried(env):
    await generate_all(env, week_numbers=[1], include_assignment=True)
    a = env.activities[0]
    service = rev.ActivityReviewService()

    await service.validate_activity(env.db, a.id)
    await service.retry_activity(env.db, a.id)

    assert a.version == 2 and a.status == ActivityStatus.DRAFT


# ==========================================
# 8. REGENERASI: versi sebelumnya + catatan revisi
# ==========================================
async def test_first_generation_has_no_previous_version(env):
    await generate_all(env, week_numbers=[1])

    variables = env.llm.calls[0].variables
    assert variables["previous_version"] == ""
    assert variables["revision_notes"] == ""


async def test_content_regeneration_sends_previous_version_and_notes(env):
    content = await make_content(env)

    await rev.ContentReviewService().retry_content(
        env.db, content.id, revision_notes="tambah contoh kode"
    )

    variables = env.llm.calls[-1].variables
    assert variables["revision_notes"] == "tambah contoh kode"
    assert "Normalisasi Basis Data" in variables["previous_version"]
    assert "traceability" not in variables["previous_version"]


async def test_activity_regeneration_sends_previous_version_and_notes(env, activity_case):
    a = activity_case.activity

    await rev.ActivityReviewService().retry_activity(
        env.db, a.id, revision_notes="soal lebih sulit"
    )

    variables = env.llm.calls[-1].variables
    assert variables["revision_notes"] == "soal lebih sulit"
    assert a.title in variables["previous_version"]
    assert "traceability" not in variables["previous_version"]


async def test_regeneration_overwrites_without_keeping_history(env):
    content = await make_content(env)
    await rev.ContentReviewService().retry_content(env.db, content.id)

    assert len(env.contents) == 1  # tidak ada baris riwayat; baris yang sama ditimpa
    assert env.contents[0].version == 2


async def test_reject_reason_goes_to_revision_notes_not_style_prompt(env):
    content = await make_content(env)
    content.reject_reason = ""  # kolom ada di model (hasattr -> True)
    service = rev.ContentReviewService()
    await service.validate_content(env.db, content.id)
    await service.submit_for_review(env.db, content.id)
    await service.reject_content(env.db, content.id, "kurang contoh")

    await service.retry_content(env.db, content.id)

    variables = env.llm.calls[-1].variables
    assert "kurang contoh" in variables["revision_notes"]
    assert "kurang contoh" not in variables["additional_prompt"]


# ==========================================
# 9. LEARNING MATERIAL MEMAKAI LEARNING RESOURCE
# ==========================================
async def test_resource_is_generated_before_material_by_default(env):
    results = await generate_linked(env, week_numbers=[1])

    assert [(r.content_type, r.error) for r in results] == [
        ("RESOURCE", None),
        ("LEARNING_MATERIAL", None),
    ]
    assert env.llm.prompts() == ["learning_resource", "learning_material"]
    assert sorted(c.content_type for c in env.contents) == ["LEARNING_MATERIAL", "RESOURCE"]


async def test_material_prompt_receives_generated_resource(env):
    await generate_linked(env, week_numbers=[1])

    resource_call = calls_of(env, "learning_resource")[0]
    material_call = calls_of(env, "learning_material")[0]

    assert resource_call.variables["learning_resources"] == NO_RESOURCES_TEXT
    text = material_call.variables["learning_resources"]
    assert RESOURCE_TITLE in text
    assert "https://example.com/normalization" in text
    assert "traceability" not in text and "sub_cpmk_codes" not in text


async def test_resource_with_null_url_is_passed_as_null(env):
    resource = copy.deepcopy(OUTPUT_EXAMPLES["RESOURCE"])
    resource["url"] = None
    env.llm.script["learning_resource"] = [resource]

    await generate_linked(env, week_numbers=[1])

    assert '"url": null' in calls_of(env, "learning_material")[0].variables["learning_resources"]


async def test_material_still_generated_when_resource_fails(env):
    env.llm.script["learning_resource"] = [RuntimeError("boom")]

    results = await generate_linked(env, week_numbers=[1])

    by_type = {r.content_type: r for r in results}
    assert by_type["RESOURCE"].error is not None
    assert by_type["LEARNING_MATERIAL"].error is None
    assert calls_of(env, "learning_material")[0].variables["learning_resources"] == NO_RESOURCES_TEXT
    assert [c.content_type for c in env.contents] == ["LEARNING_MATERIAL"]


async def test_material_falls_back_to_saved_resource_when_new_one_fails(env):
    await generate_linked(env, week_numbers=[1])
    env.llm.script["learning_resource"] = [RuntimeError("boom")]

    results = await generate_linked(env, week_numbers=[1])

    assert {r.content_type: r.error is None for r in results} == {
        "RESOURCE": False,
        "LEARNING_MATERIAL": True,
    }
    assert RESOURCE_TITLE in calls_of(env, "learning_material")[-1].variables["learning_resources"]


async def test_material_retry_reuses_saved_resource_without_calling_resource_prompt(env):
    await generate_linked(env, week_numbers=[1])
    material = next(c for c in env.contents if c.content_type == "LEARNING_MATERIAL")
    resource_calls = len(calls_of(env, "learning_resource"))

    await rev.ContentReviewService().retry_content(env.db, material.id)

    assert len(calls_of(env, "learning_resource")) == resource_calls
    assert RESOURCE_TITLE in calls_of(env, "learning_material")[-1].variables["learning_resources"]
    assert material.version == 2


async def test_include_resources_false_skips_resource_prompt(env):
    await generate_linked(env, week_numbers=[1], include_resources=False)

    assert env.llm.prompts() == ["learning_material"]
    assert calls_of(env, "learning_material")[0].variables["learning_resources"] == NO_RESOURCES_TEXT


async def test_resource_only_for_weeks_that_generate_material(env):
    await generate_linked(env)  # minggu 1 regular, 2 quiz, 3 assignment, 4 uts

    assert len(calls_of(env, "learning_resource")) == 1
    prompts = env.llm.prompts()
    assert prompts.index("learning_resource") < prompts.index("learning_material")


async def test_resource_material_and_assignment_together(env):
    results = await generate_linked(env, week_numbers=[1], include_assignment=True)

    assert {r.content_type for r in results} == {"RESOURCE", "LEARNING_MATERIAL", "ASSIGNMENT"}
    prompts = env.llm.prompts()
    assert prompts.index("learning_resource") < prompts.index("learning_material")
    assert all(r.error is None for r in results)


async def test_material_references_are_stored_and_rendered(env):
    await generate_linked(env, week_numbers=[1])

    material = next(c for c in env.contents if c.content_type == "LEARNING_MATERIAL")
    assert material.content_data["references"][0]["title"] == RESOURCE_TITLE
    assert f"## Referensi\n\n- [{RESOURCE_TITLE}](https://example.com/normalization)" in material.content_markdown


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v", *sys.argv[1:]]))
