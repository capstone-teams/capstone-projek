"""Test RPS Analysis Service (BE-09.2).

Membutuhkan: pytest, pytest-asyncio.
Sesuaikan `MODULE` dengan lokasi service di proyek.

Test `test_valid_for_sample_rps` memakai model Pydantic asli dan fixture
`tests/fixtures/rps_sample_output.json` (taruh JSON hasil yang sudah benar,
mis. hasil RPS Matematika Diskrit). Dilewati jika file tidak ada.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

import src.services.analysis.service as mod  # sesuaikan path
from src.services.analysis.service import RPSAnalysisError, analyze_rps

VALID_YAML = """
course:
  name: Contoh
cpmk: []
weekly_plan:
  - weeks: [1]
  - weeks: [2]
assessments:
  - component: UAS
    weight_percent: 100
"""

VALID = {"name": "x", "count": 1}
INVALID = {"name": "SECRET-VALUE"}  # field `count` hilang


class _Stub(BaseModel):
    name: str
    count: int


@pytest.fixture
def llm(monkeypatch):
    state = SimpleNamespace(responses=[], calls=[])

    class FakeService:
        async def execute_prompt(self, **kwargs):
            state.calls.append(kwargs)
            item = state.responses.pop(0)
            if isinstance(item, Exception):
                raise item
            return SimpleNamespace(
                data=item, model="gpt-4o-mini", input_tokens=100, output_tokens=50
            )

    monkeypatch.setattr(mod, "LLMService", FakeService)
    monkeypatch.setattr(mod, "OpenAIProvider", lambda: object())
    monkeypatch.setattr(mod, "RPSStructuredData", _Stub)
    return state


@pytest.fixture
def events():
    log = []

    async def emit(**kwargs):
        log.append(kwargs)

    emit.log = log
    emit.types = lambda: [e["event_type"] for e in log]
    return emit


@pytest.fixture
def traces():
    log = []

    async def record(**kwargs):
        log.append(kwargs)

    record.log = log
    return record


@pytest.mark.asyncio
async def test_success_first_attempt(llm, events, traces):
    llm.responses = [VALID]
    result = await analyze_rps(
        VALID_YAML, max_fix_attempts=2, emit_event=events, record_trace=traces
    )

    assert result.name == "x"
    assert len(llm.calls) == 1
    assert events.types() == [
        "ANALYSIS_STARTED",
        "YAML_PARSING",
        "YAML_PARSED",
        "LLM_CALLING",
        "LLM_RESPONDED",
        "VALIDATING",
        "ANALYSIS_COMPLETED",
    ]
    assert "2 minggu" in events.log[2]["message"]
    assert traces.log[0]["validation"] == "success"
    assert traces.log[0]["prompt"] == "rps_analysis/v1"
    assert traces.log[0]["model"] == "gpt-4o-mini"
    assert traces.log[0]["tokens_input"] == 100


@pytest.mark.asyncio
async def test_invalid_output_triggers_retry_with_feedback(llm, events, traces):
    llm.responses = [INVALID, VALID]
    result = await analyze_rps(
        VALID_YAML, max_fix_attempts=2, emit_event=events, record_trace=traces
    )

    assert result.count == 1
    assert len(llm.calls) == 2
    # percobaan 1 tanpa feedback, percobaan 2 membawa pesan error
    assert llm.calls[0]["variables"]["validation_feedback"] == ""
    assert "count" in llm.calls[1]["variables"]["validation_feedback"]
    # event RETRY_FIX tercatat tepat sekali, di antara dua panggilan LLM
    assert events.types().count("RETRY_FIX") == 1
    retry = next(e for e in events.log if e["event_type"] == "RETRY_FIX")
    assert retry["reason_code"] == "SCHEMA_VALIDATION_FAILED"
    # jejak: gagal lalu sukses
    assert [t["validation"] for t in traces.log] == ["failed", "success"]
    assert [t["attempt"] for t in traces.log] == [1, 2]


@pytest.mark.asyncio
async def test_event_details_do_not_leak_input_values(llm, events):
    llm.responses = [INVALID, VALID]
    await analyze_rps(VALID_YAML, max_fix_attempts=1, emit_event=events)

    assert "SECRET-VALUE" not in json.dumps(events.log)


@pytest.mark.asyncio
async def test_fails_after_retry_limit(llm, events, traces):
    llm.responses = [INVALID, INVALID, INVALID]
    with pytest.raises(RPSAnalysisError) as exc_info:
        await analyze_rps(
            VALID_YAML, max_fix_attempts=2, emit_event=events, record_trace=traces
        )

    err = exc_info.value
    assert err.code == "LLM_GENERATION_FAILED"
    assert err.reason_code == "SCHEMA_VALIDATION_FAILED"
    assert err.attempts == 3
    assert len(llm.calls) == 3
    assert events.types().count("RETRY_FIX") == 2  # tidak ada retry setelah percobaan terakhir
    assert events.types()[-1] == "ANALYSIS_FAILED"
    assert [t["validation"] for t in traces.log] == ["failed"] * 3


@pytest.mark.asyncio
async def test_zero_retries_means_single_attempt(llm):
    llm.responses = [INVALID]
    with pytest.raises(RPSAnalysisError):
        await analyze_rps(VALID_YAML, max_fix_attempts=0)
    assert len(llm.calls) == 1


@pytest.mark.asyncio
async def test_retry_limit_is_configurable(llm, monkeypatch):
    # `Settings` (pydantic) menolak setattr atribut yang tidak dideklarasikan,
    # jadi ganti objek settings di modul dengan objek sederhana.
    monkeypatch.setattr(
        mod, "settings", SimpleNamespace(rps_analysis_max_fix_attempts=1)
    )
    llm.responses = [INVALID, INVALID]
    with pytest.raises(RPSAnalysisError):
        await analyze_rps(VALID_YAML)  # tanpa argumen -> dari konfigurasi
    assert len(llm.calls) == 2


@pytest.mark.asyncio
async def test_output_not_json_is_retried(llm, events):
    llm.responses = ["bukan json {", VALID]
    result = await analyze_rps(VALID_YAML, max_fix_attempts=1, emit_event=events)

    assert result.name == "x"
    retry = next(e for e in events.log if e["event_type"] == "RETRY_FIX")
    assert retry["reason_code"] == "OUTPUT_NOT_JSON"


@pytest.mark.asyncio
async def test_json_string_output_is_accepted(llm):
    llm.responses = [json.dumps(VALID)]
    result = await analyze_rps(VALID_YAML, max_fix_attempts=0)
    assert result.count == 1


@pytest.mark.asyncio
async def test_provider_error_is_not_retried(llm, events, traces):
    llm.responses = [TimeoutError("timeout")]
    with pytest.raises(RPSAnalysisError) as exc_info:
        await analyze_rps(
            VALID_YAML, max_fix_attempts=2, emit_event=events, record_trace=traces
        )

    assert exc_info.value.code == "LLM_GENERATION_FAILED"
    assert exc_info.value.reason_code == "PROVIDER_TIMEOUT"
    assert len(llm.calls) == 1
    assert "RETRY_FIX" not in events.types()
    assert events.types()[-1] == "ANALYSIS_FAILED"
    assert traces.log[0]["validation"] == "provider_error"


@pytest.mark.asyncio
async def test_invalid_yaml_fails_before_llm(llm, events):
    with pytest.raises(ValueError):
        await analyze_rps("course: [unclosed", emit_event=events)

    assert llm.calls == []
    assert events.types() == ["ANALYSIS_STARTED", "YAML_PARSING", "ANALYSIS_FAILED"]
    assert events.log[-1]["reason_code"] == "YAML_INVALID"


@pytest.mark.asyncio
async def test_empty_yaml_rejected(llm):
    with pytest.raises(ValueError):
        await analyze_rps("   ")


@pytest.mark.asyncio
async def test_negative_retry_rejected(llm):
    with pytest.raises(ValueError):
        await analyze_rps(VALID_YAML, max_fix_attempts=-1)


@pytest.mark.asyncio
async def test_emit_and_trace_failures_do_not_break_analysis(llm):
    async def broken(**kwargs):
        raise RuntimeError("boom")

    llm.responses = [VALID]
    result = await analyze_rps(
        VALID_YAML, max_fix_attempts=0, emit_event=broken, record_trace=broken
    )
    assert result.name == "x"


@pytest.mark.asyncio
async def test_valid_for_sample_rps(monkeypatch):
    """Output contoh yang benar harus lolos validasi model Pydantic asli."""
    sample = Path(__file__).parent / "fixtures" / "rps_sample_output.json"
    if not sample.exists():
        pytest.skip("fixtures/rps_sample_output.json belum ada")

    payload = json.loads(sample.read_text(encoding="utf-8"))

    class FakeService:
        async def execute_prompt(self, **kwargs):
            return SimpleNamespace(
                data=payload, model="m", input_tokens=1, output_tokens=1
            )

    monkeypatch.setattr(mod, "LLMService", FakeService)
    monkeypatch.setattr(mod, "OpenAIProvider", lambda: object())

    result = await analyze_rps(VALID_YAML, max_fix_attempts=0)
    assert result.schema_version == "2.0"
