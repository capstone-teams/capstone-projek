import asyncio
from dataclasses import dataclass
from urllib.parse import parse_qs

import httpx
import pytest

from src.services.moodle_adapter import MoodleAdapter
from src.services.moodle_adapter_exceptions import (
    MoodleAuthenticationFailedError,
    MoodleCapabilityUnavailableError,
    MoodleOperationFailedError,
    MoodleTransientError,
)
from src.services.moodle_client import MoodleClient
from src.services.moodle_execution import (
    InMemoryMoodleExecutionRepository,
    MoodleExecutionStatus,
    MoodleExecutionTracker,
)
from src.services.moodle_integration_interface import LearningMaterial
from src.services.moodle_mapping import InMemoryMoodleMappingRepository, MoodleMapping
from src.services.moodle_mock import MockMoodleIntegration
from src.services.moodle_tracked_integration import TrackedMoodleIntegration

TOKEN = "test-token"
BASE_URL = "http://moodle.test"
COURSE = {"id": 42, "fullname": "Computer Science 101", "shortname": "cs101", "visible": 1}


def run(coro):
    return asyncio.run(coro)


def timeout(request):
    raise httpx.ReadTimeout("timeout", request=request)


@dataclass
class Setup:
    tracked: TrackedMoodleIntegration
    executions: InMemoryMoodleExecutionRepository
    mappings: InMemoryMoodleMappingRepository
    client: MoodleClient
    calls: list


def make_setup(responder, sleep=None):
    calls = []

    def handler(request):
        function = parse_qs(request.content.decode())["wsfunction"][0]
        calls.append(function)
        return responder(function, calls.count(function), request)

    async def no_sleep(seconds):
        return None

    executions = InMemoryMoodleExecutionRepository()
    mappings = InMemoryMoodleMappingRepository()
    tracker = MoodleExecutionTracker(executions)
    client = MoodleClient(BASE_URL, TOKEN, transport=httpx.MockTransport(handler))
    adapter = MoodleAdapter(
        client,
        mappings,
        sleep=sleep or no_sleep,
        retry_observer=tracker.observe_retry,
    )
    return Setup(TrackedMoodleIntegration(adapter, tracker), executions, mappings, client, calls)


def test_successful_operation_goes_from_running_to_success_with_moodle_id():
    executions = InMemoryMoodleExecutionRepository()
    tracker = MoodleExecutionTracker(executions)
    seen = {}

    async def action():
        seen["during"] = (await executions.list_for_entity("course", "course_1"))[0]
        return 42

    async def scenario():
        result = await tracker.run(
            "create_course", "course", "course_1", action, moodle_id_of=lambda value: value
        )
        assert result == 42
        assert seen["during"].status is MoodleExecutionStatus.RUNNING
        assert seen["during"].attempts == 1
        final = (await executions.list_for_entity("course", "course_1"))[0]
        assert final.status is MoodleExecutionStatus.SUCCESS
        assert final.moodle_id == 42
        assert final.operation == "create_course"
        assert final.internal_id == "course_1"
        assert final.error_category is None

    run(scenario())


def test_failed_operation_is_tracked_with_error_category_and_error_is_reraised():
    executions = InMemoryMoodleExecutionRepository()
    tracker = MoodleExecutionTracker(executions)

    async def action():
        raise MoodleAuthenticationFailedError("token ditolak")

    async def scenario():
        with pytest.raises(MoodleAuthenticationFailedError):
            await tracker.run("create_course", "course", "course_1", action)
        record = (await executions.list_for_entity("course", "course_1"))[0]
        assert record.status is MoodleExecutionStatus.FAILED
        assert record.error_category == "authentication"
        assert record.error_message == "token ditolak"
        assert record.moodle_id is None

    run(scenario())


def test_validation_and_unexpected_errors_get_their_own_category():
    executions = InMemoryMoodleExecutionRepository()
    tracker = MoodleExecutionTracker(executions)

    async def invalid():
        raise ValueError("input salah")

    async def unexpected():
        raise RuntimeError("boom")

    async def scenario():
        with pytest.raises(ValueError):
            await tracker.run("update_course", "course", "c1", invalid)
        with pytest.raises(RuntimeError):
            await tracker.run("update_course", "course", "c2", unexpected)
        assert (await executions.list_for_entity("course", "c1"))[0].error_category == "validation"
        assert (await executions.list_for_entity("course", "c2"))[0].error_category == "unexpected"

    run(scenario())


def test_long_error_message_is_truncated():
    executions = InMemoryMoodleExecutionRepository()
    tracker = MoodleExecutionTracker(executions)

    async def action():
        raise MoodleOperationFailedError("x" * 2000)

    async def scenario():
        with pytest.raises(MoodleOperationFailedError):
            await tracker.run("create_course", "course", "course_1", action)
        record = (await executions.list_for_entity("course", "course_1"))[0]
        assert len(record.error_message) == 500

    run(scenario())


def test_observe_retry_outside_a_tracked_run_does_nothing():
    tracker = MoodleExecutionTracker(InMemoryMoodleExecutionRepository())

    run(tracker.observe_retry(MoodleTransientError("timeout")))


def test_retries_are_visible_as_retrying_and_end_in_success():
    observed = []
    holder = {}

    def responder(function, number, request):
        if function == "core_course_update_courses":
            if number < 3:
                timeout(request)
            return httpx.Response(200, json={"warnings": []})
        return httpx.Response(200, json=[COURSE])

    async def sleep(seconds):
        record = (await holder["setup"].executions.list_for_entity("course", "course_1"))[0]
        observed.append((record.status, record.attempts, record.error_category))

    setup = make_setup(responder, sleep)
    holder["setup"] = setup

    async def scenario():
        await setup.mappings.save(MoodleMapping("course", "course_1", 42))
        await setup.tracked.update_course("course_1", fullname="Judul Baru")
        assert observed == [
            (MoodleExecutionStatus.RETRYING, 2, "transient"),
            (MoodleExecutionStatus.RETRYING, 3, "transient"),
        ]
        final = (await setup.executions.list_for_entity("course", "course_1"))[0]
        assert final.status is MoodleExecutionStatus.SUCCESS
        assert final.attempts == 3
        assert final.moodle_id == 42
        assert final.error_category is None
        await setup.client.aclose()

    run(scenario())


def test_exhausted_retries_end_in_failed_with_transient_category():
    def responder(function, number, request):
        if function == "core_course_update_courses":
            timeout(request)
        return httpx.Response(200, json=[COURSE])

    setup = make_setup(responder)

    async def scenario():
        await setup.mappings.save(MoodleMapping("course", "course_1", 42))
        with pytest.raises(MoodleTransientError):
            await setup.tracked.update_course("course_1", fullname="Judul Baru")
        record = (await setup.executions.list_for_entity("course", "course_1"))[0]
        assert record.status is MoodleExecutionStatus.FAILED
        assert record.attempts == 3
        assert record.error_category == "transient"
        await setup.client.aclose()

    run(scenario())


def test_create_course_execution_links_internal_id_to_moodle_id_and_survives_agent_retry():
    def responder(function, number, request):
        return httpx.Response(200, json=[COURSE] if function != "core_course_create_courses" else [{"id": 42}])

    setup = make_setup(responder)

    async def scenario():
        first = await setup.tracked.create_course("course_1", "CS 101", "cs101")
        second = await setup.tracked.create_course("course_1", "CS 101", "cs101")
        assert first.moodle_id == second.moodle_id == 42
        assert setup.calls.count("core_course_create_courses") == 1
        records = await setup.executions.list_for_entity("course", "course_1")
        assert len(records) == 2
        assert all(record.status is MoodleExecutionStatus.SUCCESS for record in records)
        assert all(record.moodle_id == 42 for record in records)
        await setup.client.aclose()

    run(scenario())


def test_unavailable_capability_is_recorded_as_failed_execution():
    setup = make_setup(lambda function, number, request: httpx.Response(200, json=[]))

    async def scenario():
        with pytest.raises(MoodleCapabilityUnavailableError):
            await setup.tracked.create_section("course_1", "week_a", 1, "Minggu 1")
        record = (await setup.executions.list_for_entity("course_plan_week", "week_a"))[0]
        assert record.operation == "create_section"
        assert record.status is MoodleExecutionStatus.FAILED
        assert record.error_category == "capability_unavailable"
        await setup.client.aclose()

    run(scenario())


def test_learning_material_execution_records_module_id_with_mock_integration():
    executions = InMemoryMoodleExecutionRepository()
    mock = MockMoodleIntegration()
    tracked = TrackedMoodleIntegration(mock, MoodleExecutionTracker(executions))
    material = LearningMaterial(title="Pengantar", content="<p>Isi</p>")

    async def scenario():
        await tracked.create_course("course_1", "CS 101", "cs101")
        await tracked.create_section("course_1", "week_a", 1, "Minggu 1")
        created = await tracked.create_learning_material("course_1", "week_a", "material_1", material)
        record = (await executions.list_for_entity("learning_material", "material_1"))[0]
        assert record.status is MoodleExecutionStatus.SUCCESS
        assert record.moodle_id == created.moodle_module_id

    run(scenario())


def test_read_operations_are_not_tracked():
    setup = make_setup(lambda function, number, request: httpx.Response(200, json=[COURSE]))

    async def scenario():
        await setup.mappings.save(MoodleMapping("course", "course_1", 42))
        await setup.tracked.get_course("course_1")
        assert await setup.executions.list_for_entity("course", "course_1") == []
        await setup.client.aclose()

    run(scenario())