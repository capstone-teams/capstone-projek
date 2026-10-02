"""Error domain User.

Error domain berada di layer service dan tidak boleh berupa HTTPException.
Pemetaan ke status HTTP dilakukan oleh ``src/routes`` atau
``src/middlewares`` (lihat ``backend/README.md``).

Saran pemetaan HTTP untuk konsumen (BE-03.3/BE-03.4):

- :class:`UserValidationError` → 422/400 (input tidak valid);
- :class:`UserNotFoundError` → 404;
- :class:`DuplicateEmailError` → 409.
"""


class UserDomainError(Exception):
    """Base error untuk seluruh pelanggaran aturan domain User."""


class UserValidationError(UserDomainError):
    """Nilai identity/atribut User tidak memenuhi aturan domain.

    Membawa atribut ``field`` supaya layer pemanggil dapat memetakan error ke
    response HTTP tanpa harus menebak atribut mana yang tidak valid.
    """

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


class UserNotFoundError(UserDomainError):
    """User yang diminta tidak ditemukan.

    ``identifier`` dapat berupa UUID maupun email, tergantung operasi yang
    gagal, supaya pesan error konsisten untuk kedua jalur pencarian.
    """

    def __init__(self, identifier: object) -> None:
        self.identifier = identifier
        super().__init__(f"user tidak ditemukan: {identifier}")


class DuplicateEmailError(UserDomainError):
    """Email sudah dipakai user lain (email adalah unique identity attribute)."""

    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"email sudah terdaftar: {email}")
