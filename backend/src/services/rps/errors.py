"""Error domain RPS (BE-05).

Error domain berada di layer service dan **bukan** ``HTTPException``; pemetaan ke
status HTTP dilakukan oleh ``src/middlewares`` (lihat ``backend/README.md``).
Setiap error membawa kontrak publik yang sama seperti error LLM (BE-03):

- ``error_code`` — kode pada envelope error (``design-api.md`` §18);
- ``status_code`` — status HTTP yang sesuai (``design-api.md`` §19);
- ``public_message`` — pesan aman untuk client;
- ``log_message`` — detail untuk log server-side, tidak pernah dikirim ke client.

Kode error diambil dari daftar resmi design-api §18 (``INVALID_FILE``,
``RPS_PROCESSING_FAILED``, ``RESOURCE_NOT_FOUND``, ``INVALID_REQUEST``), sehingga
client dapat menangani kegagalan RPS tanpa menebak-nebak.
"""

from __future__ import annotations

__all__ = [
    "DocumentConversionError",
    "DocumentConverterUnavailableError",
    "DocumentStorageError",
    "InvalidFileError",
    "RPSDomainError",
    "RPSNotFoundError",
    "RPSStateError",
    "RPSValidationError",
]


class RPSDomainError(Exception):
    """Base error domain RPS.

    Tiga hal yang dibawa setiap error domain RPS:

    - ``error_code`` / ``status_code`` / ``public_message`` — kontrak HTTP pada
      envelope error (design-api §18/§19);
    - ``log_message`` — detail untuk log server-side, tidak pernah dikirim ke
      client;
    - ``public_reason`` — penjelasan singkat yang **aman** ditampilkan ke client
      dan lebih spesifik daripada ``public_message``. Diperlukan karena
      pemrosesan RPS berjalan di background: kegagalannya tidak dapat muncul
      pada response request, sehingga alasan yang dapat dipahami client harus
      disimpan pada dokumen (``rps.processing_error``) dan dibaca lewat polling.

    ``public_reason`` bawaannya sama dengan ``public_message``; subclass yang
    tahu penyebabnya memberi nilai yang lebih spesifik.
    """

    error_code = "INTERNAL_ERROR"
    status_code = 500
    public_message = "Permintaan RPS gagal."

    def __init__(self, log_message: str | None = None, *, public_reason: str | None = None) -> None:
        self.log_message = log_message or type(self).__name__
        self.public_reason = public_reason or self.public_message
        super().__init__(self.log_message)


class RPSValidationError(RPSDomainError):
    """Nilai/atribut RPS tidak memenuhi aturan domain.

    Membawa atribut ``field`` supaya layer pemanggil dapat memetakan error tanpa
    menebak atribut mana yang tidak valid. Dipakai untuk nilai yang *bentuknya*
    salah (misalnya hash bukan SHA-256), bukan untuk file unggahan — file punya
    :class:`InvalidFileError` dengan status dan kode tersendiri.
    """

    error_code = "INVALID_REQUEST"
    status_code = 422
    public_message = "Data RPS tidak valid."

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


class InvalidFileError(RPSDomainError):
    """File unggahan tidak dapat diterima.

    Mencakup tipe file di luar daftar yang diizinkan, ukuran melebihi batas,
    file kosong, dan isi yang tidak sesuai dengan tipenya (design-api §23.8:
    "File upload harus divalidasi berdasarkan type dan size"). ``reason`` adalah
    alasan internal yang dicatat server-side.
    """

    error_code = "INVALID_FILE"
    status_code = 400
    public_message = "File RPS tidak valid."

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class RPSNotFoundError(RPSDomainError):
    """RPS yang diminta tidak ada **atau** bukan milik peminta.

    Kedua keadaan sengaja menghasilkan error yang sama supaya keberadaan RPS
    milik instruktur lain tidak dapat diketahui dari perbedaan response
    (bandingkan design-api §23.3).
    """

    error_code = "RESOURCE_NOT_FOUND"
    status_code = 404
    public_message = "RPS tidak ditemukan."

    def __init__(self, identifier: object) -> None:
        self.identifier = identifier
        super().__init__(f"rps tidak ditemukan: {identifier}")


class RPSStateError(RPSDomainError):
    """Status RPS tidak mengizinkan operasi yang diminta (HTTP 409).

    Contoh: dokumen sedang ``PROCESSING`` lalu diminta diproses lagi oleh
    request lain. Ini bukan kegagalan validasi input, melainkan konflik state.
    """

    error_code = "INVALID_REQUEST"
    status_code = 409
    public_message = "Status RPS tidak mengizinkan operasi ini."

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class DocumentStorageError(RPSDomainError):
    """Penyimpanan berkas dokumen gagal (disk penuh, izin, berkas hilang).

    Terpisah dari kegagalan konversi supaya log dapat membedakan "dokumennya
    tidak dapat dibaca" dari "dokumennya tidak dapat dikonversi" — dua hal yang
    membutuhkan tindakan berbeda. Pesan dari sistem berkas hanya dicatat
    server-side karena memuat path internal.
    """

    error_code = "INTERNAL_ERROR"
    status_code = 500
    public_message = "Penyimpanan dokumen gagal."

    def __init__(self, reason: str, *, public_reason: str | None = None) -> None:
        self.reason = reason
        super().__init__(reason, public_reason=public_reason)


class DocumentConversionError(RPSDomainError):
    """Konversi dokumen menjadi representasi terstruktur gagal.

    Penyebab sebenarnya hanya dicatat server-side: pesan dari library konversi
    dapat memuat path internal maupun potongan isi dokumen. Yang dibawa ke client
    adalah ``public_reason`` — penjelasan singkat yang ditulis tangan pada titik
    kegagalannya (lihat :mod:`src.services.rps.docling_converter`).
    """

    error_code = "RPS_PROCESSING_FAILED"
    status_code = 500
    public_message = "Pemrosesan RPS gagal."
    #: Penjelasan bawaan yang aman bila titik kegagalan tidak memberi yang lebih
    #: spesifik. Sengaja tidak menyebut detail internal apa pun.
    default_public_reason = "Dokumen RPS gagal diproses oleh konverter."

    def __init__(self, reason: str, *, public_reason: str | None = None) -> None:
        self.reason = reason
        super().__init__(
            reason, public_reason=public_reason or self.default_public_reason
        )


class DocumentConverterUnavailableError(DocumentConversionError):
    """Converter dokumen tidak dapat dipakai di lingkungan ini.

    Terpisah dari kegagalan konversi biasa karena penyebabnya adalah konfigurasi
    deployment (misalnya dependensi opsional Docling belum terpasang), bukan
    dokumen yang diproses. Status HTTP tetap 500 agar tidak memperkenalkan kode
    status di luar daftar design-api §19.
    """

    default_public_reason = (
        "Konverter dokumen tidak tersedia di server ini; hubungi administrator."
    )

    def __init__(self, reason: str, *, public_reason: str | None = None) -> None:
        super().__init__(reason, public_reason=public_reason)
