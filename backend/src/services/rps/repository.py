"""RPS Repository — satu-satunya tempat query dan mutasi tabel ``rps``.

Repository hanya menjawab "bagaimana data RPS diambil/disimpan?", tanpa aturan
bisnis dan tanpa keputusan workflow. Operasi aplikasi (validasi unggahan,
lifecycle pemrosesan, idempotency) berada di
:mod:`src.services.rps.service`.

Query deduplikasi ada di sini karena ia murni operasi data: "adakah baris dengan
owner, hash, dan versi skema yang sama?". Keputusan *memakai* hasilnya (unggahan
dianggap duplikat atau tidak) tetap milik service.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.rps import RPS as RPSEntity
from src.services.rps.domain import RPSDocument
from src.services.rps.enums import RPSStatus
from src.services.rps.mappers import apply_to_entity, to_domain

__all__ = ["RPSRepository"]


class RPSRepository:
    """Akses data RPS di atas ``AsyncSession`` yang di-inject dari luar.

    Seluruh operasi mengembalikan domain model, bukan entity ORM, sehingga
    pemanggil tidak perlu mengetahui struktur tabel.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, document: RPSDocument) -> RPSDocument:
        """Simpan dokumen RPS baru dan kembalikan hasil persist."""
        entity = apply_to_entity(document, RPSEntity())
        self._session.add(entity)
        await self._session.commit()
        await self._session.refresh(entity)
        return to_domain(entity)

    async def get_by_id(self, rps_id: str) -> RPSDocument | None:
        """Ambil dokumen berdasarkan identifier (ShortUUID); ``None`` bila tidak ada."""
        entity = await self._session.get(RPSEntity, rps_id)
        return to_domain(entity) if entity is not None else None

    async def find_by_id_and_owner(self, rps_id: str, owner_id: str) -> RPSDocument | None:
        """Ambil dokumen yang dimiliki user tertentu.

        Scoping owner dilakukan di query — bukan dengan memeriksa hasilnya di
        service — supaya dokumen milik instruktur lain tidak pernah termuat ke
        dalam proses ini.
        """
        statement = select(RPSEntity).where(
            RPSEntity.id == rps_id,
            RPSEntity.owner_id == owner_id,
        )
        entity = (await self._session.execute(statement)).scalar_one_or_none()
        return to_domain(entity) if entity is not None else None

    async def list_by_owner(self, owner_id: str) -> list[RPSDocument]:
        """Seluruh dokumen milik satu owner, terbaru lebih dulu (design-api §6.5).

        Scoping owner dilakukan di query, sama seperti
        :meth:`find_by_id_and_owner`; dokumen milik instruktur lain tidak pernah
        termuat ke dalam proses ini.
        """
        statement = (
            select(RPSEntity)
            .where(RPSEntity.owner_id == owner_id)
            .order_by(RPSEntity.created_at.desc())
        )
        entities = (await self._session.execute(statement)).scalars().all()
        return [to_domain(entity) for entity in entities]

    async def find_by_hash(
        self,
        *,
        owner_id: str,
        file_hash: str,
        schema_version: str,
        status: RPSStatus | None = None,
    ) -> RPSDocument | None:
        """Cari dokumen milik owner dengan hash dan versi skema tertentu.

        Dipakai untuk idempotency (``file_hash`` + ``schema_version``). Hasil
        terbaru yang dipilih, sehingga unggahan ulang selalu bertemu baris yang
        paling relevan.
        """
        statement = (
            select(RPSEntity)
            .where(
                RPSEntity.owner_id == owner_id,
                RPSEntity.file_hash == file_hash,
                RPSEntity.schema_version == schema_version,
            )
            .order_by(RPSEntity.created_at.desc())
            .limit(1)
        )
        if status is not None:
            statement = statement.where(RPSEntity.status == status)

        entity = (await self._session.execute(statement)).scalar_one_or_none()
        return to_domain(entity) if entity is not None else None

    async def update(self, document: RPSDocument) -> RPSDocument | None:
        """Perbarui dokumen yang sudah dipersist; ``None`` bila barisnya tidak ada."""
        if document.id is None:
            raise ValueError(
                "update memerlukan dokumen yang sudah dipersist (id tidak boleh kosong)"
            )

        entity = await self._session.get(RPSEntity, document.id)
        if entity is None:
            return None

        apply_to_entity(document, entity)
        await self._session.commit()
        await self._session.refresh(entity)
        return to_domain(entity)
