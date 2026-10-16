"""Test domain RPS, validasi berkas, dan lifecycle pemrosesan (BE-05.1/BE-05.2).

Seluruh test di sini murni: tanpa database, tanpa filesystem, tanpa Docling.
Yang diuji adalah aturan yang menjaga integritas dokumen RPS — nilai yang
disimpan selalu tervalidasi, status hanya berpindah lewat transisi yang sah, dan
``file_hash`` benar-benar dihitung dari isi berkas.
"""

from __future__ import annotations

import hashlib

import pytest
import shortuuid

from src.schemas.rps_structured import RPS_SCHEMA_VERSION
from src.services.rps.domain import RPSDocument, require_owner
from src.services.rps.enums import RPSStatus
from src.services.rps.errors import (
    InvalidFileError,
    RPSStateError,
    RPSValidationError,
)
from src.services.rps.validation import (
    compute_file_hash,
    ensure_matches_declared_type,
    ensure_size_within_limit,
    ensure_supported_extension,
    file_extension,
    normalize_file_hash,
    normalize_file_name,
    normalize_file_path,
    normalize_identifier,
    normalize_schema_version,
)

PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"
OWNER_ID = shortuuid.uuid()
FILE_PATH = "owner/ab/abcdef.pdf"


# --- Validasi murni --------------------------------------------------------


def test_file_hash_is_sha256_of_the_content():
    assert compute_file_hash(PDF_BYTES) == hashlib.sha256(PDF_BYTES).hexdigest()


def test_identical_content_always_hashes_the_same():
    """Kunci deduplikasi hanya berguna bila hash stabil antar unggahan."""
    assert compute_file_hash(PDF_BYTES) == compute_file_hash(bytes(PDF_BYTES))
    assert compute_file_hash(PDF_BYTES) != compute_file_hash(PDF_BYTES + b" ")


@pytest.mark.parametrize("value", [b"", b"x"])
def test_hash_of_any_content_is_a_64_character_hex_digest(value):
    assert len(compute_file_hash(value)) == 64
    assert normalize_file_hash(compute_file_hash(value)) == compute_file_hash(value)


def test_file_hash_must_look_like_a_sha256_digest():
    for invalid in ["", "bukan-hash", "A" * 63, "z" * 64, None]:
        with pytest.raises(RPSValidationError):
            normalize_file_hash(invalid)


def test_file_hash_is_normalized_to_lowercase():
    assert normalize_file_hash("AB" * 32) == "ab" * 32


@pytest.mark.parametrize(
    ("file_name", "expected"),
    [
        ("rps.pdf", "pdf"),
        ("RPS Basis Data.PDF", "pdf"),
        ("arsip.tar.gz", "gz"),
        ("tanpa-ekstensi", ""),
        (".pdf", ""),
        ("", ""),
    ],
)
def test_file_extension_is_read_from_the_last_dot(file_name, expected):
    assert file_extension(file_name) == expected


def test_file_name_is_metadata_so_path_separators_are_rejected():
    """Nama dari client tidak pernah boleh menjadi bagian dari path penyimpanan."""
    for unsafe in ["../../etc/passwd", "folder/rps.pdf", r"folder\rps.pdf", "rps\x00.pdf"]:
        with pytest.raises(RPSValidationError):
            normalize_file_name(unsafe)


def test_file_name_is_trimmed_and_length_limited():
    assert normalize_file_name("  rps.pdf  ") == "rps.pdf"

    with pytest.raises(RPSValidationError):
        normalize_file_name("a" * 256)
    with pytest.raises(RPSValidationError):
        normalize_file_name("   ")


def test_stored_path_must_stay_inside_the_storage_root():
    assert normalize_file_path("owner/ab/hash.pdf") == "owner/ab/hash.pdf"

    for unsafe in ["/etc/passwd", "owner/../../etc/passwd", "..\\windows\\system32", "", None]:
        with pytest.raises(RPSValidationError):
            normalize_file_path(unsafe)


def test_identifier_must_be_a_shortuuid():
    assert normalize_identifier(OWNER_ID) == OWNER_ID
    assert normalize_identifier(None) is None

    for invalid in ["bukan-id", "3f2504e0-4f89-41d3-9a0c-0305e82c3301", "O" * 22]:
        with pytest.raises(RPSValidationError):
            normalize_identifier(invalid)


def test_owner_is_required():
    assert require_owner(OWNER_ID) == OWNER_ID

    with pytest.raises(RPSValidationError):
        require_owner(None)


def test_schema_version_is_required_and_trimmed():
    assert normalize_schema_version(" 2.0 ") == "2.0"

    for invalid in ["", "   ", None, 1]:
        with pytest.raises(RPSValidationError):
            normalize_schema_version(invalid)


# --- Kebijakan unggahan ----------------------------------------------------


def test_only_configured_extensions_are_accepted():
    assert ensure_supported_extension("pdf", ("pdf",)) == "pdf"

    with pytest.raises(InvalidFileError):
        ensure_supported_extension("exe", ("pdf",))
    with pytest.raises(InvalidFileError):
        ensure_supported_extension("", ("pdf",))


def test_docx_can_be_enabled_without_code_changes():
    """design-api §6.1 mengizinkan PDF/DOCX; cakupan M02 membatasi ke PDF."""
    assert ensure_supported_extension("DOCX", ("pdf", "docx")) == "docx"


def test_empty_and_oversized_files_are_rejected_before_being_stored():
    assert ensure_size_within_limit(10, 100) == 10

    with pytest.raises(InvalidFileError):
        ensure_size_within_limit(0, 100)
    with pytest.raises(InvalidFileError):
        ensure_size_within_limit(101, 100)


def test_content_must_match_the_extension_it_claims():
    """Nama ``.pdf`` tidak cukup: beberapa byte pertama harus benar-benar PDF."""
    ensure_matches_declared_type(PDF_BYTES, "pdf")

    with pytest.raises(InvalidFileError):
        ensure_matches_declared_type(b"<html>not a pdf</html>", "pdf")


def test_unknown_formats_are_left_to_the_converter():
    """Format tanpa signature dikenal tidak ditolak di sini."""
    ensure_matches_declared_type(b"apa saja", "txt")


# --- Lifecycle dokumen -----------------------------------------------------


def make_document(**overrides) -> RPSDocument:
    payload = {
        "owner_id": OWNER_ID,
        "file_name": "rps-basis-data.pdf",
        "file_path": FILE_PATH,
        "content": PDF_BYTES,
    }
    payload.update(overrides)
    return RPSDocument.register(**payload)


def test_register_computes_hash_and_derives_file_type():
    document = make_document()

    assert document.file_hash == compute_file_hash(PDF_BYTES)
    assert document.file_type == "PDF"
    assert document.schema_version == RPS_SCHEMA_VERSION
    assert document.status is RPSStatus.UPLOADED
    assert document.id is None
    assert document.source_markdown is None


def test_register_accepts_a_precomputed_hash_to_avoid_hashing_twice():
    digest = compute_file_hash(PDF_BYTES)

    document = make_document(file_hash=digest)

    assert document.file_hash == digest


def test_register_requires_an_extension():
    with pytest.raises(RPSValidationError):
        make_document(file_name="rps")


def test_a_new_document_is_not_considered_processed():
    assert not make_document().is_processed
    assert not make_document().is_processing


def test_processing_transitions_uploaded_to_processed():
    document = make_document()

    document.start_processing()
    assert document.is_processing

    document.complete_processing("# RPS Basis Data")
    assert document.is_processed
    assert document.source_markdown == "# RPS Basis Data"


def test_a_document_cannot_be_processed_twice_at_once():
    """Dua pemrosesan bersamaan atas satu dokumen hanya akan saling menimpa."""
    document = make_document()
    document.start_processing()

    with pytest.raises(RPSStateError):
        document.start_processing()


def test_a_failed_document_can_be_processed_again():
    document = make_document()
    document.start_processing()
    document.fail_processing()
    assert document.status is RPSStatus.FAILED

    document.start_processing()
    document.complete_processing("# percobaan kedua")

    assert document.is_processed


def test_completing_without_processing_is_a_state_error():
    document = make_document()

    with pytest.raises(RPSStateError):
        document.complete_processing("# markdown")


@pytest.mark.parametrize("empty", ["", "   ", None])
def test_empty_conversion_output_is_not_a_valid_result(empty):
    document = make_document()
    document.start_processing()

    with pytest.raises(RPSValidationError):
        document.complete_processing(empty)


def test_already_processed_as_matches_on_hash_and_schema_version():
    document = make_document()
    document.start_processing()
    document.complete_processing("# RPS")

    assert document.already_processed_as(
        file_hash=document.file_hash, schema_version=RPS_SCHEMA_VERSION
    )
    assert not document.already_processed_as(
        file_hash=document.file_hash, schema_version="2.0"
    )
    assert not document.already_processed_as(
        file_hash=compute_file_hash(b"dokumen lain"), schema_version=RPS_SCHEMA_VERSION
    )


def test_already_processed_as_is_false_while_still_unprocessed():
    document = make_document()

    assert not document.already_processed_as(
        file_hash=document.file_hash, schema_version=RPS_SCHEMA_VERSION
    )


def test_a_processed_document_is_stale_for_a_newer_schema_version():
    """Inilah pertanyaan yang diajukan service sebelum memutuskan memproses ulang."""
    document = make_document()
    document.start_processing()
    document.complete_processing("# RPS")

    assert document.already_processed_as(
        file_hash=document.file_hash, schema_version=RPS_SCHEMA_VERSION
    )
    assert not document.already_processed_as(
        file_hash=document.file_hash, schema_version="2.0"
    )

    # Setelah diputuskan diproses ulang, dokumen mencatat versi yang benar-benar
    # dipakai — bukan membiarkan hasil lama mengaku berasal dari skema baru.
    document.retarget_schema_version("2.0")

    assert document.schema_version == "2.0"
    assert not document.already_processed_as(
        file_hash=document.file_hash, schema_version=RPS_SCHEMA_VERSION
    )


def test_retargeting_rejects_a_blank_schema_version():
    document = make_document()

    with pytest.raises(RPSValidationError):
        document.retarget_schema_version("   ")


def test_ownership_is_decided_by_the_owner_identifier():
    document = make_document()

    assert document.belongs_to(OWNER_ID)
    assert not document.belongs_to(shortuuid.uuid())


def test_repr_never_embeds_the_converted_markdown():
    """Representasi dipakai pada log; dokumen RPS bisa ribuan baris."""
    document = make_document()
    document.start_processing()
    document.complete_processing("# RAHASIA PANJANG")

    assert "RAHASIA" not in repr(document)
    assert "source_markdown=set" in repr(document)
