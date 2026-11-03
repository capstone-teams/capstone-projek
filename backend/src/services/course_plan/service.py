"""Operasi aplikasi course plan (BE-14.1).

Service ini menjawab "versi rencana apa yang boleh disimpan/dibaca?" — aturan
approval dan review ada di BE-14.2, sedangkan urutan tahap generasi ada di
orkestrator BE-14.3. Akses tabel berada di
:class:`~src.services.course_plan.repository.CoursePlanRepository`.

Scoping akses selalu dimulai dari workflow milik dosen yang login
(:meth:`WorkflowService.get_workflow`): workflow dosen lain menghasilkan error
yang sama dengan workflow tidak ada, sehingga keberadaan rencana dosen lain
tidak dapat ditebak dari perbedaan response.
"""

from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.course_plan import CoursePlanOutput
from src.services.course_plan.domain import (
    CoursePlanDraft,
    CoursePlanRecord,
    CoursePlanWeekRecord,
)
from src.services.course_plan.errors import (
    CoursePlanNotFoundError,
    CoursePlanStateError,
    CoursePlanValidationError,
)
from src.services.course_plan.repository import CoursePlanRepository
from src.services.workflow.domain import WorkflowRecord
from src.services.workflow.service import WorkflowService

__all__ = ["CoursePlanService"]

#: Nilai ``week_type`` yang dikenal domain (selaras ``CoursePlanWeek``).
WEEK_TYPES = ("regular", "kuis", "uts", "uas")


class CoursePlanService:
    """Operasi versi course plan di atas satu ``AsyncSession``."""

    def __init__(
        self,
        repository: CoursePlanRepository,
        *,
        workflow_service: WorkflowService,
    ) -> None:
        self._repository = repository
        self._workflows = workflow_service

    @classmethod
    def from_session(cls, session: AsyncSession) -> CoursePlanService:
        """Bangun service dengan dependency bawaan."""
        return cls(
            CoursePlanRepository(session),
            workflow_service=WorkflowService.from_session(session),
        )

    # --- Baca -------------------------------------------------------------

    async def get_latest(
        self, *, workflow_id: str, owner_id: str
    ) -> CoursePlanRecord:
        """Versi terbaru sebuah workflow; 404 bila belum ada."""
        workflow = await self._workflows.get_workflow(
            workflow_id=workflow_id, owner_id=owner_id
        )
        record = await self._repository.get_latest(workflow.id or "")
        if record is None:
            raise CoursePlanNotFoundError(workflow_id)
        return record

    async def list_versions(
        self, *, workflow_id: str, owner_id: str
    ) -> list[CoursePlanRecord]:
        """Seluruh versi (terbaru lebih dulu) milik workflow dosen ini."""
        workflow = await self._workflows.get_workflow(
            workflow_id=workflow_id, owner_id=owner_id
        )
        return await self._repository.list_versions(workflow.id or "")

    async def get_version(
        self, *, workflow_id: str, owner_id: str, version: int
    ) -> CoursePlanRecord:
        """Detail satu versi; 404 bila versinya tidak ada."""
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise CoursePlanValidationError("version", "harus bilangan bulat positif")

        workflow = await self._workflows.get_workflow(
            workflow_id=workflow_id, owner_id=owner_id
        )
        record = await self._repository.get_version(workflow.id or "", version)
        if record is None:
            raise CoursePlanNotFoundError(workflow_id, version=version)
        return record

    # --- Tulis ------------------------------------------------------------

    async def create_version(
        self,
        *,
        workflow: WorkflowRecord,
        output: CoursePlanOutput,
        rps_weeks: Mapping[int, Mapping] | None = None,
        validation_result: dict | None = None,
        activity_configuration: dict | None = None,
        rps_analysis_id: str | None = None,
        revision_notes: str | None = None,
        regeneration_instruction: str | None = None,
        prompt_version: str | None = None,
        model_name: str | None = None,
    ) -> CoursePlanRecord:
        """Simpan satu versi baru berstatus ``DRAFT``.

        Versi sebelumnya tidak diubah. Versi baru ditolak bila workflow sudah
        memiliki versi ``APPROVED``: rencana yang disetujui adalah keputusan
        akhir, bukan bahan regenerasi.
        """
        if workflow.id is None:
            raise CoursePlanValidationError("workflow_id", "wajib diisi")
        if await self._repository.has_approved(workflow.id):
            raise CoursePlanStateError(
                "Course plan sudah disetujui; versi baru tidak dapat dibuat."
            )

        weeks = _build_weeks(output, rps_weeks)
        plan_data = {
            "course": output.course.model_dump(mode="json"),
            "weeks": [
                {
                    "week_number": week.week_number,
                    "title": week.title,
                    "learning_outcomes": list(week.learning_outcomes),
                    "objectives": list(week.objectives),
                    "topics": list(week.topics),
                    "teaching_methods": list(week.teaching_methods),
                    "planned_activities": list(week.planned_activities),
                    "week_type": week.week_type,
                    "rps_week": week.rps_week,
                }
                for week in weeks
            ],
        }

        draft = CoursePlanDraft(
            workflow_id=workflow.id,
            rps_id=workflow.rps_id,
            rps_analysis_id=rps_analysis_id,
            version=await self._repository.next_version(workflow.id),
            course=output.course.model_dump(mode="json"),
            weeks=weeks,
            plan_data=plan_data,
            activity_configuration=activity_configuration,
            validation_result=validation_result,
            revision_notes=revision_notes,
            regeneration_instruction=regeneration_instruction,
            prompt_version=prompt_version,
            model_name=model_name,
        )
        return await self._repository.create(draft)


def _build_weeks(
    output: CoursePlanOutput, rps_weeks: Mapping[int, Mapping] | None
) -> tuple[CoursePlanWeekRecord, ...]:
    """Urutkan minggu dan salin penanda UTS/UAS dari RPS (bila tersedia).

    Penanda minggu dan referensi baris RPS **tidak** diambil dari output agent
    supaya tidak dapat dikarang; keduanya disalin dari RPS Analysis.
    """
    by_number = dict(rps_weeks or {})
    weeks: list[CoursePlanWeekRecord] = []

    for week in sorted(output.weeks, key=lambda item: item.week_number):
        rps_week = by_number.get(week.week_number)
        week_type = "regular"
        if isinstance(rps_week, Mapping):
            candidate = rps_week.get("week_type")
            if isinstance(candidate, str) and candidate in WEEK_TYPES:
                week_type = candidate

        weeks.append(
            CoursePlanWeekRecord(
                week_number=week.week_number,
                title=week.title,
                learning_outcomes=tuple(week.learning_outcomes),
                objectives=tuple(week.objectives),
                topics=tuple(week.topics),
                teaching_methods=tuple(week.teaching_methods),
                planned_activities=tuple(
                    activity.value for activity in week.planned_activities
                ),
                week_type=week_type,
                rps_week=week.week_number if rps_week is not None else None,
            )
        )

    return tuple(weeks)
