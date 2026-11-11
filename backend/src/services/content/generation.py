"""Tahap content generation pada orkestrator (BE-19.3).

Service ini menjawab "konten apa yang harus dihasilkan pada run ini, bagaimana
hasilnya disimpan, dan keputusan apa yang tercatat?". Urutan tahap tetap milik
:mod:`src.services.workflow.orchestrator`.

Aturan yang dijaga di sini:

- hanya course plan versi ``APPROVED`` yang boleh digenerate;
- jenis konten mengikuti **snapshot** ``activity_configuration`` pada versi
  rencana itu, bukan konfigurasi dosen yang mungkin sudah berubah;
- satu konten per jenis per minggu; regenerasi menambah versi baru lewat
  ``content_key`` yang sama dan tidak mengubah versi lama;
- kegagalan satu konten menjadi ValidationResult ``FAILED`` + event, bukan
  kegagalan seluruh run — konten lain tetap dihasilkan.
"""

from __future__ import annotations

import asyncio
import enum
import json
from dataclasses import dataclass
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import get_settings
from src.models.validation_result import ValidationStatus
from src.models.workflow import WorkflowStatus
from src.models.workflow_event import EventType
from src.schemas.content import WeekContext, to_row
from src.services.content.domain import (
    ContentDraft,
    ContentKind,
    ContentRecord,
    content_key_for,
)
from src.services.content.errors import (
    ContentGenerationFailedError,
    ContentNotFoundError,
    ContentStateError,
    ContentValidationError,
)
from src.services.content.generate_service import (
    PROMPT_VERSION,
    ContentGenerationError,
    ContentEvent,
    WeekResult,
    generate_contents,
    list_weeks,
)
from src.services.content.repository import ContentRepository
from src.services.course_plan.domain import CoursePlanRecord
from src.services.course_plan.repository import CoursePlanRepository
from src.services.course_plan.service import MAX_REVISION_NOTES_LENGTH
from src.services.workflow.domain import WorkflowRecord, stage_name
from src.services.workflow.service import WorkflowService

__all__ = [
    "CONTENT_LABELS",
    "ContentGenerationService",
    "ContentJob",
    "GenerationOutcome",
    "GenerationSummary",
    "RegenerationScope",
]

#: Nama tahap pada event (sama dengan ``stage_name`` domain).
GENERATION_STAGE = stage_name(WorkflowStatus.GENERATING_CONTENT) or "content_generation"
VALIDATION_STAGE = stage_name(WorkflowStatus.VALIDATING) or "validation"

EVENT_CONTENT_VALIDATED = "WORKFLOW_CONTENT_VALIDATED"
EVENT_CONTENT_VALIDATION_FAILED = "WORKFLOW_CONTENT_VALIDATION_FAILED"
EVENT_CONTENT_FAILED = "WORKFLOW_CONTENT_FAILED"
EVENT_WEEK_COMPLETED = "WORKFLOW_WEEK_COMPLETED"

CONTENT_LABELS: dict[ContentKind, str] = {
    ContentKind.LEARNING_MATERIAL: "Learning Material",
    ContentKind.RESOURCE: "Learning Resource",
    ContentKind.ASSIGNMENT: "Assignment",
    ContentKind.QUIZ: "Quiz",
}

#: ``activity_configuration`` (BE-10.1) → jenis konten yang dihasilkan.
CONFIG_TO_KIND: dict[str, ContentKind] = {
    "learning_material": ContentKind.LEARNING_MATERIAL,
    "learning_resource": ContentKind.RESOURCE,
    "assignment": ContentKind.ASSIGNMENT,
    "quiz": ContentKind.QUIZ,
}

#: Jenis konten yang didukung tiap tipe minggu.
KINDS_BY_WEEK_TYPE: dict[str, tuple[ContentKind, ...]] = {
    "regular": (
        ContentKind.RESOURCE,
        ContentKind.LEARNING_MATERIAL,
        ContentKind.ASSIGNMENT,
    ),
    "quiz": (ContentKind.QUIZ,),
    "kuis": (ContentKind.QUIZ,),
}


class RegenerationScope(str, enum.Enum):
    """Cakupan regenerasi (issue BE-19.3)."""

    COURSE = "COURSE"
    MINGGU = "MINGGU"
    ITEM = "ITEM"


@dataclass(frozen=True)
class ContentJob:
    """Permintaan satu run generation/regeneration."""

    week_numbers: tuple[int, ...] | None = None
    content_id: str | None = None
    scope: RegenerationScope | None = None
    notes: str | None = None


@dataclass(frozen=True)
class GenerationTarget:
    """Satu konten (minggu × jenis) yang harus dihasilkan."""

    ctx: WeekContext
    kind: ContentKind
    previous: ContentRecord | None = None


@dataclass(frozen=True)
class PreparedGeneration:
    course_plan_id: str
    targets: tuple[GenerationTarget, ...]
    regenerate: bool
    notes: str | None


@dataclass
class GenerationOutcome:
    target: GenerationTarget
    result: WeekResult
    retry_count: int = 0


@dataclass(frozen=True)
class GenerationSummary:
    total: int
    succeeded: int
    failed: int


class ContentGenerationService:
    """Orkestrasi domain content generation di atas satu ``AsyncSession``."""

    def __init__(
        self,
        session: AsyncSession,
        repository: ContentRepository,
        *,
        workflows: WorkflowService,
        plans: CoursePlanRepository,
    ) -> None:
        self._session = session
        self._repository = repository
        self._workflows = workflows
        self._plans = plans

    @classmethod
    def from_session(cls, session: AsyncSession) -> ContentGenerationService:
        return cls(
            session,
            ContentRepository(session),
            workflows=WorkflowService.from_session(session),
            plans=CoursePlanRepository(session),
        )

    # --- Dipanggil route --------------------------------------------------

    async def start(
        self, *, workflow_id: str, owner_id: str, job: ContentJob
    ) -> WorkflowRecord:
        """Validasi prasyarat lalu klaim workflow untuk satu run.

        Klaim atomik mencegah dua request generation berjalan bersamaan pada
        workflow yang sama (``GENERATING_CONTENT`` bukan status yang boleh
        diklaim).
        """
        workflow = await self._workflows.get_workflow(
            workflow_id=workflow_id, owner_id=owner_id
        )
        plan = await self._require_approved_plan(workflow)
        await self._build_prepared(workflow, plan, job)

        claimed = await self._workflows.claim_content_generation(
            workflow_id=workflow.id or "", owner_id=owner_id
        )
        if claimed is None:
            raise ContentStateError(
                f"workflow {workflow.id} tidak dapat mulai generation",
                public_message=(
                    "Generation konten tidak dapat dimulai pada status workflow "
                    "ini (mungkin sedang berjalan)."
                ),
            )
        return claimed

    # --- Dipanggil orkestrator -------------------------------------------

    async def prepare(
        self, workflow: WorkflowRecord, job: ContentJob
    ) -> PreparedGeneration:
        """Baca snapshot rencana yang disetujui dan tentukan target konten."""
        plan = await self._require_approved_plan(workflow)
        return await self._build_prepared(workflow, plan, job)

    async def generate(
        self,
        workflow: WorkflowRecord,
        prepared: PreparedGeneration,
        *,
        emit_event,
    ) -> list[GenerationOutcome]:
        """Jalankan Content Generation Service per minggu, isolasi kegagalan.

        Beberapa minggu dikerjakan bersamaan (``CONTENT_GENERATION_CONCURRENCY``)
        karena hampir seluruh waktunya menunggu LLM. Session database tidak boleh
        dipakai beberapa coroutine sekaligus, jadi setiap akses database selama
        generation (konteks minggu dan event) dilewatkan satu lock; yang berjalan
        paralel hanya panggilan model. Hasil tetap diurutkan per minggu.
        """
        by_week: dict[int, list[GenerationTarget]] = {}
        for target in prepared.targets:
            by_week.setdefault(target.ctx.week_number, []).append(target)

        db_lock = asyncio.Lock()
        limit = asyncio.Semaphore(get_settings().content_generation_concurrency)

        async def locked_emit(**kwargs) -> None:
            async with db_lock:
                await emit_event(**kwargs)

        async def run(week: int) -> list[GenerationOutcome]:
            async with limit:
                return await self._generate_week(
                    prepared,
                    week,
                    by_week[week],
                    emit_event=locked_emit,
                    db_lock=db_lock,
                )

        weeks = sorted(by_week)
        results = await asyncio.gather(*(run(week) for week in weeks))
        return [outcome for week_outcomes in results for outcome in week_outcomes]

    async def store(
        self,
        workflow: WorkflowRecord,
        prepared: PreparedGeneration,
        outcomes: list[GenerationOutcome],
    ) -> GenerationSummary:
        """Simpan versi konten + hasil validasi, lalu catat event per item/minggu."""
        if not outcomes:
            raise ContentGenerationFailedError(
                "tidak ada konten yang dihasilkan pada run ini"
            )

        by_week: dict[int, list[GenerationOutcome]] = {}
        for outcome in outcomes:
            by_week.setdefault(outcome.target.ctx.week_number, []).append(outcome)

        succeeded = 0
        for week in sorted(by_week):
            week_succeeded = 0
            for outcome in by_week[week]:
                record, passed = await self._store_one(
                    workflow, prepared, outcome
                )
                if outcome.result.error is None:
                    succeeded += 1
                if passed:
                    week_succeeded += 1

            count = len(by_week[week])
            await self._workflows.record_event(
                workflow,
                event_type=EventType.AKTIVITAS_AGENT,
                event=EVENT_WEEK_COMPLETED,
                stage=VALIDATION_STAGE,
                message=(
                    f"Minggu {week} selesai: {week_succeeded} konten berhasil "
                    f"divalidasi, {count - week_succeeded} gagal."
                ),
                metadata={
                    "week_number": week,
                    "content_count": count,
                    "validated_count": week_succeeded,
                },
            )

        failed = len(outcomes) - succeeded
        if succeeded == 0:
            raise ContentGenerationFailedError(
                f"seluruh {len(outcomes)} konten gagal dihasilkan"
            )
        return GenerationSummary(
            total=len(outcomes), succeeded=succeeded, failed=failed
        )

    # --- Internal ---------------------------------------------------------

    async def _require_approved_plan(
        self, workflow: WorkflowRecord
    ) -> CoursePlanRecord:
        plan = await self._plans.get_approved(workflow.id or "")
        if plan is None:
            raise ContentStateError(
                f"workflow {workflow.id} tidak memiliki course plan APPROVED",
                public_message=(
                    "Generate konten hanya dapat dijalankan setelah course plan "
                    "disetujui."
                ),
            )
        return plan

    async def _build_prepared(
        self, workflow: WorkflowRecord, plan, job: ContentJob
    ) -> PreparedGeneration:
        active = _active_kinds(plan.activity_configuration)
        if not active:
            raise ContentValidationError(
                "activity_configuration",
                "tidak ada jenis konten aktif pada course plan",
            )

        try:
            contexts = await list_weeks(self._session, plan.id)
        except ContentGenerationError as exc:
            raise ContentStateError(
                str(exc),
                public_message="Course plan belum memiliki minggu yang dapat digenerate.",
            ) from exc

        available = {ctx.week_number for ctx in contexts}
        requested = _validated_weeks(job.week_numbers, available)

        notes = (job.notes or "").strip() or None
        if job.scope is not None:
            if not notes:
                raise ContentValidationError("notes", "catatan revisi wajib diisi")
            if len(notes) > MAX_REVISION_NOTES_LENGTH:
                raise ContentValidationError(
                    "notes", f"maksimal {MAX_REVISION_NOTES_LENGTH} karakter"
                )

        if job.scope is RegenerationScope.ITEM:
            targets = await self._item_targets(workflow, contexts, job, active)
        else:
            if job.scope is RegenerationScope.MINGGU and (
                requested is None or len(requested) != 1
            ):
                raise ContentValidationError(
                    "week_number", "regenerasi MINGGU memerlukan satu minggu"
                )
            weeks = available if requested is None else requested
            targets = await self._targets(
                workflow, contexts, weeks, active, regenerate=job.scope is not None
            )

        if not targets:
            if job.scope is None:
                # Run lanjutan setelah server mulai ulang: seluruh konten sudah
                # tersimpan, jadi tidak ada panggilan model yang perlu diulang.
                return PreparedGeneration(
                    course_plan_id=plan.id,
                    targets=(),
                    regenerate=False,
                    notes=notes,
                )
            raise ContentStateError(
                "tidak ada konten yang cocok untuk digenerate",
                public_message=(
                    "Tidak ada jenis konten aktif yang dapat dihasilkan pada "
                    "minggu yang dipilih."
                ),
            )

        return PreparedGeneration(
            course_plan_id=plan.id,
            targets=tuple(targets),
            regenerate=job.scope is not None,
            notes=notes,
        )

    async def _targets(
        self,
        workflow: WorkflowRecord,
        contexts: list[WeekContext],
        weeks: set[int],
        active: tuple[ContentKind, ...],
        *,
        regenerate: bool,
    ) -> list[GenerationTarget]:
        targets: list[GenerationTarget] = []
        for ctx in sorted(contexts, key=lambda item: item.week_number):
            if ctx.week_number not in weeks:
                continue
            for kind in active:
                if kind not in KINDS_BY_WEEK_TYPE.get(
                    ctx.week_data.week_type.lower(), ()
                ):
                    continue
                existing = await self._repository.get_latest(
                    content_key_for(workflow.id or "", ctx.week_number, kind)
                )
                previous = None
                if regenerate:
                    previous = existing
                elif existing is not None:
                    # Generate awal yang dilanjutkan: konten yang sudah tersimpan
                    # tidak dibuat ulang, sehingga run yang terputus melanjutkan
                    # sisa minggu/jenis saja.
                    continue
                targets.append(GenerationTarget(ctx=ctx, kind=kind, previous=previous))
        return targets

    async def _item_targets(
        self,
        workflow: WorkflowRecord,
        contexts: list[WeekContext],
        job: ContentJob,
        active: tuple[ContentKind, ...],
    ) -> list[GenerationTarget]:
        if not job.content_id:
            raise ContentValidationError("content_id", "wajib diisi untuk scope ITEM")

        record = await self._repository.get_by_id(job.content_id)
        if record is None or record.workflow_id != workflow.id:
            raise ContentNotFoundError(job.content_id)
        if record.kind not in active:
            raise ContentStateError(
                f"jenis konten {record.kind.value} tidak aktif",
                public_message=(
                    "Jenis konten ini tidak aktif pada konfigurasi course plan "
                    "sehingga tidak dapat diregenerasi."
                ),
            )

        ctx = next(
            (
                context
                for context in contexts
                if context.week_number == record.week_number
                or context.course_plan_week_id == record.course_plan_week_id
            ),
            None,
        )
        if ctx is None:
            raise ContentNotFoundError(job.content_id)
        return [GenerationTarget(ctx=ctx, kind=record.kind, previous=record)]

    async def _generate_week(
        self,
        prepared: PreparedGeneration,
        week: int,
        targets: list[GenerationTarget],
        *,
        emit_event,
        db_lock: asyncio.Lock | None = None,
    ) -> list[GenerationOutcome]:
        attempts: dict[str, int] = {}

        async def emit(*, event_type: ContentEvent, message: str, **data) -> None:
            name = getattr(event_type, "name", str(event_type))
            content_type = str(data.get("content_type") or "")
            if name == "LLM_CALLING" and content_type:
                attempts[content_type] = max(
                    attempts.get(content_type, 1), int(data.get("attempt") or 1)
                )
            await emit_event(event_type=event_type, message=message, **data)

        previous = targets[0].previous if len(targets) == 1 else None
        revision_notes = prepared.notes or (
            (previous.revision_notes if previous is not None else None) or ""
        )

        try:
            results = await generate_contents(
                _LockedSession(self._session, db_lock) if db_lock is not None else self._session,
                prepared.course_plan_id,
                week_numbers=[week],
                content_types=[target.kind.value for target in targets],
                concurrency=1,
                emit_event=emit,
                previous_version=(
                    _previous_version_text(previous) if previous is not None else ""
                ),
                revision_notes=revision_notes,
                include_assignment=False,
                include_resources=False,
            )
        except (ContentGenerationError, ValueError) as exc:
            error = (
                exc
                if isinstance(exc, ContentGenerationError)
                else ContentGenerationError(str(exc), reason_code="INVALID_WEEK")
            )
            return [
                GenerationOutcome(
                    target=target,
                    result=WeekResult(
                        ctx=target.ctx,
                        error=error,
                        content_type=target.kind.value,
                    ),
                )
                for target in targets
            ]

        by_key = {
            (result.ctx.week_number, result.content_type): result for result in results
        }
        outcomes: list[GenerationOutcome] = []
        for target in targets:
            result = by_key.get((week, target.kind.value))
            if result is None:
                result = WeekResult(
                    ctx=target.ctx,
                    error=ContentGenerationError(
                        f"Konten {target.kind.value} minggu {week} tidak dihasilkan.",
                        reason_code="CONTENT_NOT_GENERATED",
                    ),
                    content_type=target.kind.value,
                )
            outcomes.append(
                GenerationOutcome(
                    target=target,
                    result=result,
                    retry_count=max(attempts.get(target.kind.value, 1) - 1, 0),
                )
            )
        return outcomes

    async def _store_one(
        self,
        workflow: WorkflowRecord,
        prepared: PreparedGeneration,
        outcome: GenerationOutcome,
    ) -> tuple[ContentRecord, bool]:
        target = outcome.target
        result = outcome.result
        label = CONTENT_LABELS[target.kind]
        key = (
            target.previous.content_key
            if target.previous is not None and target.previous.content_key
            else None
        )

        if result.error is None and result.material is not None:
            row = to_row(target.kind.value, result.material, target.ctx)
            data = row.get("activity_data") if target.kind.is_activity else row["content_data"]
            record = await self._repository.create(
                ContentDraft(
                    kind=target.kind,
                    workflow_id=workflow.id or "",
                    course_plan_id=prepared.course_plan_id,
                    course_plan_week_id=target.ctx.course_plan_week_id,
                    week_number=target.ctx.week_number,
                    title=row["title"],
                    content_data=data,
                    content_markdown=row.get("content_markdown"),
                    content_key=key,
                    revision_notes=prepared.notes,
                    prompt_version=_prompt_version(target.kind),
                    model_name=_model_name(),
                )
            )
            validation = validate_generated_content(
                target.kind, result.material, target.ctx
            )
            await self._repository.add_validation(
                record,
                status=validation["status"],
                checks=validation["checks"],
                errors=validation["errors"],
                score=validation["score"],
                retry_count=outcome.retry_count,
            )
            passed = validation["status"] is ValidationStatus.PASSED
            await self._workflows.record_event(
                workflow,
                event_type=(
                    EventType.AKTIVITAS_AGENT
                    if passed
                    else EventType.ERROR_FAILURE
                ),
                event=(
                    EVENT_CONTENT_VALIDATED
                    if passed
                    else EVENT_CONTENT_VALIDATION_FAILED
                ),
                stage=VALIDATION_STAGE,
                message=(
                    f"Minggu {target.ctx.week_number} - {label} "
                    f"{'selesai' if passed else 'gagal validasi'}."
                ),
                metadata={
                    "content_id": record.id,
                    "week_number": target.ctx.week_number,
                    "content_type": target.kind.value,
                    "validation_status": validation["status"].value,
                    "score": validation["score"],
                },
            )
            return record, passed

        error = result.error or ContentGenerationError("Konten tidak dihasilkan.")
        record = await self._repository.create(
            ContentDraft(
                kind=target.kind,
                workflow_id=workflow.id or "",
                course_plan_id=prepared.course_plan_id,
                course_plan_week_id=target.ctx.course_plan_week_id,
                week_number=target.ctx.week_number,
                title=_failure_title(target, label),
                content_data={
                    "error": {
                        "reason_code": getattr(error, "reason_code", None),
                        "message": str(error)[:500],
                        "details": list(getattr(error, "details", []) or [])[:5],
                    }
                },
                content_key=key,
                revision_notes=prepared.notes,
                prompt_version=_prompt_version(target.kind),
                model_name=_model_name(),
            )
        )
        await self._repository.add_validation(
            record,
            status=ValidationStatus.FAILED,
            checks={"generation": "FAILED"},
            errors={"generation": [str(error)[:500]]},
            score=0.0,
            retry_count=outcome.retry_count,
        )
        await self._workflows.record_event(
            workflow,
            event_type=EventType.ERROR_FAILURE,
            event=EVENT_CONTENT_FAILED,
            stage=VALIDATION_STAGE,
            message=f"Minggu {target.ctx.week_number} - {label} gagal.",
            metadata={
                "content_id": record.id,
                "week_number": target.ctx.week_number,
                "content_type": target.kind.value,
                "reason_code": getattr(error, "reason_code", None),
                "retry_count": outcome.retry_count,
            },
        )
        return record, False


# --- Aturan validasi ---------------------------------------------------------


def validate_generated_content(
    kind: ContentKind, output, ctx: WeekContext
) -> dict:
    """Pemeriksaan BE-20.4 yang dapat dijalankan tanpa memanggil LLM.

    Validasi skema sudah dilakukan Content Generation Service saat output
    di-parse. Di sini diperiksa hal yang tidak dapat dijamin schema: Sub-CPMK
    harus berasal dari weekly plan dan URL resource harus berbentuk valid.

    ponytail: pemeriksaan semantik berbasis LLM (BE-20.4) belum ada; tambahkan
    di sini saat service itu mendarat, tanpa mengubah kontrak penyimpanan.
    """
    checks: dict[str, str] = {"schema": "PASSED"}
    errors: dict[str, list[str]] = {}

    expected = {
        str(code).strip()
        for code in (ctx.week_data.learning_outcomes or ())
        if str(code).strip()
    }
    codes = {str(code).strip() for code in getattr(output, "sub_cpmk_codes", ())}
    checks["sub_cpmk"] = "PASSED"
    if expected and not codes.issubset(expected):
        unknown = sorted(codes - expected)
        checks["sub_cpmk"] = "FAILED"
        errors["sub_cpmk"] = [
            f"Sub-CPMK tidak ada pada weekly plan: {', '.join(unknown)}"
        ]

    if kind is ContentKind.RESOURCE:
        checks["resource_url"] = "PASSED"
        url = getattr(output, "url", None)
        if url is not None:
            parsed = urlparse(str(url))
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                checks["resource_url"] = "FAILED"
                errors["resource_url"] = ["URL resource tidak valid."]

    passed = not errors
    return {
        "status": ValidationStatus.PASSED if passed else ValidationStatus.FAILED,
        "checks": checks,
        "errors": errors or None,
        "score": 1.0 if passed else 0.0,
    }


# --- Helper ------------------------------------------------------------------


def _active_kinds(configuration: dict | None) -> tuple[ContentKind, ...]:
    """Jenis aktif dari snapshot Activity Configuration, urut deterministik."""
    config = configuration or {"learning_material": True}
    return tuple(
        kind for name, kind in CONFIG_TO_KIND.items() if config.get(name) is True
    )


def _validated_weeks(
    weeks: tuple[int, ...] | None, available: set[int]
) -> set[int] | None:
    if weeks is None:
        return None
    if not weeks:
        raise ContentValidationError("weeks", "daftar minggu tidak boleh kosong")
    if any(isinstance(week, bool) or not isinstance(week, int) or week < 1 for week in weeks):
        raise ContentValidationError("weeks", "nomor minggu harus bilangan positif")
    if len(set(weeks)) != len(weeks):
        raise ContentValidationError("weeks", "nomor minggu tidak boleh duplikat")
    invalid = set(weeks) - available
    if invalid:
        raise ContentValidationError(
            "weeks",
            f"minggu tidak tersedia pada course plan: {sorted(invalid)}",
        )
    return set(weeks)


def _previous_version_text(record: ContentRecord | None) -> str:
    if record is None:
        return ""
    body = {
        key: value
        for key, value in (record.content_data or {}).items()
        if key != "traceability"
    }
    return json.dumps(
        {"title": record.title, **body}, ensure_ascii=False, indent=2
    )


def _failure_title(target: GenerationTarget, label: str) -> str:
    title = target.ctx.week_data.title or f"Minggu {target.ctx.week_number}"
    return f"{title} - {label}"[:255]


def _prompt_version(kind: ContentKind) -> str:
    # Prompt per jenis konten sudah ada sejak BE-20.2; nama berkasnya sama
    # dengan nama prompt pada Content Generation Service.
    name = {
        ContentKind.LEARNING_MATERIAL: "learning_material",
        ContentKind.RESOURCE: "learning_resource",
        ContentKind.ASSIGNMENT: "assignment",
        ContentKind.QUIZ: "quiz",
    }[kind]
    return f"{name}/{PROMPT_VERSION}"


def _model_name() -> str | None:
    settings = get_settings()
    return settings.llm_model_for(settings.llm_provider) or None


class _LockedSession:
    """Session yang ``execute``-nya bergiliran lewat lock (generation paralel per minggu)."""

    def __init__(self, session: AsyncSession, lock: asyncio.Lock) -> None:
        self._session = session
        self._lock = lock

    async def execute(self, *args, **kwargs):
        async with self._lock:
            return await self._session.execute(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._session, name)
