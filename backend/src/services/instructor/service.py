"""Instructor Setup Service (BE-10.2/BE-10.3).

Tiga konsumen memakai service ini tanpa menyentuh ORM, session, maupun HTTP:

- endpoint setup dosen (:mod:`src.routes.instructors`) — ambil/simpan setup;
- seed akun uji (:mod:`src.services.seed`) — setup default untuk dosen uji;
- agent — konteks dosen berupa payload/YAML, sehingga agent tidak query database
  sendiri (BE-10.3).

Perubahan setup bersifat **parsial** (design-api §7.2): pemanggil mengirim hanya
field yang berubah, service menggabungkannya dengan nilai tersimpan, lalu
memvalidasi hasil gabungan itu secara utuh — sehingga konfigurasi yang menjadi
tidak sah setelah penggabungan (mis. semua aktivitas dimatikan) tetap ditolak.

Batas panjang Additional Prompt dibaca dari environment saat service dibangun
(``Settings.instructor_additional_prompt_max_length``), bukan di-hardcode pada
schema, sehingga operator dapat menyesuaikannya tanpa mengubah kode.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import get_settings
from src.services.instructor.context import instructor_context_to_yaml, to_agent_context
from src.services.instructor.domain import InstructorSetup, normalize_setup
from src.services.instructor.repository import InstructorSetupRepository

__all__ = ["InstructorSetupService"]


class InstructorSetupService:
    """Operasi aplikasi terhadap setup dosen."""

    def __init__(self, repository: InstructorSetupRepository, *, prompt_max_length: int) -> None:
        self._repository = repository
        self._prompt_max_length = prompt_max_length

    @classmethod
    def from_session(
        cls, session: AsyncSession, *, prompt_max_length: int | None = None
    ) -> "InstructorSetupService":
        """Bangun service di atas session yang diberikan."""
        return cls(
            InstructorSetupRepository(session),
            prompt_max_length=(
                get_settings().instructor_additional_prompt_max_length
                if prompt_max_length is None
                else prompt_max_length
            ),
        )

    async def find_setup(self, instructor_id: str) -> InstructorSetup | None:
        """Setup tersimpan dosen; ``None`` bila dosen belum pernah menyimpan."""
        return await self._repository.load(instructor_id)

    async def get_setup(self, instructor_id: str) -> InstructorSetup:
        """Setup dosen dengan nilai default bila belum pernah disimpan.

        Endpoint memakai operasi ini: dosen baru langsung melihat form yang siap
        diisi dengan default (learning material aktif), bukan 404.
        """
        return await self._repository.load(instructor_id) or InstructorSetup()

    async def update_setup(
        self,
        instructor_id: str,
        *,
        profile_changes: Mapping[str, str] | None = None,
        activity_changes: Mapping[str, Any] | None = None,
    ) -> InstructorSetup:
        """Ubah sebagian setup dosen; field yang tidak dikirim dibiarkan.

        ``profile_changes`` berisi subset key :class:`InstructorProfile`
        (``teaching_style`` dan seterusnya); ``activity_changes`` berisi subset
        key :class:`ActivityConfiguration` (flag aktivitas dan
        ``additional_prompt``).

        Nilai tidak valid ditolak sebagai
        :class:`~src.services.instructor.errors.InstructorSetupValidationError`
        **sebelum** database disentuh, sehingga tidak ada setup setengah valid
        yang tersimpan.
        """
        current = await self.get_setup(instructor_id)
        merged = normalize_setup(
            profile=replace(current.profile, **(profile_changes or {})),
            activity=replace(current.activity, **(activity_changes or {})),
            prompt_max_length=self._prompt_max_length,
        )
        await self._repository.save(instructor_id, merged)

        # Nilai tersimpan (termasuk timestamp database) lebih akurat daripada
        # hasil gabungan di memori.
        return await self.get_setup(instructor_id)

    async def ensure_default_setup(self, instructor_id: str) -> bool:
        """Buat setup default bila dosen belum punya; ``True`` bila baris dibuat.

        Idempotent dan **tidak** menimpa setup yang sudah ada, sehingga aman
        dipanggil setiap kali seed akun uji dijalankan (BE-10.1).
        """
        if await self._repository.load(instructor_id) is not None:
            return False
        await self._repository.save(instructor_id, InstructorSetup())
        return True

    async def get_agent_context(self, instructor_id: str) -> dict[str, Any]:
        """Konteks dosen untuk prompt agent (BE-10.3).

        ``ponytail:`` menerima id dosen saja. Varian ``workflow_id`` dari issue
        BE-10.3 menunggu tabel workflow (BE-11.1); saat itu ada, resolver
        workflow → dosen cukup ditambahkan di sini, bukan di agent.
        """
        return to_agent_context(await self.get_setup(instructor_id))

    async def get_agent_context_yaml(self, instructor_id: str) -> str:
        """Konteks dosen sebagai YAML, dirender bersama YAML RPS pada prompt."""
        return instructor_context_to_yaml(await self.get_setup(instructor_id))
