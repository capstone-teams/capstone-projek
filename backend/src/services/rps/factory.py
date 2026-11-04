"""Pemilihan konverter dan penyimpanan dokumen RPS (BE-05).

Mengikuti pola yang sama seperti :mod:`src.services.llm.factory`: service
bergantung pada port (:class:`~src.services.rps.converter.DocumentConverter`,
:class:`~src.services.rps.storage.DocumentStorage`), dan modul ini yang
memutuskan implementasi mana yang dipakai berdasarkan konfigurasi.

Bedanya dengan factory LLM: konverter Docling **mahal untuk dibangun** (memuat
model ML), sehingga hasilnya di-cache per proses. Seluruh request memakai
instance yang sama; model cukup dimuat sekali.
"""

from __future__ import annotations

from src.config.settings import get_settings
from src.services.rps.converter import DocumentConverter
from src.services.rps.docling_converter import DOCLING_PACKAGE, DoclingDocumentConverter
from src.services.rps.storage import DocumentStorage, LocalDocumentStorage

__all__ = [
    "CONVERTER_REGISTRY",
    "available_converters",
    "get_document_converter",
    "get_document_storage",
    "reset_document_converter",
    "reset_document_storage",
]

# Registry konverter yang didukung. Menambah konverter berarti menambah satu
# entri di sini; service tetap hanya bergantung pada DocumentConverter.
CONVERTER_REGISTRY: dict[str, type[DocumentConverter]] = {
    DOCLING_PACKAGE: DoclingDocumentConverter,
}

# Instance konverter per nama, dibangun sekali lalu dipakai ulang.
_instances: dict[str, DocumentConverter] = {}

# Instance penyimpanan (satu direktori root per proses).
_storage: DocumentStorage | None = None


def available_converters() -> list[str]:
    """Nama konverter yang terdaftar."""
    return sorted(CONVERTER_REGISTRY)


def get_document_converter(name: str | None = None) -> DocumentConverter:
    """Konverter dokumen sesuai konfigurasi (atau yang disebutkan eksplisit).

    Opsi Docling dibaca dari settings, sehingga perilaku konversi (OCR, struktur
    tabel, lokasi model) dapat diubah tanpa mengubah kode.
    """
    settings = get_settings()
    converter_name = (name or settings.rps_converter or DOCLING_PACKAGE).strip().lower()

    cached = _instances.get(converter_name)
    if cached is not None:
        return cached

    converter_class = CONVERTER_REGISTRY.get(converter_name)
    if converter_class is None:
        raise ValueError(
            f"konverter dokumen tidak dikenal: {converter_name!r}; "
            f"pilihan: {', '.join(available_converters())}"
        )

    converter = (
        converter_class(
            do_ocr=settings.rps_converter_ocr,
            do_table_structure=settings.rps_converter_table_structure,
            table_mode=settings.rps_converter_table_mode,
            artifacts_path=settings.rps_converter_artifacts_path,
        )
        if converter_name == DOCLING_PACKAGE
        else converter_class()
    )
    _instances[converter_name] = converter
    return converter


def reset_document_converter() -> None:
    """Lupakan instance yang di-cache.

    Dipakai pengujian (agar konfigurasi baru benar-benar terbaca) dan oleh
    operator setelah mengubah konfigurasi konverter.
    """
    _instances.clear()


def get_document_storage() -> DocumentStorage:
    """Penyimpanan dokumen sesuai konfigurasi (``RPS_STORAGE_DIR``)."""
    global _storage
    if _storage is None:
        _storage = LocalDocumentStorage(get_settings().rps_storage_path)
    return _storage


def reset_document_storage() -> None:
    """Lupakan instance penyimpanan yang di-cache (dipakai pengujian)."""
    global _storage
    _storage = None
