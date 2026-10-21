"""Test serializer YAML input LLM (BE-08.1).

Dua janji yang diuji:

1. ``document_to_yaml`` memuat teks, heading, tabel, dan nomor halaman yang
   relevan — tanpa identitas dosen maupun header/footer halaman.
2. ``structured_data_to_yaml`` hanya memuat field akademik (content-schema
   §6.1/§6.3), tanpa metadata ekstraksi dan tanpa nilai kosong.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
import pytest

from src.schemas.rps_structured import RPSStructuredData
from src.services.rps.errors import RPSValidationError
from src.services.rps.yaml_export import (
    LLM_FIELDS,
    document_to_yaml,
    structured_data_to_yaml,
)

DOSEN_NAME = "Ramadhan Paninggalih"

SOURCE_DOCUMENT = {
    "schema_name": "DoclingDocument",
    "pages": {"1": {"page_no": 1}, "2": {"page_no": 2}, "3": {"page_no": 3}},
    "texts": [
        # Header halaman: di sinilah identitas dosen tercetak.
        {
            "self_ref": "#/texts/0",
            "label": "page_header",
            "content_layer": "furniture",
            "text": f"RPS Basis Data — Dosen Pengampu: {DOSEN_NAME}",
            "prov": [{"page_no": 1}],
        },
        {
            "self_ref": "#/texts/1",
            "label": "section_header",
            "content_layer": "body",
            "text": "CAPAIAN PEMBELAJARAN MATA KULIAH",
            "prov": [{"page_no": 1}],
        },
        {
            "self_ref": "#/texts/2",
            "label": "text",
            "content_layer": "body",
            "text": "CPMK-1: Mahasiswa mampu merancang basis data relasional.",
            "prov": [{"page_no": 1}],
        },
        {
            "self_ref": "#/texts/3",
            "label": "caption",
            "content_layer": "body",
            "text": "Tabel 1. Distribusi Mingguan",
            "prov": [{"page_no": 2}],
        },
        {
            "self_ref": "#/texts/4",
            "label": "text",
            "content_layer": "furniture",
            "text": "Halaman 2 dari 3",
            "prov": [{"page_no": 2}],
        },
        {
            "self_ref": "#/texts/4",
            "label": "text",
            "content_layer": "body",
            "text": "UTS dilaksanakan pada minggu 8.",
            "prov": [{"page_no": 3}],
        },
        # Header template yang diulang di setiap halaman, bukan header semantik.
        {
            "self_ref": "#/texts/6",
            "label": "text",
            "content_layer": "body",
            "text": "No. Dok.",
            "prov": [{"page_no": 1}],
        },
        {
            "self_ref": "#/texts/7",
            "label": "text",
            "content_layer": "body",
            "text": "No. Dok.",
            "prov": [{"page_no": 2}],
        },
        {
            "self_ref": "#/texts/8",
            "label": "text",
            "content_layer": "body",
            "text": "No. Dok.",
            "prov": [{"page_no": 3}],
        },
        {
            "self_ref": "#/texts/9",
            "label": "text",
            "content_layer": "body",
            "text": "NIDN : 07 1234 5678",
            "prov": [{"page_no": 1}],
        },
    ],
    "tables": [
        {
            "self_ref": "#/tables/0",
            "label": "table",
            "content_layer": "body",
            "prov": [{"page_no": 1}],
            "captions": [{"$ref": "#/texts/3"}],
            "data": {
                "num_rows": 2,
                "num_cols": 2,
                "table_cells": [
                    {"text": "Kode", "start_row_offset_idx": 0, "start_col_offset_idx": 0},
                    {"text": "Rumusan CPMK", "start_row_offset_idx": 0, "start_col_offset_idx": 1},
                    {"text": "CPMK-1", "start_row_offset_idx": 1, "start_col_offset_idx": 0},
                    {
                        # Identitas dosen menyatu dalam satu sel hasil deteksi
                        # Docling; teks akademik setelahnya harus tetap utuh.
                        "text": "Merancang basis data relasional. DOSEN PENGAMPU "
                        f"{DOSEN_NAME} S.Si., M.Sc. OTORISASI PENYUSUN RPS "
                        "merumuskan capaian pembelajaran.",
                        "start_row_offset_idx": 1,
                        "start_col_offset_idx": 1,
                    },
                ],
            },
        },
        # Kisi administratif template (nomor dokumen, tanggal terbit, revisi).
        {
            "self_ref": "#/tables/2",
            "label": "table",
            "content_layer": "body",
            "prov": [{"page_no": 3}],
            "data": {
                "num_rows": 4,
                "num_cols": 2,
                "table_cells": [
                    {"text": "No. Dok.", "start_row_offset_idx": 0, "start_col_offset_idx": 0},
                    {"text": ": 01", "start_row_offset_idx": 0, "start_col_offset_idx": 1},
                    {"text": "Tgl. Terbit", "start_row_offset_idx": 1, "start_col_offset_idx": 0},
                    {"text": ": 05/08/2017", "start_row_offset_idx": 1, "start_col_offset_idx": 1},
                    {"text": "No. Revisi", "start_row_offset_idx": 2, "start_col_offset_idx": 0},
                    {"text": ": 01", "start_row_offset_idx": 2, "start_col_offset_idx": 1},
                    {"text": "Hal", "start_row_offset_idx": 3, "start_col_offset_idx": 0},
                    {"text": ": 3/3", "start_row_offset_idx": 3, "start_col_offset_idx": 1},
                ],
            },
        },
        {
            "self_ref": "#/tables/1",
            "label": "table",
            "content_layer": "body",
            "prov": [{"page_no": 2}],
            "data": {
                "num_rows": 3,
                "num_cols": 3,
                "table_cells": [
                    {"text": "Minggu", "start_row_offset_idx": 0, "start_col_offset_idx": 0},
                    {"text": "Topik", "start_row_offset_idx": 0, "start_col_offset_idx": 1},
                    {"text": "Metode", "start_row_offset_idx": 0, "start_col_offset_idx": 2},
                    {"text": "1", "start_row_offset_idx": 1, "start_col_offset_idx": 0},
                    {"text": "Pengenalan Basis Data", "start_row_offset_idx": 1, "start_col_offset_idx": 1},
                    {"text": "Kuliah", "start_row_offset_idx": 1, "start_col_offset_idx": 2},
                    {"text": "2", "start_row_offset_idx": 2, "start_col_offset_idx": 0},
                    {"text": "Model Relasional", "start_row_offset_idx": 2, "start_col_offset_idx": 1},
                    {"text": "Latihan", "start_row_offset_idx": 2, "start_col_offset_idx": 2},
                ],
            },
        },
    ],
}

STRUCTURED_DATA = {
    "schema_version": "2.0",
    "course": {"name": "Basis Data", "code": "IF123", "credits": 3, "description": ""},
    "cpl": [{"id": "CPL-1", "description": "Mampu merancang sistem informasi"}],
    "cpmk": [{"id": "CPMK-1", "description": "Merancang basis data relasional", "cpl_ids": ["CPL-1"]}],
    "sub_cpmk": [],
    "topics": [{"id": "TOP-1", "name": "Pengenalan Basis Data"}],
    "weeks": [
        {"week": 1, "topics": ["Pengenalan Basis Data"], "cpmk": ["CPMK-1"], "assessment": None},
        {"week": 8, "week_type": "uts", "topics": []},
    ],
    "teaching_methods": ["Kuliah", "Latihan"],
    "media": [],
    "assessments": [{"id": "AS-1", "type": "uts", "week": 8, "weight_percent": 30}],
    "references": [{"id": "REF-1", "citation": "Silberschatz, Database System Concepts", "year": 2019}],
    "extraction": {"extractor": "docling", "model_name": "gpt-4o", "source_pages": [1, 2]},
}


def load(yaml_text: str) -> dict:
    return yaml.safe_load(yaml_text)


# --- source_document → YAML -------------------------------------------------


def test_the_extracted_document_is_serialized_with_pages_and_blocks():
    payload = load(document_to_yaml(SOURCE_DOCUMENT))

    assert payload["page_count"] == 3
    assert payload["blocks"]
    # Setiap blok membawa nomor halaman.
    assert all("page" in block for block in payload["blocks"])


def test_blocks_are_ordered_by_page():
    pages = [block["page"] for block in load(document_to_yaml(SOURCE_DOCUMENT))["blocks"]]

    assert pages == sorted(pages)


def test_headings_and_paragraphs_are_kept_apart():
    blocks = load(document_to_yaml(SOURCE_DOCUMENT))["blocks"]

    assert {"page": 1, "heading": "CAPAIAN PEMBELAJARAN MATA KULIAH"} in blocks
    assert {
        "page": 1,
        "text": "CPMK-1: Mahasiswa mampu merancang basis data relasional.",
    } in blocks
    assert {"page": 3, "text": "UTS dilaksanakan pada minggu 8."} in blocks


def test_the_cpmk_and_weekly_plan_tables_are_complete():
    """Tabel CPMK dan rencana mingguan harus utuh, termasuk captionnya."""
    tables = [
        block["table"]
        for block in load(document_to_yaml(SOURCE_DOCUMENT))["blocks"]
        if "table" in block
    ]

    assert tables[0]["caption"] == "Tabel 1. Distribusi Mingguan"
    assert tables[0]["rows"][0] == ["Kode", "Rumusan CPMK"]
    assert tables[0]["rows"][1][0] == "CPMK-1"
    assert "merumuskan capaian pembelajaran." in tables[0]["rows"][1][1]
    # Header tabel akademik yang berulang di tiap halaman tetap dipertahankan.
    assert tables[1]["rows"][0] == ["Minggu", "Topik", "Metode"]
    assert ["1", "Pengenalan Basis Data", "Kuliah"] in tables[1]["rows"]
    assert ["2", "Model Relasional", "Latihan"] in tables[1]["rows"]


def test_page_headers_and_footers_never_reach_the_llm():
    """Identitas dosen tercetak pada header halaman: harus hilang."""
    yaml_text = document_to_yaml(SOURCE_DOCUMENT)

    assert DOSEN_NAME not in yaml_text
    assert "Dosen Pengampu" not in yaml_text
    assert "Halaman 2 dari 3" not in yaml_text
    # Isi akademik pada halaman yang sama tetap ada.
    assert "UTS dilaksanakan pada minggu 8." in yaml_text


def test_template_chrome_repeated_on_every_page_is_dropped():
    """Nomor dokumen/tanggal terbit diulang tiap halaman; bukan isi akademik."""
    yaml_text = document_to_yaml(SOURCE_DOCUMENT)

    assert "No. Dok." not in yaml_text
    # Kalimat akademik yang panjang tidak ikut terbuang meski muncul sekali.
    assert "UTS dilaksanakan pada minggu 8." in yaml_text


def test_the_lecturer_identifier_and_name_are_redacted_everywhere():
    yaml_text = document_to_yaml(SOURCE_DOCUMENT)

    assert DOSEN_NAME not in yaml_text
    assert "1234 5678" not in yaml_text
    assert "NIDN" not in yaml_text
    # Penanda pengganti, bukan penghapusan baris: teks akademik tetap ada.
    assert yaml_text.count("[identitas dihapus]") >= 2


def test_the_administrative_template_grid_is_dropped_from_tables():
    """Kisi nomor dokumen/tanggal terbit/No. Revisi/Hal bukan isi RPS."""
    yaml_text = document_to_yaml(SOURCE_DOCUMENT)

    for label in ("No. Dok.", "Tgl. Terbit", "No. Revisi", ": 05/08/2017", ": 3/3"):
        assert label not in yaml_text
    # Header akademik yang diulang pada banyak halaman tidak ikut terbuang.
    assert "Minggu" in yaml_text


def test_page_number_cells_are_dropped_from_tables():
    """Sel nomor halaman (": 4/16") bukan isi tabel."""
    document = {
        "pages": {"1": {"page_no": 1}},
        "texts": [],
        "tables": [
            {
                "label": "table",
                "prov": [{"page_no": 1}],
                "data": {
                    "num_rows": 2,
                    "num_cols": 2,
                    "table_cells": [
                        {"text": ": 4/16", "start_row_offset_idx": 0, "start_col_offset_idx": 0},
                        {
                            "text": "Materi Pembelajaran",
                            "start_row_offset_idx": 1,
                            "start_col_offset_idx": 0,
                        },
                        {
                            "text": "Himpunan",
                            "start_row_offset_idx": 1,
                            "start_col_offset_idx": 1,
                        },
                    ],
                },
            }
        ],
    }

    rows = load(document_to_yaml(document))["blocks"][0]["table"]["rows"]

    assert rows == [["Materi Pembelajaran", "Himpunan"]]


def test_a_document_without_content_produces_no_blocks():
    payload = load(document_to_yaml({"pages": {}, "texts": [], "tables": []}))

    assert payload == {"page_count": 0, "blocks": []}


def test_the_document_must_be_a_json_object():
    with pytest.raises(RPSValidationError):
        document_to_yaml(["bukan", "objek"])


# --- structured_data → YAML -------------------------------------------------


def test_the_structured_data_is_serialized_with_academic_fields_only():
    payload = load(structured_data_to_yaml(STRUCTURED_DATA))

    # Hanya field input LLM, dan urutannya mengikuti kontrak.
    assert list(payload) == [field for field in LLM_FIELDS if field in payload]
    assert "schema_version" not in payload
    assert "extraction" not in payload
    assert payload["cpmk"] == [
        {"id": "CPMK-1", "description": "Merancang basis data relasional", "cpl_ids": ["CPL-1"]}
    ]
    assert [week["week"] for week in payload["weeks"]] == [1, 8]


def test_empty_values_are_dropped_instead_of_serialized_as_nulls():
    payload = load(structured_data_to_yaml(STRUCTURED_DATA))

    assert "description" not in payload["course"]
    assert "sub_cpmk" not in payload
    assert "media" not in payload
    assert payload["weeks"][1] == {"week": 8, "week_type": "uts"}


def test_a_pydantic_structured_data_model_is_accepted():
    model = RPSStructuredData.model_validate(STRUCTURED_DATA)

    assert load(structured_data_to_yaml(model))["course"]["name"] == "Basis Data"


def test_the_analysis_must_contain_something_academic():
    with pytest.raises(RPSValidationError):
        structured_data_to_yaml({"schema_version": "2.0", "extraction": {"extractor": "docling"}})


@pytest.mark.parametrize("invalid", [None, "bukan objek", 42])
def test_the_analysis_must_be_an_object(invalid):
    with pytest.raises(RPSValidationError):
        structured_data_to_yaml(invalid)


# --- Konversi sungguhan (opt-in) -------------------------------------------

FIXTURE_PDF = Path(__file__).parent / "fixtures" / "test.pdf"


@pytest.mark.skipif(
    os.getenv("RPS_DOCLING_LIVE_TEST") != "1",
    reason="opt-in live Docling test: set RPS_DOCLING_LIVE_TEST=1",
)
@pytest.mark.asyncio
async def test_the_real_rps_fixture_produces_llm_ready_yaml():
    """Pipeline utuh pada RPS contoh: PDF → Docling (BE-13) → YAML (BE-08.1).

    Serializer sendiri tidak memanggil Docling — inputnya ``source_document``
    yang sudah dikonversi. Test ini menjaga asumsi itu pada dokumen sungguhan:
    RPS 16 halaman dengan kisi administratif, header halaman berisi identitas
    dosen, dan tabel rencana mingguan yang header-nya diulang tiap halaman.
    """
    from src.services.rps.docling_converter import DoclingDocumentConverter

    pdf_path = Path(os.environ.get("RPS_DOCLING_TEST_PDF") or FIXTURE_PDF)
    if not pdf_path.is_file():
        pytest.skip(f"berkas PDF tidak ditemukan: {pdf_path}")

    conversion = await DoclingDocumentConverter().convert(
        content=pdf_path.read_bytes(), file_name=pdf_path.name
    )
    yaml_text = document_to_yaml(conversion.document_json)
    payload = load(yaml_text)

    assert payload["page_count"] == 16
    assert payload["blocks"]

    # Tabel rencana mingguan ikut beserta header akademiknya.
    rows = [
        row
        for block in payload["blocks"]
        if "table" in block
        for row in block["table"]["rows"]
    ]
    flat = "\n".join(cell for row in rows for cell in row)
    assert "Sub-CPMK" in flat
    assert "Bahan Kajian" in flat

    # Tidak ada identitas dosen, kisi administratif, maupun nomor halaman.
    for absent in ("Paninggalih", "Dosen Pengampu", "Tgl. Terbit", "No. Dok.", ": 4/16"):
        assert absent not in yaml_text

    # YAML jauh lebih ringkas daripada JSON Docling apa adanya.
    assert len(yaml_text) < 40_000
