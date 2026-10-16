"""Domain RPS: unggah, penyimpanan, dan konversi dokumen (BE-05).

Paket ini melayani pemrosesan awal RPS — tahap pertama alur data aplikasi
(content-schema §54: ``RPS File → RPS Analysis``) — dan menjadi kontrak untuk
BE-08, yang melakukan ekstraksi terstruktur dari hasil konversi di sini.

Isi paket:

- :class:`RPSDocument` (+ :mod:`src.services.rps.validation`) — aturan bentuk dan
  lifecycle dokumen RPS;
- :class:`RPSService` — operasi aplikasi: unggah, ambil, proses;
- :class:`RPSRepository` — akses tabel ``rps``; hanya dipanggil oleh service;
- :class:`DocumentStorage` / :class:`LocalDocumentStorage` — port penyimpanan
  berkas beserta adapter filesystem lokal;
- :class:`DocumentConverter` — port konversi dokumen, dengan
  :class:`DoclingDocumentConverter` sebagai adapter Docling (dipasang lewat
  extra opsional ``docling``);
- :class:`RPSStructuredData``-nya ada di :mod:`src.schemas.rps_structured`,
  karena ia adalah kontrak data (Pydantic), bukan logika domain.

Seluruh error domain dipetakan ke HTTP oleh ``src.middlewares``. Pemrosesan
dijalankan *synchronous* pada tahap S0 (Sprint 0); workflow asynchronous beserta Agent
Run menyusul pada BE-08 — lihat :meth:`RPSService.process_rps`.
"""

from src.schemas.rps_structured import (
    RPS_SCHEMA_VERSION,
    RPSStructuredData,
    to_rps_analysis_payload,
)
from src.services.rps.converter import (
    ConvertedTable,
    DocumentConversion,
    DocumentConverter,
)
from src.services.rps.docling_converter import DoclingDocumentConverter
from src.services.rps.domain import RPSDocument
from src.services.rps.enums import RPSStatus
from src.services.rps.errors import (
    DocumentConversionError,
    DocumentConverterUnavailableError,
    DocumentStorageError,
    InvalidFileError,
    RPSDomainError,
    RPSNotFoundError,
    RPSStateError,
    RPSValidationError,
)
from src.services.rps.repository import RPSRepository
from src.services.rps.runner import run_rps_processing
from src.services.rps.service import (
    RPSConversionResult,
    RPSProcessResult,
    RPSProcessStart,
    RPSService,
    RPSUploadResult,
)
from src.services.rps.storage import (
    DocumentStorage,
    LocalDocumentStorage,
    StoredDocument,
    artifact_dir_for,
)

__all__ = [
    # Schema / kontrak data (BE-05.3)
    "RPS_SCHEMA_VERSION",
    "RPSStructuredData",
    "to_rps_analysis_payload",
    # Domain & lifecycle
    "RPSDocument",
    "RPSStatus",
    # Application layer
    "RPSService",
    "RPSRepository",
    "RPSUploadResult",
    "RPSProcessStart",
    "RPSConversionResult",
    "RPSProcessResult",
    "run_rps_processing",
    # Konversi dokumen (BE-05.2)
    "DocumentConverter",
    "DocumentConversion",
    "ConvertedTable",
    "DoclingDocumentConverter",
    # Penyimpanan (BE-05.1)
    "DocumentStorage",
    "LocalDocumentStorage",
    "StoredDocument",
    "artifact_dir_for",
    # Error domain
    "RPSDomainError",
    "RPSValidationError",
    "InvalidFileError",
    "RPSNotFoundError",
    "RPSStateError",
    "DocumentConversionError",
    "DocumentConverterUnavailableError",
    "DocumentStorageError",
]
