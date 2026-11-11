"""Mode otomatis: RPS → course plan (disetujui bila lolos validasi) → konten, berhenti sebelum Moodle."""

from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from src.models.course_plan import CoursePlanStatus
from src.models.workflow import WorkflowStatus
from src.services.course_plan.errors import CoursePlanNotFoundError, CoursePlanStateError
from src.services.workflow import autopilot


class State:
    def __init__(self, *, plan_passes=True):
        self.steps = []
        self.notes = []
        self.plan = None
        self.plan_passes = plan_passes
        self.workflow = SimpleNamespace(id="wf1", status=WorkflowStatus.WAITING_FOR_REVIEW, rps_id="rps1")


@pytest.fixture
def state(monkeypatch):
    s = State()

    @asynccontextmanager
    async def session():
        yield object()

    monkeypatch.setattr(autopilot, "get_session_factory", lambda: session)

    async def workflow_of_rps(rps_id, owner_id):
        return s.workflow

    async def current(workflow_id, owner_id):
        return s.workflow

    monkeypatch.setattr(autopilot, "_workflow_of_rps", workflow_of_rps)
    monkeypatch.setattr(autopilot, "_current", current)

    class Workflows:
        async def record_event(self, workflow, **kwargs):
            s.notes.append(kwargs["message"])

        async def get_workflow(self, **kwargs):
            return s.workflow

    class Plans:
        async def get_latest(self, **kwargs):
            if s.plan is None:
                raise CoursePlanNotFoundError("wf1")
            return s.plan

        async def start_planning(self, **kwargs):
            s.steps.append("start_planning")

        async def approve(self, **kwargs):
            if not s.plan_passes:
                raise CoursePlanStateError("x", public_message="Course plan belum lolos validasi sehingga belum dapat disetujui.")
            s.steps.append("approve")
            s.plan = SimpleNamespace(status=CoursePlanStatus.APPROVED)

    class Contents:
        async def start(self, **kwargs):
            s.steps.append("start_content")

    from src.services.content.generation import ContentGenerationService
    from src.services.course_plan.service import CoursePlanService
    from src.services.workflow.service import WorkflowService

    monkeypatch.setattr(WorkflowService, "from_session", classmethod(lambda cls, session: Workflows()))
    monkeypatch.setattr(CoursePlanService, "from_session", classmethod(lambda cls, session: Plans()))
    monkeypatch.setattr(ContentGenerationService, "from_session", classmethod(lambda cls, session: Contents()))
    return s


def _runners(s):
    async def processing(**kwargs):
        s.steps.append("process_rps")

    async def planning(**kwargs):
        s.steps.append("plan")
        s.plan = SimpleNamespace(status=CoursePlanStatus.DRAFT)

    async def content(**kwargs):
        s.steps.append("content")

    return {"processing_runner": processing, "planning_runner": planning, "content_runner": content}


@pytest.mark.asyncio
async def test_runs_until_content_ready_for_review(state):
    await autopilot.run_autopilot_workflow(rps_id="rps1", owner_id="d1", **_runners(state))
    assert state.steps == ["process_rps", "start_planning", "plan", "approve", "start_content", "content"]
    assert state.notes[-1].startswith("Mode otomatis: konten selesai dibuat.")


@pytest.mark.asyncio
async def test_stops_at_plan_review_when_validation_fails(state):
    state.plan_passes = False
    await autopilot.run_autopilot_workflow(rps_id="rps1", owner_id="d1", **_runners(state))
    assert state.steps == ["process_rps", "start_planning", "plan"]
    assert "berhenti di review course plan" in state.notes[-1]


@pytest.mark.asyncio
async def test_stops_when_rps_processing_failed(state):
    state.workflow.status = WorkflowStatus.FAILED
    await autopilot.run_autopilot_workflow(rps_id="rps1", owner_id="d1", **_runners(state))
    assert state.steps == ["process_rps"]
