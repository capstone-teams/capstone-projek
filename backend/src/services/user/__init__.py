"""Domain User dan Role (BE-03.1).

Paket ini menyediakan representasi domain User yang dipakai oleh User Service
(BE-03.2), authentication (BE-03.3), dan authorization (BE-03.4) tanpa perlu
menyentuh ORM, session database, maupun HTTP layer.

- :class:`User` — domain model beserta aturan identity dan lifecycle;
- :class:`UserRole` / :class:`UserStatus` — re-export dari ``src.models.user``
  (sumber tunggal nilai role dan status, tanpa duplikasi);
- :class:`UserDomainError` / :class:`UserValidationError` — error domain yang
  dipetakan ke HTTP oleh ``src.routes`` atau ``src.middlewares``.
"""

from src.services.user.domain import User
from src.services.user.enums import UserRole, UserStatus
from src.services.user.errors import UserDomainError, UserValidationError
from src.services.user.validation import (
    MAX_EMAIL_LENGTH,
    MAX_NAME_LENGTH,
    MAX_PASSWORD_HASH_LENGTH,
)

__all__ = [
    "User",
    "UserRole",
    "UserStatus",
    "UserDomainError",
    "UserValidationError",
    "MAX_NAME_LENGTH",
    "MAX_EMAIL_LENGTH",
    "MAX_PASSWORD_HASH_LENGTH",
]
