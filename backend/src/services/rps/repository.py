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
from src.services.rps.domain import RPSDocument, RPSMetadata
from src.services.rps.enums import RPSStatus
from src.services.rps.mappers import apply_to_entity, to_domain

__all__ = ["RPSRepository"]

# Kolom ringkasan untuk endpoint daftar/detail. ``source_document`` dan
# ``structured_data`` sengaja tidak dipilih: keduanya JSONB besar, sedangkan
# response hanya membutuhkan metadata dan indikator keberadaan dokumen sumber.
_METADATA_COLUMNS = (
    RPSEntity.id,
    RPSEntity.file_name,
    RPSEntity.file_hash,
    RPSEntity.schema_version,
    RPSEntity.status,
    RPSEntity.workflow_id,
    RPSEntity.processing_duration_ms,
    RPSEntity.processing_error_code,
    RPSEntity.processing_error,
    RPSEntity.created_at,
    RPSEntity.updated_at,
    RPSEntity.source_document.isnot(None).label("has_source_document"),
)


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

    async def list_metadata_by_owner(self, owner_id: str) -> list[RPSMetadata]:
        """Ringkasan dokumen milik satu owner, tanpa memuat JSONB besar.

        Dipakai endpoint daftar: mengirim seluruh baris (termasuk JSON Docling)
        hanya untuk menampilkan nama/status membuat request tumbuh mengikuti
        ukuran dokumen, bukan jumlah dokumen.
        """
        statement = (
            select(*_METADATA_COLUMNS)
            .where(RPSEntity.owner_id == owner_id)
            .order_by(RPSEntity.created_at.desc())
        )
        rows = (await self._session.execute(statement)).all()
        return [_to_metadata(row) for row in rows]

    async def find_metadata_by_id_and_owner(
        self, rps_id: str, owner_id: str
    ) -> RPSMetadata | None:
        """Ringkasan satu dokumen milik owner, tanpa memuat JSONB besar.

        Endpoint detail dipantau (polling) selama pemrosesan, sehingga ia tidak
        boleh ikut mengangkut ``source_document``/``structured_data`` setiap kali
        status dibaca.
        """
        statement = select(*_METADATA_COLUMNS).where(
            RPSEntity.id == rps_id,
            RPSEntity.owner_id == owner_id,
        )
        row = (await self._session.execute(statement)).one_or_none()
        return _to_metadata(row) if row is not None else None

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


def _to_metadata(row) -> RPSMetadata:
    """Petakan baris kolom ringkasan menjadi :class:`RPSMetadata`."""
    return RPSMetadata(
        id=row.id,
        file_name=row.file_name,
        file_hash=row.file_hash,
        schema_version=row.schema_version,
        status=row.status,
        has_source_document=bool(row.has_source_document),
        workflow_id=row.workflow_id,
        processing_duration_ms=row.processing_duration_ms,
        processing_error_code=row.processing_error_code,
        processing_error=row.processing_error,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
