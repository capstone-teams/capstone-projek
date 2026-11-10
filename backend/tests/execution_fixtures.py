"""Helper bersama test eksekusi struktur course (BE-16.2).

Dipakai ``test_execution_structure.py`` (Moodle tiruan) dan
``test_moodle_execution_live.py`` (Moodle tim) supaya kedua test menyiapkan
workflow dan course plan dengan cara yang sama seperti alur produk: upload RPS,
workflow menunggu review, course target diset, course plan disetujui.
"""

from __future__ import annotations

from datetime import datetime, timezone

import shortuuid

from src.models.course_plan import CoursePlanStatus
from src.services.auth import hash_password
from src.services.content.domain import ApprovalStatus, ContentDraft, ContentKind
from src.services.content.repository import ContentRepository
from src.services.course_plan.domain import CoursePlanDraft, CoursePlanRecord, CoursePlanWeekRecord
from src.services.course_plan.repository import CoursePlanRepository
from src.services.execution.service import ExecutionService
from src.services.instructor.service import InstructorSetupService
from src.services.rps.converter import DocumentConversion, DocumentConverter
from src.services.rps.service import RPSService
from src.services.rps.storage import LocalDocumentStorage
from src.services.user import UserRole, UserService
from src.services.workflow.broker import WorkflowEventBroker
from src.services.workflow.domain import WorkflowRecord
from src.services.workflow.orchestrator import run_execution_workflow
from src.services.workflow.service import WorkflowService

PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"
UTS_WEEK = 8
UAS_WEEK = 16


class UnusedConverter(DocumentConverter):
    """Upload tidak mengonversi dokumen; test eksekusi tidak butuh konversi."""

    name = "unused"

    @property
    def version(self) -> str:
        return "unused-1"

    async def convert(self, *, content: bytes, file_name: str) -> DocumentConversion:
        raise AssertionError("test eksekusi tidak boleh mengonversi dokumen")


class _SessionScope:
    def __init__(self, session) -> None:
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *exc_info) -> bool:
        return False


class FixedSessionFactory:
    """Session factory yang memakai session test (tidak membuka session baru)."""

    def __init__(self, session) -> None:
        self._session = session

    def __call__(self) -> _SessionScope:
        return _SessionScope(self._session)


def semester_weeks(count: int = 16) -> tuple[CoursePlanWeekRecord, ...]:
    """Minggu course plan satu semester: UTS di minggu 8, UAS di minggu 16."""
    weeks = []
    for number in range(1, count + 1):
        if number == UTS_WEEK:
            weeks.append(CoursePlanWeekRecord(week_number=number, title="Ujian Tengah Semester", week_type="uts"))
        elif number == UAS_WEEK:
            weeks.append(CoursePlanWeekRecord(week_number=number, title="Ujian Akhir Semester", week_type="uas"))
        else:
            weeks.append(
                CoursePlanWeekRecord(
                    week_number=number,
                    title=f"Materi minggu {number}",
                    objectives=(f"Mahasiswa memahami konsep minggu {number}",),
                    topics=(f"Topik {number}.1", f"Topik {number}.2"),
                    learning_outcomes=(f"Sub-CPMK-{(number + 1) // 2}",),
                )
            )
    return tuple(weeks)


async def create_instructor(session) -> str:
    suffix = shortuuid.uuid()[:10].lower()
    user = await UserService.from_session(session).create_user(
        username=f"exec{suffix}",
        firstname="Pengguna",
        lastname="Uji",
        email=f"exec-{suffix}@itk.ac.id",
        role=UserRole.INSTRUCTOR,
        password=hash_password("SecretPassword123"),
    )
    return user.id or ""


async def prepare_structure_workflow(
    session,
    owner_id: str,
    storage: LocalDocumentStorage,
    *,
    moodle_course_id: int,
    weeks: tuple[CoursePlanWeekRecord, ...],
) -> tuple[WorkflowRecord, CoursePlanRecord]:
    """Workflow menunggu review dengan course target dan course plan ``APPROVED``."""
    rps_service = RPSService.from_session(session, storage=storage, converter=UnusedConverter())
    uploaded = await rps_service.upload_rps(owner_id=owner_id, file_name="rps.pdf", content=PDF_BYTES)
    rps_id = uploaded.document.id or ""

    workflows = WorkflowService.from_session(session, broker=WorkflowEventBroker())
    workflow = await workflows.create_for_rps(owner_id=owner_id, rps_id=rps_id, total=1)
    await rps_service.attach_workflow(rps_id=rps_id, owner_id=owner_id, workflow_id=workflow.id or "")
    started = await workflows.begin_run(workflow, total=1)
    await workflows.wait_for_review(started)
    workflow = await workflows.set_moodle_course_id(
        workflow_id=workflow.id or "", owner_id=owner_id, moodle_course_id=moodle_course_id
    )

    plans = CoursePlanRepository(session)
    plan = await plans.create(
        CoursePlanDraft(
            workflow_id=workflow.id or "",
            rps_id=rps_id,
            course={"name": "Basis Data", "code": "IF123"},
            weeks=weeks,
            plan_data={"weeks": len(weeks)},
        )
    )
    plan = await plans.set_status(plan.id, CoursePlanStatus.APPROVED, approved_at=datetime.now(timezone.utc))
    return workflow, plan


async def execute_structure(session, moodle, workflow_id: str, owner_id: str):
    """Mulai eksekusi ``STRUCTURE`` lalu jalankan di orkestrator seperti endpoint."""
    execution = await ExecutionService.from_session(session, moodle=moodle).start_structure(
        workflow_id=workflow_id, owner_id=owner_id
    )
    await run_execution_workflow(
        workflow_id=workflow_id, owner_id=owner_id, execution_id=execution.id or "", moodle=moodle
    )
    return execution.id or ""


async def retry_structure(session, moodle, workflow_id: str, owner_id: str, execution_id: str) -> None:
    """Ulangi operasi gagal pada eksekusi yang sama, seperti endpoint retry (BE-17.2)."""
    await ExecutionService.from_session(session, moodle=moodle).retry_failed(
        workflow_id=workflow_id, owner_id=owner_id, execution_id=execution_id
    )
    await run_execution_workflow(
        workflow_id=workflow_id, owner_id=owner_id, execution_id=execution_id, moodle=moodle
    )

# --- Cakupan FULL (BE-21.1): konten APPROVED dan eksekusinya -----------------


def traceability(week: int) -> dict:
    return {
        "week_number": week,
        "sub_cpmk_codes": ["Sub-CPMK-1"],
        "weekly_plan_ref": f"week-{week}",
    }


def material_data(week: int) -> dict:
    return {
        "learning_objectives": ["Mahasiswa memahami topik minggu ini"],
        "sections": [{"heading": "Pengantar", "body_markdown": "Isi **materi**."}],
        "references": [
            {"title": "MDN", "url": "https://developer.mozilla.org"},
            {"title": "Tidak aman", "url": "javascript:alert(1)"},
        ],
        "traceability": traceability(week),
    }


def resource_data(week: int, *, url: str | None = "https://example.com/artikel") -> dict:
    return {
        "url": url,
        "description": "Artikel pengantar",
        "resource_kind": "ARTICLE",
        "relevance_reason": "Mendukung topik minggu ini",
        "traceability": traceability(week),
    }


def assignment_data(week: int) -> dict:
    return {
        "instructions_markdown": "Kerjakan latihan pada modul.",
        "expected_outputs": ["Laporan"],
        "rubric": [
            {"criterion": "Ketepatan", "description": "Sesuai instruksi", "weight_percent": 100}
        ],
        "traceability": traceability(week),
    }


def quiz_data(week: int) -> dict:
    return {
        "description": "Kuis minggu ini",
        "config": {
            "time_limit_minutes": 10,
            "max_attempts": 1,
            "shuffle_questions": False,
            "passing_score_percent": 70,
        },
        "questions": [
            {
                "question_text": "Apa itu HTML?",
                "options": [
                    {"key": "A", "text": "Bahasa markup"},
                    {"key": "B", "text": "Basis data"},
                ],
                "correct_option_key": "A",
                "explanation": "HTML adalah bahasa markup.",
            }
        ],
        "traceability": traceability(week),
    }


async def approve_content(
    session,
    workflow_id: str,
    plan: CoursePlanRecord,
    kind: ContentKind,
    week_number: int,
    data: dict,
):
    """Simpan satu versi konten lalu langsung setujui (jalur review disederhanakan)."""
    week = next(item for item in plan.weeks if item.week_number == week_number)
    return await ContentRepository(session).create(
        ContentDraft(
            kind=kind,
            workflow_id=workflow_id,
            course_plan_id=plan.id,
            course_plan_week_id=week.id or "",
            week_number=week_number,
            title=f"{kind.value} minggu {week_number}",
            content_data=data,
            status=ApprovalStatus.APPROVED,
        )
    )


async def enable_all_activities(session, owner_id: str) -> None:
    """Aktifkan keempat jenis konten pada Activity Configuration dosen."""
    await InstructorSetupService.from_session(session).update_setup(
        owner_id,
        activity_changes={
            "learning_material": True,
            "learning_resource": True,
            "assignment": True,
            "quiz": True,
        },
    )


async def execute_full(session, moodle, workflow_id: str, owner_id: str) -> str:
    """Mulai eksekusi ``FULL`` lalu jalankan di orkestrator seperti endpoint."""
    execution = await ExecutionService.from_session(session, moodle=moodle).start_full(
        workflow_id=workflow_id, owner_id=owner_id
    )
    await run_execution_workflow(
        workflow_id=workflow_id, owner_id=owner_id, execution_id=execution.id or "", moodle=moodle
    )
    return execution.id or ""
