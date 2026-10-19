"""Port konversi dokumen (BE-05.2, dikoreksi BE-13).

Pipeline BE-05 adalah: **dokumen RPS → representasi terstruktur**. Tahap itu
dipisahkan menjadi sebuah *port* (:class:`DocumentConverter`) dengan alasan yang
sama seperti provider LLM pada BE-03:

1. **Docling adalah pilihan, bukan kontrak.** Service hanya tahu "ada konverter
   yang mengubah dokumen menjadi JSON Docling". Mengganti atau menambah
   konverter berarti menambah satu adapter, bukan mengubah service.
2. **Dependensinya berat dan opsional.** Docling menarik torch dan model ML
   (ratusan MB–GB), sehingga ia dipasang sebagai *extra* opsional: `uv sync
   --extra docling`. Tanpa extra tersebut, konverter gagal dengan error domain
   yang jelas — bukan ImportError mentah yang membingungkan operator.
3. **Pengujian tidak perlu menjalankan ML.** Test suite memakai konverter
   pengganti, sehingga dapat dijalankan di CI ringan tanpa model.

Hasil konversi **hanya** membawa satu representasi persisten (DL-008, BE-13):

- ``document_json`` — dokumen Docling lengkap (``DoclingDocument``) yang
  mempertahankan teks, heading, tabel, dan nomor halaman. Inilah yang disimpan
  pada kolom ``rps.source_document`` (data-model §8), sehingga BE-08 dapat
  memetakan field tanpa menjalankan Docling ulang;
- ``tables`` — struktur tabel yang dipisahkan sebagai artefak turunan, karena
  tabel RPS (mis. distribusi mingguan dan bobot penilaian) adalah data akademik
  yang tidak boleh hilang menjadi teks rata.

Markdown **tidak pernah dibentuk** dari RPS: DL-008 menetapkan JSON sebagai
satu-satunya format hasil Docling. YAML juga tidak dibentuk di sini — YAML baru
diserialisasi oleh BE-08.1 ketika benar-benar dibutuhkan sebagai input LLM
(DL-006), langsung dari ``source_document``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "ConvertedTable",
    "DocumentConversion",
    "DocumentConverter",
    "has_extractable_content",
]


@dataclass(frozen=True, slots=True)
class ConvertedTable:
    """Satu tabel yang ditemukan pada dokumen.

    ``html`` mempertahankan penggabungan sel (rowspan/colspan) yang tidak dapat
    diwakili struktur seragam, sedangkan ``cells`` memudahkan tahap ekstraksi
    (BE-08) membaca baris/kolom tanpa mem-parsing ulang. Nomor halaman disimpan
    agar setiap tabel tetap dapat dilacak ke sumbernya (content-schema §3.3).
    """

    index: int
    page: int | None = None
    caption: str | None = None
    html: str | None = None
    cells: list[list[str]] = field(default_factory=list)

    @property
    def num_rows(self) -> int:
        return len(self.cells)

    @property
    def num_cols(self) -> int:
        return max((len(row) for row in self.cells), default=0)

    def to_dict(self) -> dict[str, Any]:
        """Bentuk serializable untuk artefak ``tables.json``."""
        return {
            "index": self.index,
            "page": self.page,
            "caption": self.caption,
            "num_rows": self.num_rows,
            "num_cols": self.num_cols,
            "html": self.html,
            "cells": self.cells,
        }


@dataclass(frozen=True, slots=True)
class DocumentConversion:
    """Hasil lengkap konversi satu dokumen (JSON Docling, tanpa Markdown).

    ``converter_name`` dan ``converter_version`` ikut dibawa supaya hasil yang
    tersimpan dapat dilacak ke versi konverter yang menghasilkannya — penting
    ketika kualitas konversi berubah setelah upgrade (bandingkan prinsip
    traceability pada content-schema §3.3).
    """

    document_json: dict[str, Any]
    tables: list[ConvertedTable]
    converter_name: str
    converter_version: str

    @property
    def table_count(self) -> int:
        return len(self.tables)


def has_extractable_content(document_json: Mapping[str, Any]) -> bool:
    """Apakah JSON Docling memuat teks atau tabel yang dapat diekstrak.

    Dokumen pindai tanpa OCR menghasilkan struktur halaman tetapi daftar
    ``texts``/``tables`` yang kosong. Hasil seperti itu bukan konversi yang
    berhasil: menyimpannya sebagai ``source_document`` akan membuat tahap
    berikutnya bekerja dengan bahan yang tidak ada. Pemeriksaan ini menggantikan
    pemeriksaan "markdown kosong" pada BE-05.2.
    """
    return bool(document_json.get("texts") or document_json.get("tables"))


class DocumentConverter(ABC):
    """Interface konverter dokumen.

    Implementasi **wajib** aman dipanggil dari event loop: pekerjaan berat
    (parsing PDF, inferensi model) harus dijalankan di luar thread event loop.
    """

    #: Nama konverter, dipakai pada konfigurasi dan hasil konversi.
    name: str = "unknown"

    @property
    def version(self) -> str:
        """Versi implementasi konverter (``"unknown"`` bila tidak dapat dibaca)."""
        return "unknown"

    @abstractmethod
    async def convert(self, *, content: bytes, file_name: str) -> DocumentConversion:
        """Konversi isi dokumen menjadi representasi terstruktur.

        ``content`` adalah isi berkas asli dan ``file_name`` hanya dipakai untuk
        memberi tahu format/identitas dokumen kepada konverter — bukan untuk
        menyentuh filesystem. Kegagalan apa pun dilaporkan sebagai error domain
        (:class:`~src.services.rps.errors.DocumentConversionError`), bukan
        exception library mentah.
        """
