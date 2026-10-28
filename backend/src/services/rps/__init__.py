"""Domain RPS: unggah, penyimpanan, konversi, dan analisis dokumen.

Paket ini melayani alur data RPS (content-schema §54:
``RPS File → RPS Analysis``): konversi Docling (BE-05), serialisasi YAML
(BE-08.1), serta penyimpanan hasil analisis dan reanalyze (BE-08.2).

Isi paket:

- :class:`RPSDocument` (+ :mod:`src.services.rps.validation`) — aturan bentuk dan
  lifecycle dokumen RPS, termasuk transisi ``ANALYZING``/``ANALYZED``/``FAILED``;
- :class:`RPSService` — operasi aplikasi: unggah, ambil, proses, analisis;
- :class:`RPSRepository` — akses tabel ``rps``; hanya dipanggil oleh service;
- :class:`DocumentStorage` / :class:`LocalDocumentStorage` — port penyimpanan
  berkas beserta adapter filesystem lokal;
- :class:`DocumentConverter` — port konversi dokumen, dengan
  :class:`DoclingDocumentConverter` sebagai adapter Docling (dipasang lewat
  extra opsional ``docling``);
- :class:`RPSAnalyzer` — port analisis (BE-09.2), dengan :func:`analyze_document`
  sebagai adapter model bahasa;
- :class:`RPSStructuredData`-nya ada di :mod:`src.schemas.rps_structured`,
  karena ia adalah kontrak data (Pydantic), bukan logika domain.

Seluruh error domain dipetakan ke HTTP oleh ``src.middlewares``. Konversi dan
analisis berjalan di background lewat :func:`run_rps_processing` dan
:func:`run_rps_analysis`.
"""

from src.schemas.rps_structured import (
    RPS_SCHEMA_VERSION,
    RPSStructuredData,
    to_rps_analysis_payload,
)
from src.services.rps.analysis_runner import run_rps_analysis
from src.services.rps.analyzer import RPSAnalyzer, analyze_document
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
    RPSAnalysisFailedError,
    RPSDomainError,
    RPSNotFoundError,
    RPSStateError,
    RPSValidationError,
)
from src.services.rps.repository import RPSRepository
from src.services.rps.runner import run_rps_processing
from src.services.rps.service import (
    RPSAnalysisStart,
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
    "RPSAnalysisStart",
    "run_rps_processing",
    "run_rps_analysis",
    # Konversi dokumen (BE-05.2)
    "DocumentConverter",
    "DocumentConversion",
    "ConvertedTable",
    "DoclingDocumentConverter",
    # Analisis dokumen (BE-08.2)
    "RPSAnalyzer",
    "analyze_document",
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
    "RPSAnalysisFailedError",
]
