"""Serializer YAML sebagai input LLM (BE-08.1, DL-005/DL-006).

Dua sumber data RPS diserialisasi menjadi YAML ringkas, dan hanya ini yang
 boleh masuk ke prompt:

1. :func:`document_to_yaml` — ``rps.source_document`` (JSON Docling, BE-13)
   menjadi teks + heading + tabel + nomor halaman. Dipakai sebagai input tahap
   *RPS Analysis*.
2. :func:`structured_data_to_yaml` — ``rps.structured_data`` (RPS Structured
   Data, content-schema §6.2) menjadi YAML hanya untuk field akademik. Dipakai
   sebagai input tahap *course planning* (M03).

Aturan yang dijaga:

- **Tidak ada identitas dosen, data administratif, maupun metadata file.**
  Blok ``content_layer: furniture`` (header/footer halaman — di sanalah nama
  dosen, NIDN, dan nama program studi tercetak) dan label
  ``page_header``/``page_footer`` dilewati. Begitu pula ``extraction`` dan
  ``schema_version`` pada data terstruktur.
- **Tidak ada nilai kosong.** Field ``null``/string kosong/daftar kosong dibuang
  agar token tidak terbuang untuk lubang data.
- Bentuk YAML-nya adalah kontrak (DL-005) dan dijelaskan pada
  ``docs/02. design/content-schema.md`` §56.

Modul ini murni fungsi: tidak menyentuh database, HTTP, maupun Docling, sehingga
dapat dipakai ulang oleh service analisis (BE-09.2) dan orkestrator (BE-11.2).
"""

from __future__ import annotations

import re
from typing import Any

import yaml
from pydantic import BaseModel

from src.services.rps.errors import RPSValidationError

__all__ = [
    "HEADING_LABELS",
    "LLM_FIELDS",
    "document_to_yaml",
    "dump_yaml",
    "structured_data_to_yaml",
]

#: Label Docling yang ditampilkan sebagai ``heading`` (bukan paragraf biasa).
HEADING_LABELS = frozenset({"title", "section_header", "subtitle"})

#: Label yang selalu berupa header/footer halaman, apa pun ``content_layer``-nya.
PAGE_CHROME_LABELS = frozenset({"page_header", "page_footer"})

# Kalibrasi deteksi "chrome" halaman untuk template RPS kampus. Docling sering
# memberi header/footer template (nomor dokumen, tanggal terbit, logo kampus)
# sebagai ``content_layer: body`` biasa, sehingga pembeda satu-satunya adalah
# pengulangannya pada banyak halaman. Batas ini sengaja dibuat longgar di sisi
# panjang teks: kalimat akademik yang panjang tidak akan tersentuh.
CHROME_MIN_PAGES = 3
CHROME_MAX_CHARS = 60

# Identitas dosen pada RPS tercetak sebagai "Dosen Pengampu <nama>" atau di
# samping kolom tanda tangan, sering menyatu dengan sel tabel hasil deteksi
# Docling. Nilai yang dicocokkan **diganti penanda**, bukan dibuang, supaya teks
# akademik di sekitarnya tetap utuh.
IDENTITY_KEYWORDS = (
    r"dosen\s+pengampu",
    r"nama\s+dosen",
    r"dosen\s+pengajar",
    r"tanda\s+tangan",
    r"disusun\s+oleh",
    r"diverifikasi\s+oleh",
)

# Nama orang pada RPS ditulis dengan huruf kapital di awal kata ("Ramadhan
# Paninggalih") dan gelar berupa inisial ("S.Si.", "M.Sc."). Token HURUF BESAR
# semua ("OTORISASI", "PENYUSUN") adalah label template, jadi pencocokan berhenti
# di sana dan teks akademik setelahnya tidak ikut terhapus.
NAME_TOKEN = r"(?:[A-Z][a-z][\w'\-]*|[A-Z]\.(?:[A-Za-z]+\.)*)"

# Hanya kata kunci yang dicocokkan tanpa peduli huruf besar/kecil; pola nama
# tetap peka huruf karena kapitalisasi itulah penandanya.
IDENTITY_PATTERNS = (
    re.compile(
        rf"\b(?i:{'|'.join(IDENTITY_KEYWORDS)})\b[\s:.,\-]*"
        rf"(?:{NAME_TOKEN}[\s,]*)+"
    ),
    re.compile(r"\b(?i:nidn|nip|nik)\b[\s:.,\-]*[\d.\-\s]{4,}"),
)
IDENTITY_PLACEHOLDER = "[identitas dihapus]"

# Sel tabel yang hanya memuat nomor halaman, mis. ": 4/16" atau "4 / 16".
_PAGE_NUMBER_PATTERN = re.compile(r"^:?\s*\d+\s*/\s*\d+$")

# Baris kisi administratif template RPS (nomor dokumen, tanggal terbit, revisi,
# halaman). Docling kadang mendeteksi blok ini sebagai tabel; barisnya bukan isi
# akademik sehingga dibuang, sedangkan header tabel akademik yang berulang
# ("Minggu ke-", "Sub-CPMK", "Bahan Kajian") tetap dipertahankan.
_ADMIN_LABEL_PATTERN = re.compile(
    r"^(?:no\.?\s*(?:dok|revisi)|tgl\.?\s*terbit|tanggal|hal\.?|tahun\s+ajaran)\b.*$",
    re.IGNORECASE,
)

#: Field RPS Structured Data yang menjadi input LLM (content-schema §6.1/§6.3).
#: ``extraction`` dan ``schema_version`` sengaja tidak termasuk: keduanya
#: metadata proses, bukan informasi akademik.
LLM_FIELDS = (
    "course",
    "cpl",
    "cpmk",
    "sub_cpmk",
    "topics",
    "weeks",
    "teaching_methods",
    "media",
    "assessments",
    "references",
)

# Lebar baris besar supaya kalimat panjang tetap satu baris (lebih hemat token
# daripada terlipat dengan indentasi).
_YAML_WIDTH = 1000


def document_to_yaml(source_document: dict[str, Any]) -> str:
    """Serialisasi ``rps.source_document`` (Docling JSON) menjadi YAML.

    Hasilnya memuat ``page_count`` dan daftar ``blocks`` terurut menurut halaman:
    ``heading``, ``text``, atau ``table`` (dengan ``caption`` dan ``rows``).
    Nomor halaman disertakan pada setiap blok karena RPS merujuk halaman saat
    menyebut lampiran (mis. "lihat lampiran halaman 7").
    """
    if not isinstance(source_document, dict):
        raise RPSValidationError(
            "source_document", "harus berupa JSON objek hasil konversi Docling"
        )

    captions = _caption_index(source_document)
    repeated = _repeated_chrome_texts(source_document)
    blocks: list[tuple[int, int, dict[str, Any]]] = []

    for position, item in enumerate(_as_list(source_document.get("texts"))):
        if _is_page_chrome(item):
            continue
        text = _redact_identity(_clean_text(item.get("text")))
        if not text or text in repeated:
            continue
        page = _first_page(item)
        if item.get("label") in HEADING_LABELS:
            blocks.append((page, position, {"page": page, "heading": text}))
        else:
            blocks.append((page, position, {"page": page, "text": text}))

    for position, table in enumerate(_as_list(source_document.get("tables"))):
        if _is_page_chrome(table):
            continue
        rows = _table_rows(table)
        if not rows:
            continue
        block: dict[str, Any] = {}
        caption = _table_caption(table, captions)
        if caption:
            block["caption"] = caption
        block["rows"] = rows
        blocks.append(
            (_first_page(table), len(_as_list(source_document.get("texts"))) + position, {
                "page": _first_page(table),
                "table": block,
            })
        )

    blocks.sort(key=lambda block: (block[0], block[1]))
    payload = {
        "page_count": _page_count(source_document),
        "blocks": [block for _, _, block in blocks],
    }
    return dump_yaml(payload)


def structured_data_to_yaml(structured_data: dict[str, Any] | BaseModel) -> str:
    """Serialisasi ``rps.structured_data`` menjadi YAML untuk input LLM.

    Hanya field pada :data:`LLM_FIELDS` yang ikut; metadata ekstraksi dan versi
    schema dibuang karena bukan bahan penyusunan rencana pembelajaran.
    """
    if isinstance(structured_data, BaseModel):
        data = structured_data.model_dump(mode="json")
    elif isinstance(structured_data, dict):
        data = structured_data
    else:
        raise RPSValidationError(
            "structured_data", "harus berupa dict atau model RPS Structured Data"
        )

    selected = {field: _without_empty(data.get(field)) for field in LLM_FIELDS}
    payload = {field: value for field, value in selected.items() if value not in (None, {}, [])}
    if not payload:
        raise RPSValidationError("structured_data", "tidak memuat field akademik apa pun")
    return dump_yaml(payload)


# --- Bagian dalam -----------------------------------------------------------


def dump_yaml(payload: dict[str, Any]) -> str:
    """Tulis YAML tanpa mengubah urutan field (urutan = urutan kontrak).

    Publik supaya serializer konteks lain (mis. konteks dosen BE-10.3) memakai
    format YAML yang sama dengan input LLM RPS.
    """
    return yaml.safe_dump(
        payload,
        allow_unicode=True,
        sort_keys=False,
        width=_YAML_WIDTH,
        default_flow_style=False,
    )


def _as_list(value: Any) -> list[dict[str, Any]]:
    """Docling menulis daftar objek; nilai lain dianggap kosong."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _is_page_chrome(item: dict[str, Any]) -> bool:
    """Header/footer halaman: tempat identitas dosen dan nama program studi."""
    return item.get("content_layer") == "furniture" or item.get("label") in PAGE_CHROME_LABELS


def _repeated_chrome_texts(source_document: dict[str, Any]) -> set[str]:
    """Teks pendek yang muncul di banyak halaman = header/footer template.

    Nomor dokumen, tanggal terbit, nomor revisi, dan "Hal." berulang di setiap
    halaman. Yang dihitung hanya teks pendek (<= :data:`CHROME_MAX_CHARS`) pada
    >= :data:`CHROME_MIN_PAGES` halaman berbeda, sehingga paragraf akademik dan
    kalimat yang sengaja diulang tidak ikut terbuang.
    """
    pages_by_text: dict[str, set[int]] = {}
    for item in _as_list(source_document.get("texts")):
        if _is_page_chrome(item):
            continue
        _count_chrome_text(pages_by_text, item.get("text"), _first_page(item))
    # Sel tabel sengaja **tidak** ikut dihitung: header tabel rencana mingguan
    # memang diulang di setiap halaman dan justru dibutuhkan LLM. Artefak yang
    # perlu dibuang dari tabel hanya nomor halaman (lihat :func:`_is_page_number`).

    return {
        text for text, pages in pages_by_text.items() if len(pages) >= CHROME_MIN_PAGES
    }


def _count_chrome_text(pages_by_text: dict[str, set[int]], value: Any, page: int) -> None:
    """Catat teks pendek beserta halaman kemunculannya (lihat §chrome)."""
    text = _clean_text(value)
    if not text or len(text) > CHROME_MAX_CHARS:
        return
    pages_by_text.setdefault(text, set()).add(page)


def _redact_identity(text: str) -> str:
    """Ganti nama/NIDN/NIP dosen dengan penanda (lihat :data:`IDENTITY_PATTERNS`).

    ``ponytail:`` heuristik berbasis kata kunci template RPS, bukan pengenalan
    nama sungguhan. Identitas yang tercetak tanpa kata kunci (mis. "Nama : Kadek
    ...") lolos. Ganti dengan pemetaan field template-aware saat BE-08.2/BE-09
    membutuhkan jaminan penuh.
    """
    for pattern in IDENTITY_PATTERNS:
        text = pattern.sub(IDENTITY_PLACEHOLDER, text)
    return " ".join(text.split())


def _is_page_number(text: str) -> bool:
    """Sel tabel berisi nomor halaman (``": 4/16"``) — bukan isi akademik."""
    return bool(_PAGE_NUMBER_PATTERN.match(text))


def _clean_text(value: Any) -> str:
    return " ".join(value.split()) if isinstance(value, str) else ""


def _first_page(item: dict[str, Any]) -> int:
    """Nomor halaman dari ``prov`` pertama; 0 bila Docling tidak menyebutkannya."""
    for prov in _as_list(item.get("prov")):
        page = prov.get("page_no")
        if isinstance(page, int) and page > 0:
            return page
    return 0


def _page_count(source_document: dict[str, Any]) -> int:
    pages = source_document.get("pages")
    if isinstance(pages, (dict, list)):
        return len(pages)
    return 0


def _caption_index(source_document: dict[str, Any]) -> dict[str, str]:
    """Peta ``self_ref`` → teks, untuk menerjemahkan rujukan caption tabel."""
    index: dict[str, str] = {}
    for item in _as_list(source_document.get("texts")):
        reference = item.get("self_ref")
        text = _clean_text(item.get("text"))
        if isinstance(reference, str) and text:
            index[reference] = text
    return index


def _table_caption(table: dict[str, Any], captions: dict[str, str]) -> str:
    """Caption tabel; Docling menyimpannya sebagai daftar rujukan ``$ref``."""
    parts: list[str] = []
    for caption in _as_list(table.get("captions")):
        reference = caption.get("$ref")
        if isinstance(reference, str) and reference in captions:
            parts.append(captions[reference])
            continue
        text = _clean_text(caption.get("text"))
        if text:
            parts.append(text)
    return " ".join(parts)


def _table_rows(table: dict[str, Any]) -> list[list[str]]:
    """Susun grid teks tabel dari ``data.table_cells``.

    Sel diletakkan menurut ``start_row_offset_idx``/``start_col_offset_idx``.
    Selain itu, isi sel gabungan tidak digandakan ke sel yang tertutup ``row_span``
    — pembaca (model bahasa) tetap melihat rentangnya lewat baris yang sama.
    """
    data = table.get("data")
    if not isinstance(data, dict):
        return []
    cells = _as_list(data.get("table_cells"))
    if not cells:
        return []

    row_count = data.get("num_rows") if isinstance(data.get("num_rows"), int) else 0
    col_count = data.get("num_cols") if isinstance(data.get("num_cols"), int) else 0
    for cell in cells:
        row_count = max(row_count, _index(cell.get("start_row_offset_idx")) + 1)
        col_count = max(col_count, _index(cell.get("start_col_offset_idx")) + 1)

    grid = [["" for _ in range(col_count)] for _ in range(row_count)]
    for cell in cells:
        text = _redact_identity(_clean_text(cell.get("text")))
        if not text or _is_page_number(text):
            continue
        row = min(_index(cell.get("start_row_offset_idx")), row_count - 1)
        column = min(_index(cell.get("start_col_offset_idx")), col_count - 1)
        grid[row][column] = text

    # Baris kisi administratif template dibuang; baris/kolom yang seluruhnya
    # kosong juga tidak membawa informasi.
    rows = [
        row
        for row in ([" ".join(cell.split()) for cell in line] for line in grid)
        if any(row) and not _is_admin_row(row)
    ]
    trimmed: list[list[str]] = []
    for row in rows:
        while row and not row[-1]:
            row.pop()
        trimmed.append(row)
    return trimmed


def _is_admin_row(row: list[str]) -> bool:
    """Baris template administratif (bukan isi akademik)."""
    return any(_ADMIN_LABEL_PATTERN.match(cell) for cell in row if cell)


def _index(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return max(0, value)


def _without_empty(value: Any) -> Any:
    """Buang ``None``/string kosong/daftar kosong secara rekursif."""
    if isinstance(value, dict):
        cleaned = {key: _without_empty(item) for key, item in value.items()}
        return {key: item for key, item in cleaned.items() if item not in (None, {}, [])}
    if isinstance(value, list):
        cleaned_list = [_without_empty(item) for item in value]
        return [item for item in cleaned_list if item not in (None, {}, [])]
    if isinstance(value, str) and not value.strip():
        return None
    return value
