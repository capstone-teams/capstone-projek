"""Operasi review konten hasil generation (BE-19.2).

Service ini menjawab "konten apa yang boleh dibaca dan keputusan apa yang boleh
diberikan dosen?", bukan "bagaimana barisnya disimpan?" (itu
:class:`~src.services.content.repository.ContentRepository`).

Scoping selalu dimulai dari workflow milik dosen yang login
(:meth:`WorkflowService.get_workflow`), sehingga workflow dosen lain menghasilkan
404 yang sama seperti workflow tidak ada.

Keputusan review selalu mengenai **versi terbaru** sebuah ``content_key``:
daftar content id pada request boleh menunjuk versi lama, tetapi yang
disetujui/ditolak adalah versi terbarunya — versi lama tidak pernah diubah.
Satu keputusan menulis satu ``WorkflowEvent`` berisi id konten yang berubah,
bukan satu event per konten.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.validation_result import ValidationStatus
from src.models.workflow_event import EventType
from src.services.content.domain import ApprovalStatus, ContentKind, ContentRecord
from src.services.content.errors import (
    ContentNotFoundError,
    ContentStateError,
    ContentValidationError,
)
from src.services.content.repository import ContentGenerationRepository
from src.services.course_plan.service import MAX_REVISION_NOTES_LENGTH
from src.services.workflow.domain import WorkflowRecord, stage_name
from src.services.workflow.service import WorkflowService

__all__ = ["ContentReviewService"]

#: Nama event publik keputusan review (design-api §17: selalu ``WORKFLOW_*``).
EVENT_CONTENTS_APPROVED = "WORKFLOW_CONTENTS_APPROVED"
EVENT_CONTENTS_REJECTED = "WORKFLOW_CONTENTS_REJECTED"


class ContentReviewService:
    """Baca konten dan catat keputusan dosen di atas satu ``AsyncSession``."""

    def __init__(
        self,
        repository: ContentRepository,
        *,
        workflow_service: WorkflowService,
    ) -> None:
        self._repository = repository
        self._workflows = workflow_service

    @classmethod
    def from_session(cls, session: AsyncSession) -> ContentReviewService:
        """Bangun service dengan dependency bawaan."""
        return cls(
            ContentRepository(session),
            workflow_service=WorkflowService.from_session(session),
        )

    # --- Baca -------------------------------------------------------------

    async def list_contents(
        self,
        *,
        workflow_id: str,
        owner_id: str,
        week_number: int | None = None,
        content_type: ContentKind | None = None,
        status: ApprovalStatus | None = None,
    ) -> list[ContentRecord]:
        """Versi terbaru setiap konten pada workflow, dengan filter opsional."""
        workflow = await self._workflows.get_workflow(
            workflow_id=workflow_id, owner_id=owner_id
        )
        return await self._repository.list_for_workflow(
            workflow.id or "",
            week_number=week_number,
            content_type=content_type,
            status=status,
        )

    async def get_content(
        self, *, workflow_id: str, owner_id: str, content_id: str
    ) -> ContentRecord:
        """Detail satu versi konten beserta hasil validasi terbarunya."""
        workflow = await self._workflows.get_workflow(
            workflow_id=workflow_id, owner_id=owner_id
        )
        return await self._owned_content(workflow, content_id)

    async def list_versions(
        self, *, workflow_id: str, owner_id: str, content_id: str
    ) -> list[ContentRecord]:
        """Riwayat seluruh versi konten, terbaru lebih dulu."""
        record = await self.get_content(
            workflow_id=workflow_id, owner_id=owner_id, content_id=content_id
        )
        if not record.content_key:
            # Baris lama (sebelum BE-19) tidak punya identitas antarversi.
            return [record]
        return await self._repository.list_versions(record.content_key)

    # --- Keputusan dosen --------------------------------------------------

    async def approve(
        self,
        *,
        workflow_id: str,
        owner_id: str,
        content_ids: list[str] | None = None,
        week_number: int | None = None,
    ) -> list[ContentRecord]:
        """Setujui versi terbaru yang lolos validasi.

        Konten yang sudah ``APPROVED`` dilewati supaya permintaan berulang aman.
        Konten yang ditolak, sudah dieksekusi, atau belum lolos validasi
        menghasilkan ``409`` beserta alasan yang dapat dibaca dosen.
        """
        workflow, records = await self._selection(
            workflow_id=workflow_id,
            owner_id=owner_id,
            content_ids=content_ids,
            week_number=week_number,
        )
        decided = []
        for record in records:
            if record.status is ApprovalStatus.APPROVED:
                continue
            self._require_approvable(record)
            decided.append(record)

        changed = await self._apply(
            workflow,
            decided,
            status=ApprovalStatus.APPROVED,
            event=EVENT_CONTENTS_APPROVED,
            message="{count} konten disetujui.",
        )
        # Response tetap memuat seluruh pilihan, termasuk yang sudah disetujui.
        updated = {record.id: record for record in changed}
        return [updated.get(record.id, record) for record in records]

    async def reject(
        self,
        *,
        workflow_id: str,
        owner_id: str,
        notes: str,
        content_ids: list[str] | None = None,
        week_number: int | None = None,
    ) -> list[ContentRecord]:
        """Tolak versi terbaru dengan catatan revisi wajib.

        Catatan disimpan pada versi yang ditolak supaya regenerasi berikutnya
        memakai alasan penolakan tersebut.
        """
        revision_notes = (notes or "").strip()
        if not revision_notes:
            raise ContentValidationError("notes", "catatan revisi wajib diisi")
        if len(revision_notes) > MAX_REVISION_NOTES_LENGTH:
            raise ContentValidationError(
                "notes", f"maksimal {MAX_REVISION_NOTES_LENGTH} karakter"
            )

        workflow, records = await self._selection(
            workflow_id=workflow_id,
            owner_id=owner_id,
            content_ids=content_ids,
            week_number=week_number,
        )
        decided = []
        for record in records:
            if record.status is ApprovalStatus.EXECUTED:
                raise ContentStateError(
                    f"konten {record.id} sudah dieksekusi ke Moodle",
                    public_message=(
                        "Konten yang sudah dieksekusi ke Moodle tidak dapat ditolak."
                    ),
                )
            if record.status is ApprovalStatus.APPROVED:
                raise ContentStateError(
                    f"konten {record.id} sudah disetujui",
                    public_message="Konten yang sudah disetujui tidak dapat ditolak.",
                )
            decided.append(record)

        return await self._apply(
            workflow,
            decided,
            status=ApprovalStatus.REJECTED,
            event=EVENT_CONTENTS_REJECTED,
            message="{count} konten ditolak.",
            revision_notes=revision_notes,
        )

    # --- Internal ---------------------------------------------------------

    async def _selection(
        self,
        *,
        workflow_id: str,
        owner_id: str,
        content_ids: list[str] | None,
        week_number: int | None,
    ) -> tuple[WorkflowRecord, list[ContentRecord]]:
        """Workflow milik dosen beserta versi terbaru konten yang dipilih.

        Tanpa ``content_ids`` maupun ``week_number`` berarti seluruh konten
        workflow; keduanya tidak boleh dikirim bersamaan.
        """
        if content_ids and week_number is not None:
            raise ContentValidationError(
                "week_number",
                "pilih salah satu: daftar content_ids atau week_number",
            )

        workflow = await self._workflows.get_workflow(
            workflow_id=workflow_id, owner_id=owner_id
        )

        if content_ids:
            latest: dict[str, ContentRecord] = {}
            for content_id in content_ids:
                record = await self._owned_content(workflow, content_id)
                newest = record
                if record.content_key:
                    newest = (
                        await self._repository.get_latest(record.content_key)
                        or record
                    )
                latest.setdefault(newest.id, newest)
            return workflow, list(latest.values())

        records = await self._repository.list_for_workflow(
            workflow.id or "", week_number=week_number
        )
        if not records:
            raise ContentNotFoundError(workflow.id or workflow_id)
        return workflow, records

    async def _owned_content(
        self, workflow: WorkflowRecord, content_id: str
    ) -> ContentRecord:
        """Konten milik workflow ini; 404 bila tidak ada atau milik workflow lain."""
        record = await self._repository.get_by_id(content_id)
        if record is None or record.workflow_id != workflow.id:
            raise ContentNotFoundError(content_id)
        return record

    def _require_approvable(self, record: ContentRecord) -> None:
        if record.status is ApprovalStatus.EXECUTED:
            raise ContentStateError(
                f"konten {record.id} sudah dieksekusi ke Moodle",
                public_message=(
                    "Konten yang sudah dieksekusi ke Moodle tidak dapat disetujui."
                ),
            )
        if record.status is ApprovalStatus.REJECTED:
            raise ContentStateError(
                f"konten {record.id} berstatus {record.status.value}",
                public_message=(
                    "Konten yang sudah ditolak harus diregenerasi sebelum dapat "
                    "disetujui."
                ),
            )
        validation = record.validation
        if validation is None or validation.status is not ValidationStatus.PASSED:
            raise ContentStateError(
                f"konten {record.id} belum lolos validasi",
                public_message=(
                    "Konten belum lolos validasi sehingga belum dapat disetujui."
                ),
            )

    async def _apply(
        self,
        workflow: WorkflowRecord,
        records: list[ContentRecord],
        *,
        status: ApprovalStatus,
        event: str,
        message: str,
        revision_notes: str | None = None,
    ) -> list[ContentRecord]:
        """Ubah status setiap versi lalu catat satu event keputusan."""
        updated = []
        for record in records:
            changed = await self._repository.set_status(
                record.id, status, revision_notes=revision_notes
            )
            if changed is None:
                raise ContentNotFoundError(record.id)
            updated.append(changed)

        if updated:
            metadata: dict = {
                "content_ids": [record.id for record in updated],
                "count": len(updated),
            }
            if revision_notes is not None:
                metadata["revision_notes"] = revision_notes
            await self._workflows.record_event(
                workflow,
                event_type=EventType.PERUBAHAN_TAHAP,
                event=event,
                stage=stage_name(workflow.status),
                message=message.format(count=len(updated)),
                metadata=metadata,
            )
        return updated
