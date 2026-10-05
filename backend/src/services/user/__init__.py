"""Domain User dan Role (BE-03.1) beserta application layer-nya (BE-03.2).

Paket ini melayani tiga konsumen tanpa memaksa mereka menyentuh ORM, session
database, maupun HTTP layer:

- :class:`User` (+ :mod:`src.services.user.validation`) — aturan identity,
  role, status, dan lifecycle (BE-03.1);
- :class:`UserService` — operasi aplikasi terhadap User: create, lookup,
  update, aktivasi/deaktivasi (BE-03.2). Authentication (BE-03.3) dan
  authorization (BE-03.4) memakai service ini, bukan query langsung;
- :class:`UserRepository` — akses data di dalam service layer, hanya boleh
  dipanggil oleh service.

:class:`UserRole` / :class:`UserStatus` di-*re-export* dari
``src.models.user`` (sumber tunggal nilai role dan status). Seluruh error
domain dipetakan ke HTTP oleh ``src.routes`` atau ``src.middlewares``.

Field identity (``username``, ``firstname``, ``lastname``, ``email``,
``password``) memakai nama atribut user Moodle; ``email`` tetap menjadi identity
attribute untuk login aplikasi.
"""

from src.services.user.domain import User
from src.services.user.enums import UserRole, UserStatus
from src.services.user.errors import (
    DuplicateEmailError,
    DuplicateUsernameError,
    UserDomainError,
    UserNotFoundError,
    UserValidationError,
)
from src.services.user.repository import UserRepository
from src.services.user.service import UserService
from src.services.user.validation import (
    MAX_EMAIL_LENGTH,
    MAX_FIRSTNAME_LENGTH,
    MAX_LASTNAME_LENGTH,
    MAX_PASSWORD_HASH_LENGTH,
    MAX_USERNAME_LENGTH,
)

__all__ = [
    "User",
    "UserRole",
    "UserStatus",
    "UserService",
    "UserRepository",
    "UserDomainError",
    "UserValidationError",
    "UserNotFoundError",
    "DuplicateEmailError",
    "DuplicateUsernameError",
    "MAX_USERNAME_LENGTH",
    "MAX_FIRSTNAME_LENGTH",
    "MAX_LASTNAME_LENGTH",
    "MAX_EMAIL_LENGTH",
    "MAX_PASSWORD_HASH_LENGTH",
]
