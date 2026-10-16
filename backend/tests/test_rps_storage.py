"""Test penyimpanan berkas RPS (BE-05.1).

Penyimpanan diuji pada filesystem sungguhan (``tmp_path``) karena justru
sifat-sifat itulah yang penting: berkas disimpan berdasarkan isinya, hasilnya
dapat dibaca kembali, dan tidak ada cara menulis atau membaca di luar direktori
penyimpanan — termasuk lewat ``..`` maupun path absolut.
"""

from __future__ import annotations

import hashlib

import pytest
import shortuuid

from src.services.rps.errors import DocumentStorageError, RPSValidationError
from src.services.rps.storage import (
    ARTIFACT_DIR_NAME,
    LocalDocumentStorage,
    StoredDocument,
    artifact_dir_for,
)
from src.services.rps.validation import compute_file_hash

PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"
OWNER_ID = shortuuid.uuid()


@pytest.fixture
def storage(tmp_path) -> LocalDocumentStorage:
    return LocalDocumentStorage(tmp_path)


async def save_pdf(storage: LocalDocumentStorage, content: bytes = PDF_BYTES) -> StoredDocument:
    return await storage.save_document(
        owner_id=OWNER_ID,
        file_hash=compute_file_hash(content),
        extension="pdf",
        content=content,
    )


def test_artifacts_live_next_to_their_document():
    assert artifact_dir_for("owner/ab/hash.pdf") == f"owner/ab/hash/{ARTIFACT_DIR_NAME}"
    assert artifact_dir_for("hash.pdf") == f"hash/{ARTIFACT_DIR_NAME}"
    # Dokumen tanpa ekstensi tetap punya direktori artefaknya sendiri.
    assert artifact_dir_for("owner/ab/hash") == f"owner/ab/hash/{ARTIFACT_DIR_NAME}"


def test_documents_in_the_same_shard_do_not_share_an_artifact_directory():
    """Shard ``<hash[:2]>`` dipakai bersama; artefak tidak boleh saling menimpa."""
    first = artifact_dir_for("owner/ab/aaaa.pdf")
    second = artifact_dir_for("owner/ab/bbbb.pdf")

    assert first != second


@pytest.mark.asyncio
async def test_document_is_stored_by_its_content_not_its_name(storage, tmp_path):
    """Nama dari client tidak pernah menjadi path; isi yang menentukan lokasi."""
    digest = compute_file_hash(PDF_BYTES)

    stored = await save_pdf(storage)

    assert stored.relative_path == f"{OWNER_ID}/{digest[:2]}/{digest}.pdf"
    assert stored.size_bytes == len(PDF_BYTES)
    assert (tmp_path / stored.relative_path).read_bytes() == PDF_BYTES


@pytest.mark.asyncio
async def test_identical_content_lands_in_exactly_one_place(storage, tmp_path):
    """Unggahan ulang dokumen yang sama tidak menggandakan berkas."""
    first = await save_pdf(storage)
    second = await save_pdf(storage, bytes(PDF_BYTES))

    assert first.relative_path == second.relative_path
    files = [path for path in (tmp_path / OWNER_ID).rglob("*") if path.is_file()]
    assert len(files) == 1


@pytest.mark.asyncio
async def test_different_content_and_owners_do_not_collide(storage):
    other_owner = shortuuid.uuid()

    stored = await save_pdf(storage)
    other_content = await save_pdf(storage, PDF_BYTES + b"extra")
    other_owner_doc = await storage.save_document(
        owner_id=other_owner,
        file_hash=compute_file_hash(PDF_BYTES),
        extension="pdf",
        content=PDF_BYTES,
    )

    assert stored.relative_path != other_content.relative_path
    assert stored.relative_path != other_owner_doc.relative_path
    assert other_owner_doc.relative_path.startswith(f"{other_owner}/")


@pytest.mark.asyncio
async def test_stored_document_round_trips(storage):
    stored = await save_pdf(storage)

    assert await storage.document_exists(stored.relative_path)
    assert await storage.read_document(stored.relative_path) == PDF_BYTES


@pytest.mark.asyncio
async def test_artifacts_are_written_beside_the_document(storage, tmp_path):
    stored = await save_pdf(storage)

    written = await storage.save_artifacts(
        document_path=stored.relative_path,
        artifacts={"document.json": b"{}", "tables.json": b"[]"},
    )

    assert written == {
        "document.json": f"{stored.artifact_dir}/document.json",
        "tables.json": f"{stored.artifact_dir}/tables.json",
    }
    assert (tmp_path / written["document.json"]).read_bytes() == b"{}"
    assert (tmp_path / written["tables.json"]).read_bytes() == b"[]"


@pytest.mark.asyncio
async def test_writing_artifacts_twice_replaces_them(storage, tmp_path):
    """Pemrosesan ulang menimpa artefak lama, bukan menumpuknya."""
    stored = await save_pdf(storage)

    await storage.save_artifacts(
        document_path=stored.relative_path, artifacts={"tables.json": b"[1]"}
    )
    written = await storage.save_artifacts(
        document_path=stored.relative_path, artifacts={"tables.json": b"[2]"}
    )

    assert (tmp_path / written["tables.json"]).read_bytes() == b"[2]"
    assert len(list((tmp_path / stored.artifact_dir).iterdir())) == 1


@pytest.mark.asyncio
async def test_a_missing_document_is_a_storage_error(storage):
    with pytest.raises(DocumentStorageError):
        await storage.read_document(f"{OWNER_ID}/ab/tidak-ada.pdf")


@pytest.mark.asyncio
async def test_not_even_an_existing_file_outside_the_root_can_be_read(storage, tmp_path):
    """Path traversal ditolak walau berkasnya benar-benar ada."""
    outside = tmp_path.parent / "rahasia.txt"
    outside.write_text("jangan dibaca", encoding="utf-8")

    for unsafe in [
        "../rahasia.txt",
        f"{OWNER_ID}/../../rahasia.txt",
        str(outside),
    ]:
        with pytest.raises(RPSValidationError):
            await storage.read_document(unsafe)


@pytest.mark.asyncio
async def test_artifact_names_cannot_escape_their_directory(storage):
    stored = await save_pdf(storage)

    with pytest.raises(RPSValidationError):
        await storage.save_artifacts(
            document_path=stored.relative_path, artifacts={"../keluar.json": b"{}"}
        )
    with pytest.raises(RPSValidationError):
        await storage.save_artifacts(
            document_path=stored.relative_path, artifacts={"sub/dir.json": b"{}"}
        )


@pytest.mark.asyncio
async def test_owner_must_be_a_shortuuid_because_it_becomes_a_directory(storage):
    with pytest.raises(RPSValidationError):
        await storage.save_document(
            owner_id="../etc",
            file_hash=compute_file_hash(PDF_BYTES),
            extension="pdf",
            content=PDF_BYTES,
        )


@pytest.mark.asyncio
async def test_a_failed_write_leaves_no_partial_file_behind(storage, tmp_path, monkeypatch):
    """Penulisan bersifat atomik: tidak ada berkas sementara yang tertinggal."""
    stored = await save_pdf(storage)

    import src.services.rps.storage as storage_module

    def explode(*args, **kwargs):
        raise OSError("disk penuh")

    monkeypatch.setattr(storage_module.os, "replace", explode)

    with pytest.raises(DocumentStorageError):
        await storage.save_artifacts(
            document_path=stored.relative_path, artifacts={"tables.json": b"[]"}
        )

    leftovers = list((tmp_path / stored.artifact_dir).iterdir())
    assert leftovers == []


@pytest.mark.asyncio
async def test_storage_root_can_be_any_writable_directory(tmp_path):
    """Root penyimpanan berasal dari konfigurasi, bukan dari lokasi kode."""
    nested = tmp_path / "var" / "rps"
    storage = LocalDocumentStorage(nested)

    stored = await save_pdf(storage)

    assert (nested / stored.relative_path).exists()
    assert storage.root == nested
    assert hashlib.sha256(PDF_BYTES).hexdigest() in stored.relative_path
