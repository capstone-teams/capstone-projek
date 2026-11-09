"""Test adapter Course Planning Service dan validasi akademik (BE-14.3).

Tidak ada panggilan jaringan: provider LLM diganti stub. Yang diuji adalah
bagian yang mudah rusak tanpa terlihat — perenderan prompt, retry saat output
tidak sesuai schema, penerjemahan kegagalan provider, dan aturan validasi yang
menentukan apakah sebuah versi boleh disetujui (BE-14.2).
"""

from __future__ import annotations

import json

import pytest

from src.prompts.loader import render_prompt
from src.schemas.course_plan import (
    CoursePlanActivityType,
    CoursePlanCourse,
    CoursePlanOutput,
    CoursePlanWeek,
)
from src.services.course_plan.errors import CoursePlanGenerationError
from src.services.course_plan.planner import LLMCoursePlanner, PlanningRequest
from src.services.course_plan.validation import validate_plan
from src.services.llm import LLMService
from src.services.llm.base import BaseLLMProvider, LLMConnectionError

VALID_OUTPUT = {
    "course": {"title": "Basis Data", "code": "IF2230", "description": None},
    "weeks": [
        {
            "week_number": 1,
            "title": "Pengenalan Basis Data",
            "learning_outcomes": ["SUB-1"],
            "objectives": ["Mahasiswa memahami konsep basis data"],
            "topics": ["Pengenalan Basis Data"],
            "teaching_methods": ["Ceramah"],
            "planned_activities": ["learning_material"],
        }
    ],
}

REQUEST = PlanningRequest(
    rps_structured={
        "course": {"name": "Basis Data"},
        "sub_cpmk": [{"id": "SUB-1", "description": "Menjelaskan konsep"}],
        "weeks": [{"week": 1, "week_type": "regular", "topics": ["Pengenalan"]}],
    },
    instructor_context={
        "activity_configuration": {
            "learning_material": True,
            "learning_resource": False,
            "assignment": False,
            "quiz": False,
        }
    },
    activity_configuration={
        "learning_material": True,
        "learning_resource": False,
        "assignment": False,
        "quiz": False,
    },
)


class StubProvider(BaseLLMProvider):
    """Provider yang mengembalikan respons berurutan (atau melempar error)."""

    provider_name = "stub"
    model = "stub-model"

    def __init__(self, responses) -> None:
        self.responses = list(responses)
        self.prompts: list[str] = []

    async def generate(self, prompt, system_prompt=None, **kwargs) -> str:
        self.prompts.append(prompt)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def is_configured(self) -> bool:
        return True


async def _events():
    collected: list[dict] = []

    async def emit(**kwargs) -> None:
        collected.append(kwargs)

    return collected, emit


def test_prompt_renders_all_inputs():
    prompt = render_prompt(
        "course_planning",
        "v1",
        {
            "rps_structured": "{\"course\": \"Basis Data\"}",
            "instructor_context": "{\"instructor_profile\": {}}",
            "activity_configuration": "{\"learning_material\": true}",
            "previous_plan": "Tidak ada versi sebelumnya.",
            "revision_notes": "Tidak ada catatan penolakan.",
            "instruction": "Tidak ada instruksi tambahan.",
            "validation_feedback": "Tidak ada temuan validasi.",
            "output_schema": "{\"type\": \"object\"}",
        },
    )

    assert "Course Planning Agent" in prompt
    assert "# RPS Structured Data" in prompt
    assert "Basis Data" in prompt
    assert "# Activity Configuration" in prompt
    assert "Tidak ada versi sebelumnya." in prompt


@pytest.mark.asyncio
async def test_planner_retries_after_invalid_json():
    provider = StubProvider(["bukan json", json.dumps(VALID_OUTPUT)])
    collected, emit = await _events()
    planner = LLMCoursePlanner(service=LLMService(provider), max_fix_attempts=1)

    result = await planner.generate(REQUEST, emit_event=emit)

    assert result.attempts == 2
    assert result.output.course.title == "Basis Data"
    assert result.prompt_version == "course_planning/v1"
    assert result.model_name == "stub-model"
    names = [event["event"] for event in collected]
    assert "RETRY_FIX" in names
    assert names[-1] == "PLANNING_COMPLETED"
    assert len(provider.prompts) == 2


@pytest.mark.asyncio
async def test_planner_retries_after_schema_mismatch():
    provider = StubProvider([json.dumps({"weeks": []}), json.dumps(VALID_OUTPUT)])
    collected, emit = await _events()
    planner = LLMCoursePlanner(service=LLMService(provider), max_fix_attempts=1)

    result = await planner.generate(REQUEST, emit_event=emit)

    assert result.attempts == 2
    retry = [event for event in collected if event["event"] == "RETRY_FIX"][0]
    assert retry["reason_code"] == "SCHEMA_VALIDATION_FAILED"


# RPS dengan dua Sub-CPMK yang keduanya dipetakan ke minggu 1; rencana yang
# hanya mencakup satu di antaranya gagal validasi akademik meskipun schema-nya
# benar.
REQUEST_TWO_SUBS = PlanningRequest(
    rps_structured={
        "course": {"name": "Basis Data"},
        "sub_cpmk": [{"id": "SUB-1"}, {"id": "SUB-2"}],
        "weeks": [
            {"week": 1, "week_type": "regular", "sub_cpmk": ["SUB-1", "SUB-2"]}
        ],
    },
    activity_configuration={"learning_material": True},
)

OUTPUT_MISSING_SUB = {
    "course": {"title": "Basis Data", "code": "IF2230", "description": None},
    "weeks": [
        {
            "week_number": 1,
            "title": "Pengenalan Basis Data",
            "learning_outcomes": ["SUB-1"],
            "topics": ["Pengenalan Basis Data"],
            "teaching_methods": ["Ceramah"],
            "planned_activities": ["learning_material"],
        }
    ],
}

OUTPUT_COVERING_SUBS = {
    "course": {"title": "Basis Data", "code": "IF2230", "description": None},
    "weeks": [
        {
            "week_number": 1,
            "title": "Pengenalan Basis Data",
            "learning_outcomes": ["SUB-1", "SUB-2"],
            "topics": ["Pengenalan Basis Data"],
            "teaching_methods": ["Ceramah"],
            "planned_activities": ["learning_material"],
        }
    ],
}


@pytest.mark.asyncio
async def test_planner_retries_when_sub_cpmk_coverage_is_incomplete():
    provider = StubProvider(
        [json.dumps(OUTPUT_MISSING_SUB), json.dumps(OUTPUT_COVERING_SUBS)]
    )
    collected, emit = await _events()
    planner = LLMCoursePlanner(service=LLMService(provider), max_fix_attempts=1)

    result = await planner.generate(REQUEST_TWO_SUBS, emit_event=emit)

    assert result.attempts == 2
    retry = [event for event in collected if event["event"] == "RETRY_FIX"][0]
    assert retry["reason_code"] == "VALIDATION_FAILED"
    assert any("SUB-2" in detail for detail in retry["details"])
    # Temuan benar-benar dikirim balik ke model pada percobaan kedua.
    assert "SUB-2" in provider.prompts[1]


@pytest.mark.asyncio
async def test_planner_still_returns_plan_with_issues_when_budget_is_exhausted():
    """Rencana yang tetap tidak memenuhi aturan dikembalikan agar dosen dapat
    melihat temuannya dan meminta regenerasi (BE-14.2), bukan gagal total."""

    provider = StubProvider([json.dumps(OUTPUT_MISSING_SUB)] * 2)
    collected, emit = await _events()
    planner = LLMCoursePlanner(service=LLMService(provider), max_fix_attempts=1)

    result = await planner.generate(REQUEST_TWO_SUBS, emit_event=emit)

    assert result.attempts == 2
    assert collected[-1]["event"] == "PLANNING_COMPLETED"


@pytest.mark.asyncio
async def test_planner_fails_after_retry_budget_is_exhausted():
    provider = StubProvider(["bukan json", "tetap bukan json"])
    collected, emit = await _events()
    planner = LLMCoursePlanner(service=LLMService(provider), max_fix_attempts=1)

    with pytest.raises(CoursePlanGenerationError):
        await planner.generate(REQUEST, emit_event=emit)

    assert collected[-1]["event"] == "PLANNING_FAILED"
    assert collected[-1]["reason_code"] == "OUTPUT_NOT_JSON"


@pytest.mark.asyncio
async def test_provider_failure_is_reported_as_generation_failure():
    # LLMService sudah me-retry error provider sementara; sediakan cukup
    # respons agar kegagalan benar-benar sampai ke planner.
    provider = StubProvider([LLMConnectionError("tidak dapat dihubungi")] * 8)
    collected, emit = await _events()
    planner = LLMCoursePlanner(service=LLMService(provider), max_fix_attempts=1)

    with pytest.raises(CoursePlanGenerationError):
        await planner.generate(REQUEST, emit_event=emit)

    assert collected[-1]["event"] == "PLANNING_FAILED"
    assert collected[-1]["reason_code"] == "LLM_PROVIDER_ERROR"


def _output(*, weeks, activities=None) -> CoursePlanOutput:
    return CoursePlanOutput(
        course=CoursePlanCourse(title="Basis Data"),
        weeks=[
            CoursePlanWeek(
                week_number=number,
                title=f"Minggu {number}",
                learning_outcomes=codes,
                topics=topics,
                planned_activities=activities or [],
            )
            for number, codes, topics in weeks
        ],
    )


RPS = {
    "sub_cpmk": [{"id": "SUB-1"}, {"id": "SUB-2"}],
    "weeks": [
        {"week": 1, "week_type": "regular", "sub_cpmk": ["SUB-1"]},
        {"week": 2, "week_type": "uts", "sub_cpmk": []},
    ],
}


def test_validation_passes_for_a_plan_that_follows_the_rps():
    output = _output(
        weeks=[
            (1, ["SUB-1"], ["Pengenalan"]),
            (2, ["SUB-2"], []),
        ]
    )

    result = validate_plan(
        output,
        rps_structured=RPS,
        activity_configuration={"learning_material": True},
    )

    assert result == {"passed": True, "issues": []}


def test_validation_reports_week_and_sub_cpmk_mismatches():
    output = _output(
        weeks=[
            (1, ["SUB-9"], ["Pengenalan"]),
            (3, ["SUB-2"], []),
        ]
    )

    result = validate_plan(
        output,
        rps_structured=RPS,
        activity_configuration={"learning_material": True},
    )

    codes = [issue["code"] for issue in result["issues"]]
    assert "WEEK_MISSING" in codes
    assert "WEEK_NOT_IN_RPS" in codes
    assert "UNKNOWN_SUB_CPMK" in codes
    assert "SUB_CPMK_NOT_COVERED" in codes
    assert result["passed"] is False


def test_validation_rejects_material_and_disabled_activities_on_exam_week():
    output = _output(
        weeks=[
            (1, ["SUB-1"], ["Pengenalan"]),
            (2, ["SUB-2"], ["Materi baru"]),
        ],
        activities=[CoursePlanActivityType.ASSIGNMENT],
    )

    result = validate_plan(
        output,
        rps_structured=RPS,
        activity_configuration={
            "learning_material": True,
            "assignment": False,
        },
    )

    codes = [issue["code"] for issue in result["issues"]]
    assert "EXAM_WEEK_HAS_MATERIAL" in codes
    assert "ACTIVITY_NOT_ENABLED" in codes
    assert all(issue["week"] for issue in result["issues"])


def test_validation_ignores_week_that_fills_a_hole_in_rps_numbering():
    """Ekstraksi yang melewatkan minggu 2 tidak boleh menjadikan minggu 2 pada
    rencana sebagai temuan: rencana semester memang berurutan."""
    rps = {
        "sub_cpmk": [{"id": "SUB-1"}],
        "weeks": [
            {"week": 1, "week_type": "regular", "sub_cpmk": ["SUB-1"]},
            {"week": 3, "week_type": "regular"},
        ],
    }
    output = _output(
        weeks=[
            (1, ["SUB-1"], ["Pengenalan"]),
            (2, [], ["Materi yang hilang dari RPS"]),
            (3, [], ["Lanjutan"]),
        ]
    )

    result = validate_plan(
        output,
        rps_structured=rps,
        activity_configuration={"learning_material": True},
    )

    assert result == {"passed": True, "issues": []}


def test_validation_still_rejects_week_outside_rps_range():
    output = _output(
        weeks=[
            (1, ["SUB-1"], ["Pengenalan"]),
            (2, ["SUB-2"], []),
            (3, [], ["Minggu tambahan"]),
        ]
    )

    result = validate_plan(
        output,
        rps_structured=RPS,
        activity_configuration={"learning_material": True},
    )

    codes = [issue["code"] for issue in result["issues"]]
    assert "WEEK_NOT_IN_RPS" in codes


def test_validation_does_not_require_sub_cpmk_without_week_mapping():
    """Sub-CPMK yang dideklarasikan tetapi tidak dipetakan ke minggu mana pun
    adalah celah ekstraksi; rencana tidak dapat menutupinya tanpa mengarang."""
    rps = {
        "sub_cpmk": [{"id": "SUB-1"}, {"id": "SUB-2"}],
        "weeks": [
            {"week": 1, "week_type": "regular", "sub_cpmk": ["SUB-1"]},
        ],
    }
    output = _output(weeks=[(1, ["SUB-1"], ["Pengenalan"])])

    result = validate_plan(
        output,
        rps_structured=rps,
        activity_configuration={"learning_material": True},
    )

    assert result == {"passed": True, "issues": []}
