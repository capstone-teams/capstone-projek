"""Test model dan repository workflow (BE-11.1).

Membuktikan acceptance criteria BE-11.1: workflow dan event dapat dibuat serta
dibaca kembali, status/enum tersimpan apa adanya, dan query selalu dibatasi
pemiliknya (dasar scoping endpoint monitoring BE-11.3).

Database memakai PostgreSQL pada fixture :func:`conftest.db_session`; konverter
dan penyimpanan RPS diganti stub karena test ini tidak menjalankan Docling.
"""

from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio
import shortuuid

from src.models.workflow import WorkflowStatus
from src.models.workflow_event import EventType
from src.services.auth import hash_password
from src.services.rps.converter import DocumentConversion, DocumentConverter
from src.services.rps.service import RPSService
from src.services.rps.storage import LocalDocumentStorage
from src.services.user import UserRole, UserService
from src.services.workflow.domain import (
    WorkflowEventRecord,
    WorkflowRecord,
    api_status,
    stage_name,
)
from src.services.workflow.errors import WorkflowNotFoundError, WorkflowValidationError
from src.services.workflow.repository import WorkflowRepository

PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"
PASSWORD = "SecretPassword123"


class UnusedConverter(DocumentConverter):
    """Konverter yang tidak pernah dipakai test ini (hanya unggah RPS)."""

    name = "unused"

    @property
    def version(self) -> str:
        return "unused-1"

    async def convert(self, *, content: bytes, file_name: str) -> DocumentConversion:
        raise AssertionError("repository test tidak boleh mengonversi dokumen")


async def _create_instructor(session, label: str) -> str:
    suffix = shortuuid.uuid()[:10].lower()
    user = await UserService.from_session(session).create_user(
        username=f"{label}{suffix}",
        firstname="Dosen",
        lastname="Uji",
        email=f"{label}-{suffix}@itk.ac.id",
        role=UserRole.INSTRUCTOR,
        password=hash_password(PASSWORD),
    )
    return user.id or ""


@pytest_asyncio.fixture
async def owner_id(db_session) -> str:
    return await _create_instructor(db_session, "wf")


@pytest_asyncio.fixture
async def other_owner_id(db_session) -> str:
    return await _create_instructor(db_session, "other")


@pytest_asyncio.fixture
async def rps_id(db_session, owner_id, tmp_path) -> str:
    """RPS milik ``owner_id``; workflow memiliki foreign key ke baris ini."""
    service = RPSService.from_session(
        db_session,
        storage=LocalDocumentStorage(tmp_path),
        converter=UnusedConverter(),
    )
    uploaded = await service.upload_rps(
        owner_id=owner_id, file_name="rps.pdf", content=PDF_BYTES
    )
    return uploaded.document.id or ""


@pytest.mark.asyncio
async def test_workflow_is_created_and_read_back(db_session, owner_id, rps_id):
    repository = WorkflowRepository(db_session)
    created = await repository.create(
        WorkflowRecord.create(
            owner_id=owner_id,
            rps_id=rps_id,
            progress_total=2,
            model_name="model-uji",
        )
    )

    assert len(created.id or "") == 22
    assert created.status is WorkflowStatus.QUEUED
    assert created.moodle_course_id is None
    assert created.progress_total == 2

    loaded = await repository.find_by_id_and_owner(created.id or "", owner_id)
    assert loaded is not None
    assert loaded.rps_id == rps_id
    assert loaded.model_name == "model-uji"
    assert loaded.created_at is not None


@pytest.mark.asyncio
async def test_status_and_progress_updates_are_persisted(db_session, owner_id, rps_id):
    repository = WorkflowRepository(db_session)
    workflow = await repository.create(
        WorkflowRecord.create(owner_id=owner_id, rps_id=rps_id, progress_total=2)
    )

    workflow.begin_run(total=2, model_name="model-uji")
    workflow.enter_stage(WorkflowStatus.PROCESSING_RPS)
    workflow.complete_stage()
    updated = await repository.update(workflow)

    assert updated is not None
    assert updated.status is WorkflowStatus.PROCESSING_RPS
    assert updated.progress_completed == 1
    assert updated.started_at is not None

    updated.complete_run()
    final = await repository.update(updated)
    assert final is not None
    assert final.status is WorkflowStatus.COMPLETED
    assert final.completed_at is not None


@pytest.mark.asyncio
async def test_workflows_are_scoped_to_their_owner(db_session, owner_id, other_owner_id, rps_id):
    repository = WorkflowRepository(db_session)
    workflow = await repository.create(
        WorkflowRecord.create(owner_id=owner_id, rps_id=rps_id)
    )

    assert await repository.find_by_id_and_owner(workflow.id or "", other_owner_id) is None
    assert await repository.list_by_owner(other_owner_id) == []
    assert [item.id for item in await repository.list_by_owner(owner_id)] == [workflow.id]


@pytest.mark.asyncio
async def test_events_are_created_and_read_oldest_first(db_session, owner_id, rps_id):
    repository = WorkflowRepository(db_session)
    workflow = await repository.create(
        WorkflowRecord.create(owner_id=owner_id, rps_id=rps_id)
    )

    for event in (
        WorkflowEventRecord(
            workflow_id=workflow.id or "",
            event_type=EventType.PERUBAHAN_TAHAP,
            event="WORKFLOW_STARTED",
            metadata_={"progress_completed": 0, "progress_total": 2},
        ),
        WorkflowEventRecord(
            workflow_id=workflow.id or "",
            event_type=EventType.PERUBAHAN_TAHAP,
            event="WORKFLOW_STAGE_STARTED",
            stage="rps_processing",
        ),
        WorkflowEventRecord(
            workflow_id=workflow.id or "",
            event_type=EventType.AKTIVITAS_AGENT,
            event="WORKFLOW_STAGE_PROGRESS",
            stage="rps_processing",
            message="Membaca dokumen",
        ),
    ):
        stored = await repository.create_event(event)
        assert stored.id is not None
        assert stored.created_at is not None
        # Waktu event dibuat per commit; jeda kecil menjaga urutannya jelas pada
        # test tanpa bergantung pada resolusi jam sistem.
        await asyncio.sleep(0.01)

    events = await repository.list_events(workflow.id or "")
    assert [event.event for event in events] == [
        "WORKFLOW_STARTED",
        "WORKFLOW_STAGE_STARTED",
        "WORKFLOW_STAGE_PROGRESS",
    ]
    assert events[0].metadata_ == {"progress_completed": 0, "progress_total": 2}
    assert events[2].message == "Membaca dokumen"


def test_event_name_must_follow_the_public_workflow_pattern():
    with pytest.raises(WorkflowValidationError):
        WorkflowEventRecord(
            workflow_id="q7RtYx2bM8sLdWfZaKp3nQ",
            event_type=EventType.ERROR_FAILURE,
            event="error_failure",
        )


def test_api_status_and_stage_come_from_the_internal_state_machine():
    assert api_status(WorkflowStatus.QUEUED) == "QUEUED"
    assert api_status(WorkflowStatus.ANALYZING_RPS) == "RUNNING"
    assert stage_name(WorkflowStatus.ANALYZING_RPS) == "rps_analysis"
    assert stage_name(WorkflowStatus.COMPLETED) is None
    assert api_status(WorkflowStatus.FAILED) == "FAILED"


def test_not_found_error_is_raised_for_unknown_ids():
    error = WorkflowNotFoundError("abc")
    assert error.status_code == 404
    assert error.error_code == "RESOURCE_NOT_FOUND"
