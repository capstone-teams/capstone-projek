"""Validasi dan normalisasi atribut RPS, serta pemeriksaan file unggahan.

Seluruh fungsi di sini murni: tanpa I/O, tanpa database, tanpa framework HTTP,
sehingga aturan file RPS dapat diuji tanpa infrastruktur apa pun. Batas panjang
mengikuti tipe kolom pada ``src.models.rps`` supaya nilai yang lolos validasi
domain tidak ditolak oleh database.

Dua lapis pemeriksaan dipisahkan dengan sengaja:

1. **Bentuk nilai** (:func:`normalize_file_name`, :func:`normalize_file_hash`,
   ...) — memastikan nilai yang disimpan memenuhi invariant domain;
2. **Kebijakan unggahan** (:func:`ensure_supported_extension`,
   :func:`ensure_size_within_limit`, :func:`ensure_matches_declared_type`) —
   memastikan file yang diterima sesuai batas yang dikonfigurasi.

Nama file dari client **tidak pernah** dipakai untuk membentuk path
penyimpanan; ia hanya disimpan sebagai metadata (lihat
:mod:`src.services.rps.storage`).
"""

from __future__ import annotations

import hashlib
import re

from src.models.base import ID_LENGTH
from src.services.rps.enums import RPSStatus
from src.services.rps.errors import InvalidFileError, RPSValidationError
from src.services.user.validation import SHORTUUID_ALPHABET

__all__ = [
    "DEFAULT_ALLOWED_EXTENSIONS",
    "MAX_FILE_HASH_LENGTH",
    "MAX_FILE_NAME_LENGTH",
    "MAX_FILE_PATH_LENGTH",
    "MAX_FILE_TYPE_LENGTH",
    "MAX_SCHEMA_VERSION_LENGTH",
    "compute_file_hash",
    "ensure_matches_declared_type",
    "ensure_size_within_limit",
    "ensure_supported_extension",
    "file_extension",
    "normalize_file_hash",
    "normalize_file_name",
    "normalize_file_path",
    "normalize_file_type",
    "normalize_identifier",
    "normalize_schema_version",
    "normalize_status",
]

MAX_FILE_NAME_LENGTH = 255
MAX_FILE_TYPE_LENGTH = 20
MAX_FILE_HASH_LENGTH = 255
MAX_FILE_PATH_LENGTH = 1024
MAX_SCHEMA_VERSION_LENGTH = 50

# Ekstensi yang diterima secara default. Cakupan M02 dibatasi pada RPS **PDF**
# dengan template program studi (issue BE-05), sehingga DOCX — yang memang
# diizinkan design-api §6.1 — tidak ikut secara default dan dapat diaktifkan
# lewat konfigurasi ``RPS_ALLOWED_EXTENSIONS`` tanpa mengubah kode.
DEFAULT_ALLOWED_EXTENSIONS: tuple[str, ...] = ("pdf",)

# Magic bytes PDF: file yang mengaku PDF tetapi isinya bukan PDF ditolak sebelum
# diproses, sehingga konverter tidak perlu menangani input yang jelas salah.
_PDF_MAGIC = b"%PDF-"
_ZIP_MAGIC = b"PK\x03\x04"  # DOCX (OOXML) adalah arsip ZIP

# Header yang dikenali per ekstensi.
_CONTENT_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "pdf": (_PDF_MAGIC,),
    "docx": (_ZIP_MAGIC,),
}

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
# Karakter yang tidak boleh ada pada nama file: pemisah path (Unix & Windows)
# serta karakter kontrol. Nama file hanya metadata, tetapi nilai yang memuat
# pemisah path tetap ditolak agar tidak ada tahap hilir yang tergoda
# menggunakannya sebagai path.
_FORBIDDEN_FILE_NAME_CHARS = ("/", "\\", "\x00")


def compute_file_hash(content: bytes) -> str:
    """SHA-256 dari isi file, dalam bentuk hex lowercase.

    SHA-256 dipakai karena nilai ini menjadi kunci deduplikasi dan idempotency
    (``rps.file_hash``, data-model §8/§27): dua unggahan dengan isi identik harus
    menghasilkan hash yang sama, dan collision harus tidak praktis.
    """
    if not isinstance(content, (bytes, bytearray)):
        raise RPSValidationError("content", "isi file harus berupa bytes")
    return hashlib.sha256(content).hexdigest()


def normalize_file_name(value: object) -> str:
    """Validasi dan normalisasi nama file asli dari client.

    Hanya nama dasarnya yang bermakna: pemisah path dan karakter kontrol
    ditolak, karena nama ini disimpan sebagai metadata dan ditampilkan kembali
    ke pengguna — bukan untuk membentuk path penyimpanan.
    """
    if not isinstance(value, str):
        raise RPSValidationError("file_name", "harus berupa teks")

    file_name = value.strip()
    if not file_name:
        raise RPSValidationError("file_name", "tidak boleh kosong atau hanya spasi")
    if any(char in file_name for char in _FORBIDDEN_FILE_NAME_CHARS):
        raise RPSValidationError("file_name", "tidak boleh mengandung pemisah path")
    if any(not char.isprintable() for char in file_name):
        raise RPSValidationError("file_name", "tidak boleh mengandung karakter kontrol")
    if len(file_name) > MAX_FILE_NAME_LENGTH:
        raise RPSValidationError("file_name", f"maksimal {MAX_FILE_NAME_LENGTH} karakter")
    return file_name


def file_extension(file_name: str) -> str:
    """Ekstensi file tanpa titik, dalam huruf kecil; ``""`` bila tidak ada.

    Dibaca manual (bukan ``Path.suffix``) supaya aturannya eksplisit dan sama
    untuk seluruh platform: hanya titik terakhir yang dianggap pemisah ekstensi,
    dan nama yang seluruhnya berupa ekstensi (``.pdf``) tidak dianggap punya
    ekstensi — file tanpa nama dasar bukan dokumen RPS yang valid.
    """
    base, _, extension = file_name.rpartition(".")
    if not base or not extension:
        return ""
    return extension.lower()


def normalize_file_type(value: object) -> str:
    """Normalisasi nilai kolom ``file_type`` (mis. ``PDF``), maksimal 20 karakter."""
    if not isinstance(value, str):
        raise RPSValidationError("file_type", "harus berupa teks")

    file_type = value.strip().upper()
    if not file_type:
        raise RPSValidationError("file_type", "tidak boleh kosong")
    if len(file_type) > MAX_FILE_TYPE_LENGTH:
        raise RPSValidationError("file_type", f"maksimal {MAX_FILE_TYPE_LENGTH} karakter")
    return file_type


def normalize_file_hash(value: object) -> str:
    """Validasi nilai ``file_hash`` sebagai SHA-256 hex lowercase.

    Bentuknya dipaksa tepat 64 karakter hex supaya kolom ``file_hash`` tidak
    pernah memuat nilai yang tidak dapat dipakai sebagai kunci deduplikasi.
    """
    if not isinstance(value, str):
        raise RPSValidationError("file_hash", "harus berupa teks")

    file_hash = value.strip().lower()
    if not _SHA256_PATTERN.match(file_hash):
        raise RPSValidationError("file_hash", "harus berupa SHA-256 hex 64 karakter")
    return file_hash


def normalize_file_path(value: object) -> str:
    """Validasi path penyimpanan **relatif** terhadap root storage.

    Path absolut dan path yang menunjuk ke luar root (``..``) ditolak di sini;
    :mod:`src.services.rps.storage` memeriksa ulang saat membaca, sehingga satu
    lapis kelalaian tidak cukup untuk membuat aplikasi menulis ke sembarang
    lokasi.
    """
    if not isinstance(value, str):
        raise RPSValidationError("file_path", "harus berupa teks")

    file_path = value.strip()
    if not file_path:
        raise RPSValidationError("file_path", "tidak boleh kosong")
    if file_path.startswith(("/", "\\")) or (len(file_path) > 1 and file_path[1] == ":"):
        raise RPSValidationError("file_path", "harus berupa path relatif")
    if any(part == ".." for part in re.split(r"[\\/]", file_path)):
        raise RPSValidationError("file_path", "tidak boleh menunjuk ke luar direktori storage")
    if len(file_path) > MAX_FILE_PATH_LENGTH:
        raise RPSValidationError("file_path", f"maksimal {MAX_FILE_PATH_LENGTH} karakter")
    return file_path


def normalize_schema_version(value: object) -> str:
    """Validasi versi skema RPS Structured Data yang berlaku untuk dokumen.

    Nilai ini bagian dari kunci idempotency (``file_hash`` + ``schema_version``),
    sehingga harus selalu terisi dan tidak ambigu.
    """
    if not isinstance(value, str):
        raise RPSValidationError("schema_version", "harus berupa teks")

    version = value.strip()
    if not version:
        raise RPSValidationError("schema_version", "tidak boleh kosong")
    if len(version) > MAX_SCHEMA_VERSION_LENGTH:
        raise RPSValidationError(
            "schema_version", f"maksimal {MAX_SCHEMA_VERSION_LENGTH} karakter"
        )
    return version


def normalize_status(value: object) -> RPSStatus:
    """Pastikan status hanya berisi nilai yang telah didefinisikan."""
    if isinstance(value, RPSStatus):
        return value
    if isinstance(value, str):
        try:
            return RPSStatus(value.strip().upper())
        except ValueError:
            pass

    valid_values = ", ".join(member.value for member in RPSStatus)
    raise RPSValidationError(
        "status", f"nilai tidak dikenal: {value!r}; nilai valid: {valid_values}"
    )


def normalize_identifier(value: object) -> str | None:
    """Validasi identifier RPS (ShortUUID) yang belum tentu tersedia.

    ``None`` untuk dokumen yang belum dipersist, karena identifier dibentuk oleh
    database foundation (BE-02). Identifier yang tidak berbentuk ShortUUID
    ditolak supaya nilai cacat tidak pernah sampai ke query database.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise RPSValidationError("id", "harus berupa teks atau None")

    identifier = value.strip()
    if len(identifier) != ID_LENGTH or any(
        char not in SHORTUUID_ALPHABET for char in identifier
    ):
        raise RPSValidationError(
            "id", f"bukan ShortUUID {ID_LENGTH} karakter yang valid: {value!r}"
        )
    return identifier


def ensure_supported_extension(extension: str, allowed: tuple[str, ...] | list[str]) -> str:
    """Pastikan ekstensi termasuk yang diizinkan; kembalikan ekstensi ternormalisasi."""
    normalized = extension.strip().lower()
    permitted = tuple(item.strip().lower() for item in allowed)
    if normalized not in permitted:
        listed = ", ".join(permitted) if permitted else "tidak ada"
        raise InvalidFileError(
            f"ekstensi {normalized or '(tanpa ekstensi)'!r} tidak didukung; "
            f"format yang diterima: {listed}"
        )
    return normalized


def ensure_size_within_limit(size_bytes: int, maximum_bytes: int) -> int:
    """Pastikan ukuran file tidak melebihi batas konfigurasi.

    File kosong juga ditolak: dokumen tanpa isi tidak akan pernah dapat
    dikonversi, sehingga lebih baik gagal saat unggah daripada saat pemrosesan.
    """
    if size_bytes <= 0:
        raise InvalidFileError("file kosong")
    if size_bytes > maximum_bytes:
        raise InvalidFileError(
            f"ukuran file {size_bytes} byte melebihi batas {maximum_bytes} byte"
        )
    return size_bytes


def ensure_matches_declared_type(content: bytes, extension: str) -> None:
    """Pastikan isi file sesuai dengan ekstensi yang diklaim.

    Ekstensi saja tidak cukup: file apa pun dapat diberi nama ``.pdf``. Untuk
    format yang dikenali, beberapa byte pertama diperiksa terhadap signature
    formatnya; format tanpa signature yang dikenal dilewatkan (pemeriksaan
    sesungguhnya dilakukan oleh konverter).
    """
    signatures = _CONTENT_SIGNATURES.get(extension)
    if not signatures:
        return
    if not content.startswith(signatures):
        raise InvalidFileError(
            f"isi file tidak sesuai dengan format {extension.upper()} yang diklaim"
        )
