"""Test adapter Docling (BE-05.2, dikoreksi BE-13).

Docling memasang torch dan model ML, sehingga tidak semua perilakunya dapat
diuji sebagai bagian dari suite default. Yang diuji di sini adalah **kontrak
adapter**, bukan kualitas model Docling:

- Docling diimpor secara *lazy*: tanpa paketnya, aplikasi tetap berjalan dan
  kegagalan muncul sebagai error domain yang menyebutkan cara memasangnya —
  bukan ``ModuleNotFoundError`` mentah;
- pemetaan hasil Docling memakai ekspor **JSON** (DL-008), tanpa pernah
  memanggil ``export_to_markdown`` dan tanpa membentuk YAML;
- struktur tabel beserta nomor halaman tetap tersedia pada hasil konversi;
- pesan publik tidak membocorkan nama paket/path internal.

Konversi sungguhan dijalankan sebagai test opt-in
(:func:`test_the_sample_rps_is_converted_to_json`) memakai dokumen pada
``tests/fixtures/test.pdf`` — RPS 16 halaman dengan template program studi:

    RPS_DOCLING_LIVE_TEST=1 uv run pytest tests/test_rps_docling_converter.py -v -s

Path dokumen dapat diganti lewat ``RPS_DOCLING_TEST_PDF``. Model Docling diunduh
saat pemakaian pertama (±0,5 GB) dan disimpan pada cache Docling
(``DOCLING_CACHE_DIR``/``HF_HOME``).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.services.rps.converter import has_extractable_content
from src.services.rps.docling_converter import (
    DOCLING_INSTALL_HINT,
    DOCLING_PACKAGE,
    TABLE_MODES,
    DoclingDocumentConverter,
    _export_json,
    _export_tables,
)
from src.services.rps.errors import (
    DocumentConversionError,
    DocumentConverterUnavailableError,
)

PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"

# Dokumen RPS contoh: 16 halaman, tabel distribusi mingguan dan bobot penilaian.
FIXTURE_PDF = Path(__file__).parent / "fixtures" / "test.pdf"


class FakeFrame:
    """Tiruan ``pandas.DataFrame`` sebatas yang dipakai adapter."""

    def __init__(self, rows: list[list[object]]) -> None:
        self._rows = rows

    def fillna(self, _value):
        return self

    def astype(self, _type):
        return self

    @property
    def values(self):
        return SimpleNamespace(tolist=lambda: self._rows)


class FakeTable:
    """Tiruan ``TableItem`` Docling."""

    def __init__(self, *, rows=None, caption: str | None = "Distribusi Mingguan") -> None:
        self._rows = rows if rows is not None else [["Minggu", "Topik"], ["1", "Basis data"]]
        self._caption = caption
        self.prov = [SimpleNamespace(page_no=2)]

    def export_to_markdown(self, doc=None) -> str:
        raise AssertionError("adapter tidak boleh mengekspor Markdown dari RPS")

    def export_to_html(self, doc=None) -> str:
        assert doc is not None, "adapter wajib meneruskan doc= agar sel dapat diselesaikan"
        return "<table><tr><td>1</td></tr></table>"

    def export_to_dataframe(self, doc=None):
        return FakeFrame(self._rows)

    def caption_text(self, doc=None) -> str | None:
        return self._caption


class FakeDocument:
    """Tiruan ``DoclingDocument`` dengan teks, tabel, dan nomor halaman."""

    def __init__(self, *, tables=None) -> None:
        self.tables = tables if tables is not None else [FakeTable()]

    def export_to_markdown(self) -> str:
        raise AssertionError("adapter tidak boleh mengekspor Markdown dari RPS")

    def export_to_yaml(self) -> str:
        raise AssertionError("adapter tidak boleh membentuk YAML dari RPS")

    def export_to_dict(self) -> dict:
        return {
            "schema_name": "DoclingDocument",
            "pages": {
                "1": {"page_no": 1, "size": {"width": 612, "height": 792}},
                "2": {"page_no": 2, "size": {"width": 612, "height": 792}},
            },
            "texts": [
                {
                    "label": "section_header",
                    "text": "CPMK",
                    "prov": [{"page_no": 1}],
                }
            ],
            "tables": [
                {
                    "label": "table",
                    "prov": [{"page_no": 2}],
                    "data": {"num_rows": 2, "num_cols": 2},
                }
            ],
        }


class JsonOnlyConverter(DoclingDocumentConverter):
    """Adapter dengan API Docling palsu: cukup untuk menguji jalur ekspor."""

    async def _ensure_api(self):
        return SimpleNamespace(version="test-1")

    async def _convert_document(self, api, *, content: bytes, file_name: str):
        return FakeDocument()


# --- Kontrak konverter -----------------------------------------------------


def test_converter_is_named_docling():
    assert DoclingDocumentConverter.name == DOCLING_PACKAGE == "docling"


def test_docling_is_not_imported_until_it_is_actually_needed():
    """Aplikasi harus tetap dapat start tanpa extra Docling."""
    converter = DoclingDocumentConverter()

    assert converter._api is None


@pytest.mark.parametrize("mode", TABLE_MODES)
def test_supported_table_modes_are_accepted(mode):
    assert DoclingDocumentConverter(table_mode=mode)._table_mode == mode


def test_an_unknown_table_mode_fails_fast():
    with pytest.raises(ValueError):
        DoclingDocumentConverter(table_mode="super")


def test_version_is_reported_even_without_a_conversion():
    assert DoclingDocumentConverter().version  # "unknown" bila metadata tidak terbaca


@pytest.mark.asyncio
async def test_empty_content_never_reaches_docling():
    converter = DoclingDocumentConverter()

    with pytest.raises(DocumentConversionError):
        await converter.convert(content=b"", file_name="rps.pdf")


@pytest.mark.asyncio
async def test_a_missing_docling_package_is_a_domain_error_not_an_import_error(monkeypatch):
    """Operator harus tahu apa yang harus dijalankan; client tidak perlu detailnya."""
    monkeypatch.setitem(sys.modules, "docling.document_converter", None)

    converter = DoclingDocumentConverter()

    with pytest.raises(DocumentConverterUnavailableError) as excinfo:
        await converter.convert(content=PDF_BYTES, file_name="rps.pdf")

    assert DOCLING_INSTALL_HINT in excinfo.value.log_message
    # Kontrak publik tetap generic dan memakai kode error dari design-api §18.
    assert excinfo.value.error_code == "RPS_PROCESSING_FAILED"
    assert excinfo.value.status_code == 500
    assert excinfo.value.public_message == "Pemrosesan RPS gagal."
    assert "docling" not in excinfo.value.public_message.lower()


@pytest.mark.asyncio
async def test_an_unavailable_converter_is_still_a_conversion_error(monkeypatch):
    """Pemanggil dapat menangani seluruh kegagalan konversi lewat satu tipe."""
    monkeypatch.setitem(sys.modules, "docling.document_converter", None)

    with pytest.raises(DocumentConversionError):
        await DoclingDocumentConverter().convert(content=PDF_BYTES, file_name="rps.pdf")


# --- Pemetaan hasil Docling ------------------------------------------------


@pytest.mark.asyncio
async def test_conversion_exports_json_and_never_markdown():
    """DL-008/BE-13: satu-satunya ekspor dokumen adalah JSON Docling."""
    result = await JsonOnlyConverter().convert(content=PDF_BYTES, file_name="rps.pdf")

    assert result.document_json["schema_name"] == "DoclingDocument"
    assert result.document_json["pages"]["2"]["page_no"] == 2
    assert result.document_json["tables"][0]["prov"][0]["page_no"] == 2
    assert result.converter_name == "docling"
    assert result.converter_version == "test-1"


def test_json_export_must_be_an_object():
    class NotAnObject(FakeDocument):
        def export_to_dict(self):
            return ["bukan", "object"]

    with pytest.raises(DocumentConversionError):
        _export_json(NotAnObject())

    assert _export_json(FakeDocument())["schema_name"] == "DoclingDocument"


def test_a_document_without_text_or_tables_is_not_a_usable_result():
    """Dokumen pindai tanpa OCR tidak boleh dianggap berhasil dikonversi."""
    assert has_extractable_content({"texts": [{"text": "CPMK"}]})
    assert has_extractable_content({"tables": [{"prov": [{"page_no": 2}]}]})
    assert not has_extractable_content({"pages": {"1": {}}, "texts": [], "tables": []})
    assert not has_extractable_content({})


def test_tables_keep_their_structure_and_page_numbers():
    converter_tables = _export_tables(FakeDocument())

    assert len(converter_tables) == 1
    table = converter_tables[0]
    assert table.index == 0
    assert table.page == 2
    assert table.caption == "Distribusi Mingguan"
    assert table.html.startswith("<table>")
    assert table.cells == [["Minggu", "Topik"], ["1", "Basis data"]]
    assert (table.num_rows, table.num_cols) == (2, 2)


def test_table_cells_tolerate_missing_values_and_uneven_rows():
    table = _export_tables(
        FakeDocument(tables=[FakeTable(rows=[["a", None, "c"], ["d"]])])
    )[0]

    assert table.cells == [["a", "", "c"], ["d"]]
    assert (table.num_rows, table.num_cols) == (2, 3)


def test_one_broken_table_does_not_lose_the_rest_of_the_document():
    class BrokenTable(FakeTable):
        def export_to_html(self, doc=None) -> str:
            raise RuntimeError("tabel rusak")

        def export_to_dataframe(self, doc=None):
            raise RuntimeError("tabel rusak")

    tables = _export_tables(FakeDocument(tables=[BrokenTable(), FakeTable(caption=None)]))

    assert len(tables) == 2
    assert tables[0].html is None
    assert tables[0].cells == []
    assert tables[1].cells == [["Minggu", "Topik"], ["1", "Basis data"]]
    assert tables[1].caption is None


def test_a_document_without_tables_reports_none():
    assert _export_tables(FakeDocument(tables=[])) == []


def test_table_dict_is_ready_to_be_serialized_as_an_artifact():
    payload = _export_tables(FakeDocument())[0].to_dict()

    assert payload["num_rows"] == 2
    assert payload["num_cols"] == 2
    assert payload["page"] == 2
    assert payload["cells"][1] == ["1", "Basis data"]
    assert "markdown" not in payload


# --- Konversi sungguhan (opt-in) -------------------------------------------


def test_the_sample_rps_fixture_is_present_and_readable():
    """Fixture adalah bahan test live; berkas yang hilang harus terlihat jelas."""
    assert FIXTURE_PDF.is_file(), f"fixture RPS tidak ditemukan: {FIXTURE_PDF}"

    content = FIXTURE_PDF.read_bytes()

    assert content.startswith(b"%PDF-")
    assert len(content) > 10_000  # dokumen RPS nyata, bukan contoh satu halaman


@pytest.mark.skipif(
    os.getenv("RPS_DOCLING_LIVE_TEST") != "1",
    reason="opt-in live Docling test: set RPS_DOCLING_LIVE_TEST=1",
)
@pytest.mark.asyncio
async def test_the_sample_rps_is_converted_to_json():
    """Membuktikan pipeline Docling benar-benar bekerja pada dokumen RPS nyata.

    Memakai ``tests/fixtures/test.pdf`` (RPS 16 halaman dengan template program
    studi), atau path lain bila ``RPS_DOCLING_TEST_PDF`` diisi. Yang diperiksa
    adalah acceptance criteria BE-13: JSON menyimpan teks, tabel CPMK/rencana
    mingguan, dan nomor halaman.
    """
    pdf_path = Path(os.environ.get("RPS_DOCLING_TEST_PDF") or FIXTURE_PDF)
    if not pdf_path.is_file():
        pytest.skip(f"berkas PDF tidak ditemukan: {pdf_path}")

    converter = DoclingDocumentConverter()

    result = await converter.convert(
        content=pdf_path.read_bytes(), file_name=pdf_path.name
    )

    assert result.converter_name == "docling"
    assert result.converter_version != ""
    document = result.document_json
    assert document["schema_name"] == "DoclingDocument"

    texts = document.get("texts") or []
    tables = document.get("tables") or []
    assert texts, "RPS contoh harus menghasilkan teks"
    assert tables, "RPS contoh harus menghasilkan tabel"
    assert result.table_count > 0

    # Nomor halaman tersedia pada provenance tabel yang disimpan.
    page_numbers = [
        provenance.get("page_no")
        for table in tables
        for provenance in (table.get("prov") or [])
    ]
    assert page_numbers
    assert all(isinstance(page, int) for page in page_numbers)

    # Tabel akademik RPS (CPMK dan rencana mingguan) harus terbaca, baik sebagai
    # teks dokumen maupun sebagai sel tabel.
    table_cells = [
        cell.get("text", "")
        for table in tables
        for cell in ((table.get("data") or {}).get("table_cells") or [])
    ]
    text = " ".join(
        [item.get("text", "") for item in texts] + table_cells
    ).upper()
    assert "CPMK" in text
    assert "MINGGU" in text or "RENCANA" in text

    print(
        f"\ndocling {result.converter_version}: {len(texts)} teks, "
        f"{result.table_count} tabel, halaman: {sorted(set(page_numbers))}"
    )
