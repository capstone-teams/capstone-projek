from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.content import service


@pytest.fixture
def week_context():
    return SimpleNamespace(
        week=1,
        week_number=1,
        to_prompt_dict=lambda: {
            "course": {"name": "Matematika Diskrit"},
            "week": 1,
        },
    )


@pytest.fixture
def valid_output():
    return {
        "content_learning": [
            {
                "name": "Pengantar Graf",
                "material_learning": "Graf adalah struktur matematika yang terdiri dari simpul dan sisi.",
            }
        ]
    }


@pytest.fixture
def mock_llm(monkeypatch):
    provider = SimpleNamespace(model="gpt-4o-mini")
    execute_prompt = AsyncMock()

    llm_service = MagicMock()
    llm_service.execute_prompt = execute_prompt

    provider_class = MagicMock(return_value=provider)
    service_class = MagicMock(return_value=llm_service)

    monkeypatch.setattr(service, "OpenAIProvider", provider_class)
    monkeypatch.setattr(service, "LLMService", service_class)

    monkeypatch.setattr(service, "emit", AsyncMock())
    monkeypatch.setattr(service, "trace", AsyncMock())

    return SimpleNamespace(
        provider=provider,
        execute_prompt=execute_prompt,
        provider_class=provider_class,
        service_class=service_class,
    )


def llm_result(data):
    return SimpleNamespace(
        data=data,
        metadata=SimpleNamespace(
            prompt_tokens=100,
            completion_tokens=50,
        ),
    )


# ============================================================
# 1. SUCCESS
# ============================================================

@pytest.mark.asyncio
async def test_generate_week_content_success(
    week_context,
    valid_output,
    mock_llm,
):
    mock_llm.execute_prompt.return_value = llm_result(valid_output)

    result = await service._generate_week_content(
        week_context,
        max_fix_attempts=2,
    )

    assert isinstance(result, service.GeneratedLearningMaterial)
    assert len(result.content_learning) == 1
    assert result.content_learning[0].name == "Pengantar Graf"

    mock_llm.execute_prompt.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_week_content_passes_prompt_variables(
    week_context,
    valid_output,
    mock_llm,
):
    mock_llm.execute_prompt.return_value = llm_result(valid_output)

    await service._generate_week_content(
        week_context,
        additional_prompt="Gunakan contoh praktis.",
        max_fix_attempts=0,
    )

    kwargs = mock_llm.execute_prompt.await_args.kwargs

    assert kwargs["prompt_name"] == service.PROMPT_NAME
    assert kwargs["version"] == service.PROMPT_VERSION
    assert kwargs["variables"]["additional_prompt"] == "Gunakan contoh praktis."
    assert kwargs["variables"]["validation_feedback"] == ""
    assert "week_context" in kwargs["variables"]
    assert kwargs["output_schema"] == service.CONTENT_OUTPUT_SCHEMA


@pytest.mark.asyncio
async def test_generate_week_content_emits_events(
    week_context,
    valid_output,
    mock_llm,
):
    mock_llm.execute_prompt.return_value = llm_result(valid_output)

    await service._generate_week_content(
        week_context,
        max_fix_attempts=0,
    )

    emitted_events = [
        call.args[1]
        for call in service.emit.await_args_list
    ]

    assert service.ContentEvent.GENERATION_STARTED in emitted_events
    assert service.ContentEvent.CONTEXT_BUILT in emitted_events
    assert service.ContentEvent.LLM_CALLING in emitted_events
    assert service.ContentEvent.LLM_RESPONDED in emitted_events
    assert service.ContentEvent.VALIDATING in emitted_events
    assert service.ContentEvent.GENERATION_COMPLETED in emitted_events


@pytest.mark.asyncio
async def test_generate_week_content_records_success_trace(
    week_context,
    valid_output,
    mock_llm,
):
    mock_llm.execute_prompt.return_value = llm_result(valid_output)

    await service._generate_week_content(
        week_context,
        max_fix_attempts=0,
    )

    service.trace.assert_awaited_once()

    trace_kwargs = service.trace.await_args.kwargs

    assert trace_kwargs["validation"] == "success"
    assert trace_kwargs["reason_code"] is None
    assert trace_kwargs["model"] == "gpt-4o-mini"
    assert trace_kwargs["tokens_input"] == 100
    assert trace_kwargs["tokens_output"] == 50


# ============================================================
# 2. INPUT CONFIGURATION
# ============================================================

@pytest.mark.asyncio
async def test_generate_week_content_rejects_negative_retry(
    week_context,
):
    with pytest.raises(ValueError, match="tidak boleh negatif"):
        await service._generate_week_content(
            week_context,
            max_fix_attempts=-1,
        )


# ============================================================
# 3. JSON VALIDATION AND RETRY
# ============================================================

@pytest.mark.asyncio
async def test_generate_week_content_retries_invalid_json(
    week_context,
    valid_output,
    mock_llm,
    monkeypatch,
):
    mock_llm.execute_prompt.side_effect = [
        llm_result("{invalid json"),
        llm_result(valid_output),
    ]

    monkeypatch.setattr(
        service,
        "build_feedback",
        MagicMock(return_value="Perbaiki JSON."),
    )

    result = await service._generate_week_content(
        week_context,
        max_fix_attempts=1,
    )

    assert isinstance(result, service.GeneratedLearningMaterial)
    assert mock_llm.execute_prompt.await_count == 2

    second_call = mock_llm.execute_prompt.await_args_list[1]
    assert second_call.kwargs["variables"]["validation_feedback"] == "Perbaiki JSON."


@pytest.mark.asyncio
async def test_generate_week_content_retries_schema_validation_error(
    week_context,
    valid_output,
    mock_llm,
    monkeypatch,
):
    mock_llm.execute_prompt.side_effect = [
        llm_result({"invalid_field": "invalid"}),
        llm_result(valid_output),
    ]

    monkeypatch.setattr(
        service,
        "build_feedback",
        MagicMock(return_value="Perbaiki struktur output."),
    )

    result = await service._generate_week_content(
        week_context,
        max_fix_attempts=1,
    )

    assert isinstance(result, service.GeneratedLearningMaterial)
    assert mock_llm.execute_prompt.await_count == 2

    first_trace = service.trace.await_args_list[0].kwargs
    assert first_trace["validation"] == "failed"
    assert first_trace["reason_code"] == "SCHEMA_VALIDATION_FAILED"


@pytest.mark.asyncio
async def test_generate_week_content_fails_after_max_retries(
    week_context,
    mock_llm,
):
    mock_llm.execute_prompt.return_value = llm_result(
        {"invalid_field": "invalid"}
    )

    with pytest.raises(service.ContentGenerationError) as exc_info:
        await service._generate_week_content(
            week_context,
            max_fix_attempts=2,
        )

    error = exc_info.value

    assert error.attempts == 3
    assert error.reason_code == "SCHEMA_VALIDATION_FAILED"
    assert len(error.details) > 0
    assert mock_llm.execute_prompt.await_count == 3


@pytest.mark.asyncio
async def test_generate_week_content_does_not_retry_after_final_attempt(
    week_context,
    mock_llm,
):
    mock_llm.execute_prompt.return_value = llm_result(
        {"invalid_field": "invalid"}
    )

    with pytest.raises(service.ContentGenerationError):
        await service._generate_week_content(
            week_context,
            max_fix_attempts=0,
        )

    assert mock_llm.execute_prompt.await_count == 1

    emitted_events = [
        call.args[1]
        for call in service.emit.await_args_list
    ]

    assert service.ContentEvent.RETRY_FIX not in emitted_events
    assert service.ContentEvent.GENERATION_FAILED in emitted_events


# ============================================================
# 4. PROVIDER ERROR
# ============================================================

@pytest.mark.asyncio
async def test_generate_week_content_provider_error(
    week_context,
    mock_llm,
    monkeypatch,
):
    provider_error = TimeoutError("Provider timeout")

    mock_llm.execute_prompt.side_effect = provider_error

    monkeypatch.setattr(
        service,
        "classify_provider_error",
        MagicMock(
            return_value=(
                "LLM_TIMEOUT",
                "Layanan model tidak merespons tepat waktu.",
            )
        ),
    )

    with pytest.raises(service.ContentGenerationError) as exc_info:
        await service._generate_week_content(
            week_context,
            max_fix_attempts=3,
        )

    error = exc_info.value

    assert error.reason_code == "LLM_TIMEOUT"
    assert error.attempts == 1
    assert error.__cause__ is provider_error

    assert mock_llm.execute_prompt.await_count == 1


@pytest.mark.asyncio
async def test_generate_week_content_records_provider_error_trace(
    week_context,
    mock_llm,
    monkeypatch,
):
    mock_llm.execute_prompt.side_effect = RuntimeError("Provider failed")

    monkeypatch.setattr(
        service,
        "classify_provider_error",
        MagicMock(
            return_value=("LLM_PROVIDER_ERROR", "Provider error.")
        ),
    )

    with pytest.raises(service.ContentGenerationError):
        await service._generate_week_content(
            week_context,
            max_fix_attempts=2,
        )

    trace_kwargs = service.trace.await_args.kwargs

    assert trace_kwargs["validation"] == "provider_error"
    assert trace_kwargs["reason_code"] == "LLM_PROVIDER_ERROR"


# ============================================================
# 5. WORKFLOW EVENT AND TRACE CALLBACKS
# ============================================================

@pytest.mark.asyncio
async def test_generate_week_content_forwards_emit_event(
    week_context,
    valid_output,
    mock_llm,
):
    mock_llm.execute_prompt.return_value = llm_result(valid_output)

    callback = AsyncMock()

    await service._generate_week_content(
        week_context,
        max_fix_attempts=0,
        emit_event=callback,
    )

    callback.assert_awaited()

    event_names = [
        call.args[0]
        for call in callback.await_args_list
    ]

    assert service.ContentEvent.GENERATION_STARTED in event_names
    assert service.ContentEvent.GENERATION_COMPLETED in event_names


@pytest.mark.asyncio
async def test_generate_week_content_forwards_record_trace(
    week_context,
    valid_output,
    mock_llm,
):
    mock_llm.execute_prompt.return_value = llm_result(valid_output)

    callback = AsyncMock()

    await service._generate_week_content(
        week_context,
        max_fix_attempts=0,
        record_trace=callback,
    )

    callback.assert_awaited_once()

    trace_kwargs = callback.await_args.kwargs

    assert trace_kwargs["validation"] == "success"
    assert trace_kwargs["prompt"] == "content_generation/v1"


# ============================================================
# 6. DATABASE CONTEXT
# ============================================================

@pytest.mark.asyncio
async def test_generate_week_content_loads_context_from_repository(
    week_context,
    valid_output,
    mock_llm,
    monkeypatch,
):
    data = MagicMock()

    repository_mock = AsyncMock(return_value=data)

    monkeypatch.setattr(
        service.ContentGenerationRepository,
        "get_context",
        repository_mock,
    )

    monkeypatch.setattr(
        service,
        "_build_week_contexts",
        MagicMock(return_value=[week_context]),
    )

    mock_llm.execute_prompt.return_value = llm_result(valid_output)

    db = MagicMock()

    result = await service.generate_week_content(
        db=db,
        course_id="course-123",
        week_number=1,
        max_fix_attempts=0,
    )

    assert isinstance(result, service.GeneratedLearningMaterial)

    repository_mock.assert_awaited_once_with(
        db=db,
        course_id="course-123",
    )


@pytest.mark.asyncio
async def test_generate_week_content_raises_when_week_not_found(
    monkeypatch,
):
    repository_mock = AsyncMock(return_value=MagicMock())

    monkeypatch.setattr(
        service.ContentGenerationRepository,
        "get_context",
        repository_mock,
    )

    monkeypatch.setattr(
        service,
        "_build_week_contexts",
        MagicMock(return_value=[]),
    )

    with pytest.raises(
        service.ContentGenerationError,
        match="belum memiliki data minggu",
    ):
        await service.generate_week_content(
            db=MagicMock(),
            course_id="course-123",
            week_number=1,
        )


# ============================================================
# 7. GENERATE ALL WEEKS
# ============================================================

@pytest.mark.asyncio
async def test_generate_contents_processes_all_weeks(monkeypatch):
    week_1 = MagicMock()
    week_1.week = 1

    week_2 = MagicMock()
    week_2.week = 2

    repository_mock = AsyncMock(return_value=MagicMock())

    monkeypatch.setattr(
        service.ContentGenerationRepository,
        "get_context",
        repository_mock,
    )

    monkeypatch.setattr(
        service,
        "_build_week_contexts",
        MagicMock(return_value=[week_1, week_2]),
    )

    material = MagicMock(spec=service.GeneratedLearningMaterial)

    generate_mock = AsyncMock(return_value=material)

    monkeypatch.setattr(
        service,
        "generate_week_content",
        generate_mock,
    )

    results = await service.generate_contents(
        db=MagicMock(),
        course_id="course-123",
        concurrency=2,
    )

    assert len(results) == 2
    assert all(result.material == material for result in results)
    assert all(result.error is None for result in results)
    assert generate_mock.await_count == 2


@pytest.mark.asyncio
async def test_generate_contents_captures_week_generation_error(
    monkeypatch,
):
    week_1 = MagicMock()
    week_1.week = 1

    error = service.ContentGenerationError(
        "Generation failed",
        reason_code="LLM_TIMEOUT",
        attempts=1,
    )

    repository_mock = AsyncMock(return_value=MagicMock())

    monkeypatch.setattr(
        service.ContentGenerationRepository,
        "get_context",
        repository_mock,
    )

    monkeypatch.setattr(
        service,
        "_build_week_contexts",
        MagicMock(return_value=[week_1]),
    )

    monkeypatch.setattr(
        service,
        "generate_week_content",
        AsyncMock(side_effect=error),
    )

    results = await service.generate_contents(
        db=MagicMock(),
        course_id="course-123",
    )

    assert len(results) == 1
    assert results[0].material is None
    assert results[0].error is error


@pytest.mark.asyncio
async def test_generate_contents_rejects_invalid_concurrency():
    with pytest.raises(ValueError, match="concurrency minimal 1"):
        await service.generate_contents(
            db=MagicMock(),
            course_id="course-123",
            concurrency=0,
        )


# ============================================================
# 8. EMPTY COURSE PLAN
# ============================================================

def test_build_week_contexts_rejects_empty_weeks():
    data = SimpleNamespace(
        course_plan=SimpleNamespace(weeks=[]),
    )

    with pytest.raises(
        service.ContentGenerationError,
        match="belum memiliki data minggu",
    ):
        service._build_week_contexts(data)
