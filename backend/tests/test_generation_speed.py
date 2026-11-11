"""Percepatan proses: generation paralel per minggu, ilustrasi paralel, dan cegah analisis ganda."""

import asyncio
from types import SimpleNamespace

import pytest

from src.services.content.generation import ContentGenerationService, _LockedSession
from src.services.content.pipeline import classify_provider_error
from src.services.llm.base import (
    LLMConfigurationError,
    LLMInvalidOutputError,
    LLMRetryExhaustedError,
    LLMTimeoutError,
)
from src.services.rps.service import RPSService


@pytest.mark.asyncio
async def test_weeks_are_generated_concurrently_and_returned_in_week_order(monkeypatch):
    monkeypatch.setenv("CONTENT_GENERATION_CONCURRENCY", "3")
    from src.config.settings import get_settings

    get_settings.cache_clear()
    service = ContentGenerationService.__new__(ContentGenerationService)
    running = 0
    peak = 0

    async def fake_week(prepared, week, targets, *, emit_event, db_lock):
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(0.02)
        running -= 1
        return [f"minggu-{week}"]

    service._generate_week = fake_week
    prepared = SimpleNamespace(targets=[SimpleNamespace(ctx=SimpleNamespace(week_number=w)) for w in (4, 1, 5, 2, 3)])
    try:
        outcomes = await service.generate(None, prepared, emit_event=None)
    finally:
        get_settings.cache_clear()
    assert outcomes == ["minggu-1", "minggu-2", "minggu-3", "minggu-4", "minggu-5"]
    assert peak == 3


@pytest.mark.asyncio
async def test_locked_session_serializes_database_access():
    active = 0
    overlap = False

    class Session:
        bind = "engine"

        async def execute(self, statement):
            nonlocal active, overlap
            active += 1
            overlap = overlap or active > 1
            await asyncio.sleep(0.01)
            active -= 1
            return statement

    locked = _LockedSession(Session(), asyncio.Lock())
    assert await asyncio.gather(*(locked.execute(n) for n in range(4))) == [0, 1, 2, 3]
    assert not overlap
    assert locked.bind == "engine"


def test_provider_errors_explain_the_cause():
    exhausted = LLMRetryExhaustedError("habis")
    exhausted.last_error = LLMTimeoutError("lambat")
    assert classify_provider_error(exhausted)[0] == "PROVIDER_TIMEOUT"
    assert classify_provider_error(LLMConfigurationError("no key"))[0] == "PROVIDER_NOT_CONFIGURED"
    code, message = classify_provider_error(LLMInvalidOutputError("x"))
    assert code == "PROVIDER_INVALID_OUTPUT" and "terpotong" in message
    assert classify_provider_error(ValueError("lain"))[0] == "PROVIDER_ERROR"


def test_analysis_in_progress_respects_the_processing_lease():
    service = RPSService.__new__(RPSService)
    running = SimpleNamespace(is_analyzing=True, _is_stale=lambda **kwargs: False)
    abandoned = SimpleNamespace(is_analyzing=True, _is_stale=lambda **kwargs: True)
    idle = SimpleNamespace(is_analyzing=False, _is_stale=lambda **kwargs: False)
    assert service.analysis_in_progress(running)
    assert not service.analysis_in_progress(abandoned)
    assert not service.analysis_in_progress(idle)
