"""Port konversi dokumen (BE-05.2).

Pipeline BE-05 adalah: **dokumen RPS → representasi terstruktur**. Tahap itu
dipisahkan menjadi sebuah *port* (:class:`DocumentConverter`) dengan alasan yang
sama seperti provider LLM pada BE-03:

1. **Docling adalah pilihan, bukan kontrak.** Service hanya tahu "ada konverter
   yang mengubah dokumen menjadi markdown, JSON, YAML, dan tabel". Mengganti
   atau menambah konverter berarti menambah satu adapter, bukan mengubah
   service.
2. **Dependensinya berat dan opsional.** Docling menarik torch dan model ML
   (ratusan MB–GB), sehingga ia dipasang sebagai *extra* opsional: `uv sync
   --extra docling`. Tanpa extra tersebut, konverter gagal dengan error domain
   yang jelas — bukan ImportError mentah yang membingungkan operator.
3. **Pengujian tidak perlu menjalankan ML.** Test suite memakai konverter
   pengganti, sehingga dapat dijalankan di CI ringan tanpa model.

Hasil konversi membawa empat representasi sekaligus, sesuai kebutuhan BE-05:

- ``markdown`` — representasi normalisasi yang disimpan pada kolom
  ``rps.source_markdown`` (data-model §8) dan dibaca manusia;
- ``document_json`` — representasi penuh mesin (DoclingDocument) untuk diproses
  ulang tanpa konversi ulang;
- ``document_yaml`` — bentuk yang sama dalam YAML, untuk dibaca/di-diff manusia;
- ``tables`` — struktur tabel yang dipisahkan, karena tabel RPS (mis. distribusi
  mingguan dan bobot penilaian) adalah data akademik yang tidak boleh hilang
  menjadi teks rata.

JSON/YAML/tabel berukuran besar dan tidak perlu di-query, sehingga disimpan
sebagai artefak di samping dokumen asli (lihat
:mod:`src.services.rps.storage`), bukan di dalam kolom database.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "ConvertedTable",
    "DocumentConversion",
    "DocumentConverter",
]


@dataclass(frozen=True, slots=True)
class ConvertedTable:
    """Satu tabel yang ditemukan pada dokumen.

    Menyimpan beberapa bentuk sekaligus dengan sengaja: ``markdown`` enak dibaca
    pada ``source_markdown``, ``html`` mempertahankan penggabungan sel (rowspan/
    colspan) yang tidak dapat diwakili tabel markdown, dan ``cells`` memudahkan
    tahap ekstraksi (BE-08) membaca baris/kolom tanpa mem-parsing ulang.
    """

    index: int
    markdown: str
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
            "markdown": self.markdown,
            "html": self.html,
            "cells": self.cells,
        }


@dataclass(frozen=True, slots=True)
class DocumentConversion:
    """Hasil lengkap konversi satu dokumen.

    ``converter_name`` dan ``converter_version`` ikut dibawa supaya hasil yang
    tersimpan dapat dilacak ke versi konverter yang menghasilkannya — penting
    ketika kualitas konversi berubah setelah upgrade (bandingkan prinsip
    traceability pada content-schema §3.3).
    """

    markdown: str
    document_json: dict[str, Any]
    document_yaml: str
    tables: list[ConvertedTable]
    converter_name: str
    converter_version: str

    @property
    def table_count(self) -> int:
        return len(self.tables)


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
