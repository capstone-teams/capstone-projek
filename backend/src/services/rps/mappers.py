"""Pemetaan antara entity ORM (BE-02) dan domain model RPS (BE-05).

Pemetaan berada di layer service supaya domain tetap bebas SQLAlchemy, dan
repository tetap menjadi satu-satunya tempat yang menyentuh entity persistence.
Nama field sengaja sama persis di kedua sisi (``file_name``, ``file_type``,
``file_path``, ``file_hash``, ``schema_version``, ``status``,
``source_document``, ``processing_duration_ms``, ``processing_error_code``,
``processing_error``, ``structured_data``), sehingga tidak ada terjemahan nama
yang bisa menyimpang; satu-satunya nilai yang dibentuk persistence adalah ``id``
dan timestamp.
"""

from __future__ import annotations

from src.models.rps import RPS as RPSEntity
from src.services.rps.domain import RPSDocument

__all__ = ["apply_to_entity", "to_domain"]


def to_domain(entity: RPSEntity) -> RPSDocument:
    """Bangun domain :class:`RPSDocument` dari baris tabel ``rps``.

    Nilai dari database tetap melewati validasi domain, sehingga invariant
    (hash berbentuk SHA-256, status kanonik, path relatif yang aman) tetap
    berlaku untuk data yang dibaca — bukan hanya untuk data yang ditulis.
    """
    return RPSDocument(
        id=entity.id,
        owner_id=entity.owner_id,
        file_name=entity.file_name,
        file_type=entity.file_type,
        file_path=entity.file_path,
        file_hash=entity.file_hash,
        schema_version=entity.schema_version,
        status=entity.status,
        source_document=entity.source_document,
        processing_duration_ms=entity.processing_duration_ms,
        processing_error_code=entity.processing_error_code,
        processing_error=entity.processing_error,
        structured_data=entity.structured_data,
        analyzed_at=entity.analyzed_at,
        workflow_id=entity.workflow_id,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def apply_to_entity(document: RPSDocument, entity: RPSEntity) -> RPSEntity:
    """Salin nilai domain ke entity ORM (insert atau update).

    ``id`` hanya disalin bila domain sudah punya identifier; dokumen baru
    membiarkan kolom ``id`` dibentuk oleh database foundation.
    """
    if document.id is not None:
        entity.id = document.id
    entity.owner_id = document.owner_id
    entity.file_name = document.file_name
    entity.file_type = document.file_type
    entity.file_path = document.file_path
    entity.file_hash = document.file_hash
    entity.schema_version = document.schema_version
    entity.status = document.status
    entity.source_document = document.source_document
    entity.processing_duration_ms = document.processing_duration_ms
    entity.processing_error_code = document.processing_error_code
    entity.processing_error = document.processing_error
    entity.structured_data = document.structured_data
    entity.analyzed_at = document.analyzed_at
    entity.workflow_id = document.workflow_id
    return entity
