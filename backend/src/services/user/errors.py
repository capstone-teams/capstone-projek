"""Error domain User.

Error domain berada di layer service dan tidak boleh berupa HTTPException.
Pemetaan ke status HTTP dilakukan oleh ``src/routes`` atau
``src/middlewares`` (lihat ``backend/README.md``).
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
