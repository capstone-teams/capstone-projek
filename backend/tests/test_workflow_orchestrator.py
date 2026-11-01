"""Test orkestrator workflow RPS (BE-11.2).

Membuktikan acceptance criteria BE-11.2 tanpa Docling maupun LLM:

- satu workflow melewati ``PROCESSING_RPS`` → ``ANALYZING_RPS`` sampai hasil
  analisis tersimpan (status ``ANALYZED``);
- setiap perubahan tahap, aktivitas agent, retry, dan kegagalan tercatat sebagai
  ``WorkflowEvent``;
- kegagalan tahap menghasilkan workflow ``FAILED`` (satu event kegagalan);
- reanalyze memakai workflow yang sama dan menambahkan event baru.

Runner dijalankan langsung (bukan lewat HTTP) dengan session factory, storage,
konverter, dan analyzer palsu — persis pola ``test_rps_runner.py``.
"""

from __future__ import annotations

from typing import Any

import pytest
import pytest_asyncio
import shortuuid

from src.schemas.rps_structured import RPSStructuredData
from src.services.analysis.service import RPSEvent
from src.services.auth import hash_password
from src.services.rps.converter import (
    ConvertedTable,
    DocumentConversion,
    DocumentConverter,
)
from src.services.rps.errors import RPSAnalysisFailedError, DocumentConversionError
from src.services.rps.service import RPSService
from src.services.rps.storage import LocalDocumentStorage
from src.services.user import UserRole, UserService
from src.services.workflow.broker import WorkflowEventBroker
from src.services.workflow.domain import WorkflowRecord
from src.services.workflow.orchestrator import (
    run_rps_analysis_workflow,
    run_rps_processing_workflow,
)
from src.services.workflow.service import WorkflowService

PASSWORD = "SecretPassword123"
PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"

SOURCE_DOCUMENT = {
    "schema_name": "DoclingDocument",
    "pages": {"1": {"page_no": 1}},
    "texts": [{"label": "section_header", "text": "CPMK", "prov": [{"page_no": 1}]}],
    "tables": [
        {
            "label": "table",
            "prov": [{"page_no": 1}],
            "data": {"num_rows": 2, "num_cols": 2},
        }
    ],
}

ANALYSIS_DATA: dict[str, Any] = {
    "course": {"name": "Basis Data", "code": "IF123", "credits": 3},
    "cpmk": [{"id": "CPMK-1", "description": "Merancang basis data relasional"}],
    "weeks": [{"week": 1, "topics": ["Pengenalan Basis Data"]}],
}


class StubConverter(DocumentConverter):
    name = "stub"

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    @property
    def version(self) -> str:
        return "stub-1"

    async def convert(self, *, content: bytes, file_name: str) -> DocumentConversion:
        self.calls += 1
        if self.fail:
            raise DocumentConversionError(
                "detail internal", public_reason="Dokumen tidak dapat dibaca."
            )
        return DocumentConversion(
            document_json=SOURCE_DOCUMENT,
            tables=[ConvertedTable(index=0, page=1, cells=[["a"]])],
            converter_name=self.name,
            converter_version=self.version,
        )


class StubAnalyzer:
    """Analyzer palsu yang dapat memancarkan event retry/kegagalan."""

    def __init__(self, *, retry: bool = False, fail: bool = False) -> None:
        self.retry = retry
        self.fail = fail
        self.calls = 0

    async def __call__(self, rps_yaml: str, *, emit_event=None):
        self.calls += 1
        if self.retry and emit_event is not None:
            await emit_event(
                event_type=RPSEvent.RETRY_FIX,
                message="Hasil model tidak sesuai schema, memperbaiki.",
                attempt=1,
                reason_code="SCHEMA_VALIDATION_FAILED",
                details=[],
            )
        if self.fail:
            if emit_event is not None:
                await emit_event(
                    event_type=RPSEvent.ANALYSIS_FAILED,
                    message="Hasil model tidak sesuai schema.",
                    attempt=2,
                    reason_code="SCHEMA_VALIDATION_FAILED",
                )
            raise RPSAnalysisFailedError(
                "stub sengaja gagal",
                public_reason="Hasil model tidak sesuai schema.",
            )
        return RPSStructuredData.model_validate(ANALYSIS_DATA)


class _SessionScope:
    def __init__(self, session) -> None:
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *exc_info) -> bool:
        return False


class FixedSessionFactory:
    """Session factory palsu yang selalu menyerahkan session milik test."""

    def __init__(self, session) -> None:
        self._session = session

    def __call__(self) -> _SessionScope:
        return _SessionScope(self._session)


@pytest_asyncio.fixture
async def owner_id(db_session) -> str:
    suffix = shortuuid.uuid()[:10].lower()
    user = await UserService.from_session(db_session).create_user(
        username=f"orch{suffix}",
        firstname="Dosen",
        lastname="Uji",
        email=f"orch-{suffix}@itk.ac.id",
        role=UserRole.INSTRUCTOR,
        password=hash_password(PASSWORD),
    )
    return user.id or ""


@pytest.fixture
def storage(tmp_path) -> LocalDocumentStorage:
    return LocalDocumentStorage(tmp_path)


@pytest.fixture
def converter() -> StubConverter:
    return StubConverter()


@pytest.fixture
def analyzer() -> StubAnalyzer:
    return StubAnalyzer()


@pytest.fixture
def runner_env(monkeypatch, db_session, storage, converter, analyzer):
    """Ganti seluruh I/O mahal orkestrator dengan versi palsu yang dapat diamati."""
    import src.services.rps.service as rps_service_module
    import src.services.workflow.orchestrator as orchestrator_module

    monkeypatch.setattr(
        orchestrator_module,
        "get_session_factory",
        lambda: FixedSessionFactory(db_session),
    )
    monkeypatch.setattr(
        rps_service_module, "get_document_storage", lambda: storage
    )
    monkeypatch.setattr(
        rps_service_module, "get_document_converter", lambda: converter
    )
    monkeypatch.setattr(rps_service_module, "analyze_document", analyzer)
    return {"storage": storage, "converter": converter, "analyzer": analyzer}


async def _prepare(
    db_session,
    owner_id: str,
    *,
    workflow_id: str | None = None,
    total: int = 2,
) -> WorkflowRecord:
    """Unggah RPS, buat workflow, dan tautkan keduanya (meniru route)."""
    rps_service = RPSService.from_session(db_session)
    uploaded = await rps_service.upload_rps(
        owner_id=owner_id, file_name="rps.pdf", content=PDF_BYTES
    )
    rps_id = uploaded.document.id or ""

    workflow_service = WorkflowService.from_session(
        db_session, broker=WorkflowEventBroker()
    )
    workflow = await workflow_service.create_for_rps(
        owner_id=owner_id, rps_id=rps_id, total=total, workflow_id=workflow_id
    )
    await rps_service.attach_workflow(
        rps_id=rps_id, owner_id=owner_id, workflow_id=workflow.id or ""
    )
    return workflow


async def _workflow_and_events(db_session, workflow_id: str, owner_id: str):
    service = WorkflowService.from_session(db_session)
    workflow = await service.get_workflow(workflow_id=workflow_id, owner_id=owner_id)
    events = await service.list_events(workflow_id=workflow_id, owner_id=owner_id)
    return workflow, events


@pytest.mark.asyncio
async def test_processing_workflow_runs_both_stages_and_records_events(
    db_session, owner_id, runner_env
):
    workflow = await _prepare(db_session, owner_id, total=2)

    await run_rps_processing_workflow(
        rps_id=workflow.rps_id, owner_id=workflow.owner_id
    )

    loaded, events = await _workflow_and_events(db_session, workflow.id or "", owner_id)
    names = [event.event for event in events]

    assert loaded.status.value == "COMPLETED"
    assert (loaded.progress_completed, loaded.progress_total) == (2, 2)
    assert names[0] == "WORKFLOW_STARTED"
    assert names[-1] == "WORKFLOW_COMPLETED"
    assert names.count("WORKFLOW_STAGE_STARTED") == 2
    assert names.count("WORKFLOW_STAGE_COMPLETED") == 2
    assert [event.stage for event in events if event.event == "WORKFLOW_STAGE_STARTED"] == [
        "rps_processing",
        "rps_analysis",
    ]

    rps = await RPSService.from_session(db_session).get_rps(
        rps_id=workflow.rps_id, owner_id=owner_id
    )
    assert rps.status.value == "ANALYZED"
    assert rps.workflow_id == workflow.id
    assert runner_env["converter"].calls == 1
    assert runner_env["analyzer"].calls == 1


@pytest.mark.asyncio
async def test_conversion_failure_marks_workflow_failed_with_one_error_event(
    db_session, owner_id, runner_env
):
    runner_env["converter"].fail = True
    workflow = await _prepare(db_session, owner_id, total=2)

    await run_rps_processing_workflow(
        rps_id=workflow.rps_id, owner_id=workflow.owner_id
    )

    loaded, events = await _workflow_and_events(db_session, workflow.id or "", owner_id)
    failures = [event for event in events if event.event == "WORKFLOW_FAILED"]

    assert loaded.status.value == "FAILED"
    assert loaded.progress_completed == 0
    assert len(failures) == 1
    assert failures[0].event_type.value == "ERROR_FAILURE"
    assert failures[0].stage == "rps_processing"
    assert failures[0].message == "Dokumen tidak dapat dibaca."

    rps = await RPSService.from_session(db_session).get_rps(
        rps_id=workflow.rps_id, owner_id=owner_id
    )
    assert rps.status.value == "FAILED"
    assert rps.processing_error_code == "RPS_PROCESSING_FAILED"


@pytest.mark.asyncio
async def test_analysis_retry_is_recorded_and_workflow_completes(
    db_session, owner_id, runner_env
):
    runner_env["analyzer"].retry = True
    workflow = await _prepare(db_session, owner_id, total=2)

    await run_rps_processing_workflow(
        rps_id=workflow.rps_id, owner_id=workflow.owner_id
    )

    loaded, events = await _workflow_and_events(db_session, workflow.id or "", owner_id)
    retries = [event for event in events if event.event == "WORKFLOW_RETRY"]

    assert loaded.status.value == "COMPLETED"
    assert len(retries) == 1
    assert retries[0].event_type.value == "RETRY_FIX"
    assert retries[0].stage == "rps_analysis"
    assert retries[0].metadata_["reason_code"] == "SCHEMA_VALIDATION_FAILED"


@pytest.mark.asyncio
async def test_analysis_failure_does_not_duplicate_the_failure_event(
    db_session, owner_id, runner_env
):
    runner_env["analyzer"].fail = True
    workflow = await _prepare(db_session, owner_id, total=2)

    await run_rps_processing_workflow(
        rps_id=workflow.rps_id, owner_id=workflow.owner_id
    )

    loaded, events = await _workflow_and_events(db_session, workflow.id or "", owner_id)
    failures = [event for event in events if event.event == "WORKFLOW_FAILED"]

    assert loaded.status.value == "FAILED"
    assert len(failures) == 1
    assert failures[0].stage == "rps_analysis"

    rps = await RPSService.from_session(db_session).get_rps(
        rps_id=workflow.rps_id, owner_id=owner_id
    )
    assert rps.status.value == "FAILED"
    assert rps.processing_error_code == "LLM_GENERATION_FAILED"


@pytest.mark.asyncio
async def test_reanalyze_reuses_the_workflow_and_appends_events(
    db_session, owner_id, runner_env
):
    workflow = await _prepare(db_session, owner_id, total=2)
    await run_rps_processing_workflow(
        rps_id=workflow.rps_id, owner_id=workflow.owner_id
    )
    _, first_events = await _workflow_and_events(
        db_session, workflow.id or "", owner_id
    )

    rps_service = RPSService.from_session(db_session)
    await rps_service.begin_analysis(
        rps_id=workflow.rps_id,
        owner_id=owner_id,
        force=True,
        workflow_id=workflow.id or "",
    )
    await run_rps_analysis_workflow(
        rps_id=workflow.rps_id, owner_id=workflow.owner_id
    )

    loaded, events = await _workflow_and_events(db_session, workflow.id or "", owner_id)

    assert loaded.status.value == "COMPLETED"
    assert (loaded.progress_completed, loaded.progress_total) == (1, 1)
    assert len(events) > len(first_events)
    assert events[len(first_events)].event == "WORKFLOW_STARTED"
    assert events[-1].event == "WORKFLOW_COMPLETED"
    assert runner_env["analyzer"].calls == 2
