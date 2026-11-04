"""Penyimpanan berkas RPS: port dan adapter filesystem lokal (BE-05.1).

Dokumen RPS asli **dipertahankan** agar hasil yang dihasilkan tetap dapat
dilacak ke sumbernya (data-model §8: "The original file should be retained when
practical"). Karena itu penyimpanan menjadi tanggung jawab layer service, bukan
tugas sementara di dalam request.

Dua keputusan bentuk yang penting:

1. **Content-addressed.** Berkas disimpan pada
   ``<root>/<owner_id>/<hash[:2]>/<hash>.<ext>`` — bukan memakai nama file dari
   client. Nama dari client dapat memuat pemisah path, karakter aneh, atau
   bertabrakan antar unggahan; dengan content addressing, satu isi hanya punya
   satu lokasi dan unggahan ulang bersifat idempoten. Kolom ``rps.file_path``
   menyimpan path **relatif** ini, sehingga root storage dapat dipindahkan tanpa
   mengubah database.
2. **Artefak konversi terpisah.** Hasil Docling yang besar (JSON dan daftar
   tabel) ditulis di direktori artefak di samping dokumennya, sedangkan
   ``source_document`` disimpan pada kolom ``rps`` (data-model §8) supaya dapat
   dibaca tanpa menyentuh filesystem. Tidak ada artefak Markdown/YAML: JSON
   Docling adalah satu-satunya format hasil konversi (DL-008), dan YAML baru
   dibentuk BE-08.1 saat dibutuhkan (DL-006).

Seluruh operasi filesystem dijalankan lewat ``asyncio.to_thread`` agar tidak
memblokir event loop, dan setiap penulisan bersifat atomik (tulis ke berkas
sementara lalu ``os.replace``) supaya kegagalan di tengah jalan tidak
meninggalkan berkas separuh jadi yang tampak sah.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from src.services.rps.domain import require_owner
from src.services.rps.errors import DocumentStorageError, RPSValidationError
from src.services.rps.validation import normalize_file_path

__all__ = [
    "ARTIFACT_DIR_NAME",
    "DocumentStorage",
    "LocalDocumentStorage",
    "StoredDocument",
    "artifact_dir_for",
]

# Nama direktori artefak konversi di samping dokumen asli.
ARTIFACT_DIR_NAME = "conversion"


def artifact_dir_for(document_path: str) -> str:
    """Direktori artefak konversi milik sebuah dokumen (path relatif).

    Artefak diletakkan di samping dokumennya, di bawah direktori bernama dokumen
    itu sendiri (``<hash>/conversion``) — bukan pada direktori shard
    (``<hash[:2]>/conversion``), karena shard dipakai bersama oleh banyak
    dokumen dan artefaknya akan saling menimpa. Dengan bentuk ini, menghapus atau
    memindahkan satu dokumen berarti memindahkan seluruh hasil turunannya
    sekaligus.
    """
    directory, _, file_name = document_path.rpartition("/")
    stem = file_name.rpartition(".")[0] or file_name
    base = f"{directory}/{stem}" if directory else stem
    return f"{base}/{ARTIFACT_DIR_NAME}"


@dataclass(frozen=True, slots=True)
class StoredDocument:
    """Hasil penyimpanan dokumen: path relatif dan ukurannya."""

    relative_path: str
    size_bytes: int

    @property
    def artifact_dir(self) -> str:
        """Direktori artefak konversi milik dokumen ini (path relatif)."""
        return artifact_dir_for(self.relative_path)


class DocumentStorage(ABC):
    """Port penyimpanan berkas dokumen.

    Service bergantung pada interface ini, bukan pada filesystem, sehingga
    pengujian dapat memakai penyimpanan in-memory tanpa menyentuh disk dan
    pemindahan ke object storage (S3, dsb.) tidak mengubah logika domain.
    """

    @abstractmethod
    async def save_document(
        self, *, owner_id: str, file_hash: str, extension: str, content: bytes
    ) -> StoredDocument:
        """Simpan dokumen asli dan kembalikan lokasi relatifnya."""

    @abstractmethod
    async def read_document(self, relative_path: str) -> bytes:
        """Baca kembali dokumen asli; error domain bila tidak ada/tidak aman."""

    @abstractmethod
    async def document_exists(self, relative_path: str) -> bool:
        """Apakah dokumen pada path relatif tersebut ada."""

    @abstractmethod
    async def save_artifacts(
        self, *, document_path: str, artifacts: Mapping[str, bytes]
    ) -> dict[str, str]:
        """Simpan artefak konversi milik sebuah dokumen.

        ``document_path`` adalah path relatif dokumen aslinya; direktori artefak
        diturunkan darinya (:func:`artifact_dir_for`), sehingga pemanggil tidak
        perlu tahu tata letak penyimpanan.
        """


class LocalDocumentStorage(DocumentStorage):
    """Adapter filesystem lokal untuk :class:`DocumentStorage`."""

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)

    @property
    def root(self) -> Path:
        """Direktori akar penyimpanan (absolut bila sudah di-resolve)."""
        return self._root

    async def save_document(
        self, *, owner_id: str, file_hash: str, extension: str, content: bytes
    ) -> StoredDocument:
        owner = require_owner(owner_id)
        relative_path = f"{owner}/{file_hash[:2]}/{file_hash}.{extension.lower()}"
        target = self._resolve(relative_path)

        await asyncio.to_thread(_write_atomic, target, content)
        return StoredDocument(relative_path=relative_path, size_bytes=len(content))

    async def read_document(self, relative_path: str) -> bytes:
        target = self._resolve(normalize_file_path(relative_path))
        try:
            return await asyncio.to_thread(target.read_bytes)
        except FileNotFoundError as exc:
            raise DocumentStorageError(
                f"dokumen tidak ada pada storage: {target.name}"
            ) from exc
        except OSError as exc:
            raise DocumentStorageError(
                f"gagal membaca dokumen dari storage: {type(exc).__name__}"
            ) from exc

    async def document_exists(self, relative_path: str) -> bool:
        target = self._resolve(normalize_file_path(relative_path))
        return await asyncio.to_thread(target.is_file)

    async def save_artifacts(
        self, *, document_path: str, artifacts: Mapping[str, bytes]
    ) -> dict[str, str]:
        artifact_dir = artifact_dir_for(normalize_file_path(document_path))
        resolved_dir = self._resolve(artifact_dir)
        written: dict[str, str] = {}

        for name, content in artifacts.items():
            safe_name = _safe_artifact_name(name)
            await asyncio.to_thread(_write_atomic, resolved_dir / safe_name, content)
            written[name] = f"{artifact_dir}/{safe_name}"

        return written

    def _resolve(self, relative_path: str) -> Path:
        """Ubah path relatif menjadi path absolut yang dijamin berada di root.

        Pemeriksaan dilakukan setelah ``resolve()`` sehingga symlink dan ``..``
        tidak dapat dipakai untuk keluar dari direktori penyimpanan.
        """
        root = self._root.resolve()
        candidate = (self._root / relative_path).resolve()
        if candidate != root and root not in candidate.parents:
            raise RPSValidationError(
                "file_path", "path berada di luar direktori penyimpanan"
            )
        return candidate


def _safe_artifact_name(name: str) -> str:
    """Nama artefak harus nama berkas sederhana di dalam direktori artefak."""
    if not name or "/" in name or "\\" in name or name in {".", ".."}:
        raise RPSValidationError("artifact", f"nama artefak tidak valid: {name!r}")
    return name


def _write_atomic(target: Path, content: bytes) -> None:
    """Tulis berkas secara atomik: temp file di direktori yang sama, lalu replace."""
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary_name = tempfile.mkstemp(dir=target.parent, prefix=".tmp-")
        try:
            with os.fdopen(handle, "wb") as temporary:
                temporary.write(content)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_name, target)
        except BaseException:
            # Jangan tinggalkan berkas sementara bila penulisan gagal.
            Path(temporary_name).unlink(missing_ok=True)
            raise
    except OSError as exc:
        raise DocumentStorageError(
            f"gagal menulis ke storage: {type(exc).__name__}"
        ) from exc
