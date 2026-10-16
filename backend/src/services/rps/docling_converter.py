"""Adapter Docling untuk konversi dokumen RPS (BE-05.2).

Docling (IBM) adalah *candidate solution* untuk document processing pada desain
sistem, dan modul ini adalah satu-satunya tempat di aplikasi yang menyentuhnya.
Tiga hal yang dijaga di sini:

1. **Import ditunda (lazy).** Docling beserta torch dan model ML-nya dipasang
   sebagai extra opsional. Modul ini karena itu **tidak** mengimpor Docling pada
   module level; bila extra-nya belum terpasang, kegagalan muncul sebagai
   :class:`DocumentConverterUnavailableError` dengan pesan yang menyebutkan
   perintah pemasangannya — bukan ``ModuleNotFoundError`` mentah.
2. **Tidak memblokir event loop.** Membangun converter berarti memuat model, dan
   ``convert()`` adalah pekerjaan CPU berat. Keduanya dijalankan lewat
   ``asyncio.to_thread``; converter-nya sendiri dibangun sekali per proses
   (double-checked locking) karena pemuatan model mahal.
3. **Kegagalan diterjemahkan.** Seluruh exception Docling dipetakan ke error
   domain. Pesan asli hanya masuk log server-side, karena dapat memuat path
   internal atau potongan isi dokumen.

Konfigurasi (lihat ``src/config/settings.py`` dan ``backend/.env.example``):

- ``RPS_CONVERTER_OCR`` — jalankan OCR untuk halaman tanpa lapisan teks (default
  aktif, mengikuti default Docling; RPS hasil pindai tetap terbaca);
- ``RPS_CONVERTER_TABLE_STRUCTURE`` — ekstraksi struktur tabel (default aktif:
  tabel distribusi mingguan/bobot penilaian adalah data akademik);
- ``RPS_CONVERTER_TABLE_MODE`` — ``accurate`` atau ``fast``;
- ``RPS_CONVERTER_ARTIFACTS_PATH`` — direktori model yang sudah diunduh lebih
  dulu (``docling-tools models download``), dipakai untuk deployment offline.

Model diunduh saat pemakaian pertama (layout ±172 MB + TableFormer ±358 MB) dan
disimpan pada cache Docling (``$HOME/.cache/docling/models``, dapat diarahkan
lewat ``DOCLING_CACHE_DIR``).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from io import BytesIO
from typing import Any

from src.config.settings import RPS_TABLE_MODES
from src.services.rps.converter import (
    ConvertedTable,
    DocumentConversion,
    DocumentConverter,
)
from src.services.rps.errors import (
    DocumentConversionError,
    DocumentConverterUnavailableError,
)

__all__ = ["DOCLING_PACKAGE", "DoclingDocumentConverter"]

DOCLING_PACKAGE = "docling"

# Perintah yang disebutkan pada pesan kegagalan bila extra belum terpasang.
DOCLING_INSTALL_HINT = "uv sync --extra docling"

# Mode TableFormer yang dikenal berasal dari config.settings (RPS_TABLE_MODES)
# agar konfigurasi dan adapter tidak dapat menyimpang satu sama lain.
TABLE_MODES = RPS_TABLE_MODES


@dataclass(slots=True)
class _DoclingApi:
    """Referensi ke API Docling yang sudah diimpor dan siap dipakai."""

    converter: Any
    document_stream: Any
    conversion_error: type[BaseException]
    version: str


class DoclingDocumentConverter(DocumentConverter):
    """Konversi dokumen memakai Docling."""

    name = DOCLING_PACKAGE

    def __init__(
        self,
        *,
        do_ocr: bool = True,
        do_table_structure: bool = True,
        table_mode: str = "accurate",
        artifacts_path: str | None = None,
    ) -> None:
        mode = (table_mode or "").strip().lower()
        if mode not in TABLE_MODES:
            raise ValueError(
                f"mode tabel tidak dikenal: {table_mode!r}; pilihan: {', '.join(TABLE_MODES)}"
            )

        self._do_ocr = do_ocr
        self._do_table_structure = do_table_structure
        self._table_mode = mode
        self._artifacts_path = artifacts_path or None

        # API Docling diimpor dan converter dibangun saat konversi pertama,
        # bukan saat konstruksi: aplikasi tetap dapat start tanpa extra Docling.
        self._api: _DoclingApi | None = None
        self._build_lock = asyncio.Lock()

    @property
    def version(self) -> str:
        """Versi Docling yang terpasang, atau ``"unknown"`` bila tidak terbaca."""
        try:
            return package_version(DOCLING_PACKAGE)
        except PackageNotFoundError:
            return "unknown"

    async def convert(self, *, content: bytes, file_name: str) -> DocumentConversion:
        """Konversi isi dokumen RPS menjadi markdown, JSON, YAML, dan tabel.

        ``content`` adalah isi berkas (bukan path), sehingga service tidak perlu
        menyerahkan lokasi penyimpanan kepada library konversi.
        """
        if not content:
            raise DocumentConversionError("isi dokumen kosong")

        api = await self._ensure_api()
        document = await self._convert_document(api, content=content, file_name=file_name)

        markdown = _export_markdown(document)
        if not markdown.strip():
            # Dokumen tanpa teks yang dapat diekstrak (mis. PDF hasil pindai
            # dengan OCR nonaktif) bukan "berhasil dikonversi": menyimpannya
            # sebagai source_markdown kosong akan membuat tahap berikutnya
            # bekerja dengan bahan yang tidak ada.
            raise DocumentConversionError(
                "konversi menghasilkan markdown kosong; dokumen tidak memuat teks "
                "yang dapat diekstrak (aktifkan RPS_CONVERTER_OCR untuk dokumen pindai)"
            )

        return DocumentConversion(
            markdown=markdown,
            document_json=_export_json(document),
            document_yaml=_export_yaml(document),
            tables=_export_tables(document),
            converter_name=self.name,
            converter_version=api.version,
        )

    async def _ensure_api(self) -> _DoclingApi:
        """Bangun API Docling sekali per proses (pemuatan model itu mahal)."""
        if self._api is not None:
            return self._api

        async with self._build_lock:
            if self._api is None:
                self._api = await asyncio.to_thread(self._build_api)
        return self._api

    def _build_api(self) -> _DoclingApi:
        """Impor Docling dan bangun ``DocumentConverter`` (berjalan di thread)."""
        try:
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import (
                PdfPipelineOptions,
                TableFormerMode,
                TableStructureOptions,
            )
            from docling.document_converter import DocumentConverter as DoclingConverter
            from docling.document_converter import PdfFormatOption
            from docling.exceptions import ConversionError
        except ImportError as exc:
            raise DocumentConverterUnavailableError(
                f"dokumen tidak dapat diproses: paket '{DOCLING_PACKAGE}' belum terpasang "
                f"(jalankan `{DOCLING_INSTALL_HINT}`); detail: {exc}"
            ) from exc

        options = PdfPipelineOptions()
        options.do_ocr = self._do_ocr
        options.do_table_structure = self._do_table_structure
        if self._do_table_structure:
            options.table_structure_options = TableStructureOptions(
                do_cell_matching=True,
                mode=TableFormerMode.ACCURATE
                if self._table_mode == "accurate"
                else TableFormerMode.FAST,
            )
        if self._artifacts_path:
            # Menunjuk model yang sudah diunduh; tanpa ini Docling memakai cache
            # bawaannya dan mengunduh model saat pemakaian pertama.
            options.artifacts_path = self._artifacts_path

        try:
            converter = DoclingConverter(
                format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
            )
        except FileNotFoundError as exc:
            raise DocumentConverterUnavailableError(
                "dokumen tidak dapat diproses: berkas model Docling tidak ditemukan "
                f"(periksa RPS_CONVERTER_ARTIFACTS_PATH / DOCLING_CACHE_DIR); detail: {exc}"
            ) from exc
        except (RuntimeError, OSError, ImportError) as exc:
            raise DocumentConverterUnavailableError(
                f"dokumen tidak dapat diproses: konverter Docling gagal disiapkan "
                f"({type(exc).__name__}); detail: {exc}"
            ) from exc

        return _DoclingApi(
            converter=converter,
            document_stream=_resolve_document_stream(),
            conversion_error=ConversionError,
            version=self.version,
        )

    async def _convert_document(
        self, api: _DoclingApi, *, content: bytes, file_name: str
    ) -> Any:
        """Jalankan konversi Docling di luar event loop dan petakan kegagalannya."""
        stream = api.document_stream(name=file_name, stream=BytesIO(content))
        try:
            result = await asyncio.to_thread(api.converter.convert, stream)
        except api.conversion_error as exc:
            # Docling membungkus kegagalan backend (dokumen rusak/terenkripsi)
            # sebagai ConversionError dengan penyebab asli pada __cause__.
            raise DocumentConversionError(
                f"konversi dokumen gagal: {_summarize_docling_error(exc)}"
            ) from exc
        except FileNotFoundError as exc:
            # Model hilang saat runtime (mis. cache terhapus) — masalah
            # lingkungan, bukan dokumen.
            raise DocumentConverterUnavailableError(
                f"dokumen tidak dapat diproses: berkas model Docling tidak ditemukan; detail: {exc}"
            ) from exc
        except PermissionError as exc:
            # Cache model tidak dapat ditulis/dibaca (izin filesystem atau
            # direktori yang dipakai bersama). Juga masalah lingkungan.
            raise DocumentConverterUnavailableError(
                "dokumen tidak dapat diproses: direktori cache model Docling tidak "
                f"dapat diakses (periksa DOCLING_CACHE_DIR / HF_HOME); detail: {exc}"
            ) from exc
        except (MemoryError, OSError) as exc:
            raise DocumentConversionError(
                f"konversi dokumen gagal pada sisi sumber daya: {type(exc).__name__}"
            ) from exc
        except Exception as exc:
            raise DocumentConversionError(
                f"konversi dokumen gagal: {type(exc).__name__}"
            ) from exc

        document = getattr(result, "document", None)
        if document is None:
            raise DocumentConversionError("konversi tidak menghasilkan dokumen")
        return document


def _resolve_document_stream() -> Any:
    """Temukan kelas ``DocumentStream`` Docling pada lokasi yang dikenal.

    Docling pernah memindahkan kelas ini antar modul, sehingga lokasinya dicari
    di beberapa kandidat: lebih baik menerima ketidakpastian kecil ini daripada
    mengunci ke satu path internal yang dapat berubah pada rilis berikutnya.
    """
    candidates = (
        ("docling.datamodel.base_models", "DocumentStream"),
        ("docling.datamodel.document", "DocumentStream"),
    )
    for module_name, attribute in candidates:
        try:
            module = __import__(module_name, fromlist=[attribute])
        except ImportError:
            continue
        stream_class = getattr(module, attribute, None)
        if stream_class is not None:
            return stream_class

    raise DocumentConverterUnavailableError(
        "dokumen tidak dapat diproses: kelas DocumentStream tidak ditemukan pada "
        "instalasi Docling ini (versi tidak kompatibel)"
    )


def _summarize_docling_error(exc: BaseException) -> str:
    """Ringkas kegagalan Docling tanpa membocorkan isi dokumen ke client.

    Ringkasan ini hanya dipakai untuk pesan log/publik generic; penyebab asli
    tetap tersimpan sebagai ``__cause__`` sehingga tetap muncul di traceback
    server-side.
    """
    cause = exc.__cause__
    if cause is not None:
        return f"{type(exc).__name__} ({type(cause).__name__})"
    return type(exc).__name__


def _export_markdown(document: Any) -> str:
    """Markdown normalisasi; Docling merender tabel sebagai tabel pipe GFM."""
    try:
        return document.export_to_markdown()
    except Exception as exc:
        raise DocumentConversionError(
            f"gagal mengekspor markdown dari dokumen: {type(exc).__name__}"
        ) from exc


def _export_json(document: Any) -> dict[str, Any]:
    """Representasi penuh dokumen (DoclingDocument) sebagai dict."""
    try:
        payload = document.export_to_dict()
    except Exception as exc:
        raise DocumentConversionError(
            f"gagal mengekspor JSON dari dokumen: {type(exc).__name__}"
        ) from exc
    if not isinstance(payload, dict):
        raise DocumentConversionError("ekspor JSON dokumen bukan berupa object")
    return payload


def _export_yaml(document: Any) -> str:
    """Representasi YAML dari dokumen yang sama dengan :func:`_export_json`.

    Docling menyediakan ``export_to_yaml``; bila versi yang terpasang tidak
    memilikinya, YAML dibangun dari JSON agar artefak YAML tetap tersedia (BE-05
    meminta JSON **dan** YAML).
    """
    exporter = getattr(document, "export_to_yaml", None)
    if callable(exporter):
        try:
            return exporter()
        except Exception as exc:
            raise DocumentConversionError(
                f"gagal mengekspor YAML dari dokumen: {type(exc).__name__}"
            ) from exc

    return _dump_yaml(_export_json(document))


def _dump_yaml(payload: dict[str, Any]) -> str:
    """Serialisasi dict ke YAML sebagai fallback bila Docling tidak menyediakannya."""
    try:
        import yaml
    except ImportError as exc:
        raise DocumentConverterUnavailableError(
            "dokumen tidak dapat diproses: paket 'pyyaml' tidak tersedia untuk "
            "menghasilkan representasi YAML"
        ) from exc

    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)


def _export_tables(document: Any) -> list[ConvertedTable]:
    """Ekstrak seluruh tabel beserta struktur baris/kolomnya.

    Tabel adalah data akademik pada RPS (distribusi mingguan, bobot penilaian),
    sehingga strukturnya dipisahkan dari markdown: baris/kolom dapat dibaca
    langsung oleh tahap ekstraksi (BE-08) tanpa mem-parsing markdown kembali.
    """
    tables: list[ConvertedTable] = []
    for index, table in enumerate(getattr(document, "tables", []) or []):
        tables.append(
            ConvertedTable(
                index=index,
                markdown=_table_text(table, document, "export_to_markdown"),
                page=_table_page(table),
                caption=_table_caption(table, document),
                html=_table_text(table, document, "export_to_html") or None,
                cells=_table_cells(table, document),
            )
        )
    return tables


def _table_text(table: Any, document: Any, exporter_name: str) -> str:
    """Panggil exporter tabel (``export_to_markdown``/``export_to_html``).

    Docling memerlukan ``doc=`` agar penggabungan sel dan referensi isi dapat
    diselesaikan; tanpa itu hasilnya kosong atau memunculkan peringatan
    deprecation.
    """
    exporter = getattr(table, exporter_name, None)
    if not callable(exporter):
        return ""
    try:
        return exporter(doc=document) or ""
    except Exception:
        return ""


def _table_cells(table: Any, document: Any) -> list[list[str]]:
    """Baris/kolom tabel sebagai teks, memakai exporter dataframe Docling."""
    exporter = getattr(table, "export_to_dataframe", None)
    if not callable(exporter):
        return []
    try:
        frame = exporter(doc=document)
        return [
            ["" if cell is None else str(cell) for cell in row]
            for row in frame.fillna("").astype(str).values.tolist()
        ]
    except Exception:
        return []


def _table_page(table: Any) -> int | None:
    """Nomor halaman tabel menurut Docling (``None`` bila tidak dilaporkan)."""
    provenance = getattr(table, "prov", None) or []
    if not provenance:
        return None
    page = getattr(provenance[0], "page_no", None)
    return page if isinstance(page, int) else None


def _table_caption(table: Any, document: Any) -> str | None:
    """Caption tabel bila Docling mengenalinya."""
    caption = getattr(table, "caption_text", None)
    if not callable(caption):
        return None
    try:
        text = caption(document)
    except Exception:
        return None
    return text or None
