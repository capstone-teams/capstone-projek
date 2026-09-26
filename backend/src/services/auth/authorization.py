"""Mekanisme authorization berbasis role (BE-03.4).

Authentication (BE-03.3) menjawab **"siapa User ini?"**, authorization menjawab
**"bolehkah User ini menjalankan operation ini?"**. Modul ini hanya memuat
keputusan allow/deny berdasarkan role pada record User yang sudah
terautentikasi:

- tanpa FastAPI, tanpa session/database, dan tanpa aturan fitur tertentu,
  sehingga keputusannya dapat diuji sebagai logika murni;
- role **selalu** berasal dari record User yang dipulihkan
  ``AuthService.get_authenticated_user`` (baca ulang dari database), bukan dari
  payload, query, header, maupun klaim token yang dikirim client;
- pemakaian ulang oleh endpoint disediakan
  :func:`src.services.dependencies.require_roles`, sehingga tidak ada
  pengecekan role yang ditulis ulang (maupun tersebar) di setiap handler.

Pemakaian pada endpoint:

```python
# require_roles(...) sebagai dependency: authorization selesai sebelum handler
# (dan business operation di dalamnya) dijalankan.
@router.post("", response_model=..., dependencies=[Depends(require_roles(UserRole.ADMIN))])
async def admin_operation(...): ...

# atau bila handler membutuhkan identitas user yang sudah diotorisasi:
@router.get("")
async def read_operation(
    current_user: User = Depends(require_roles(UserRole.INSTRUCTOR)),
): ...
```

:class:`RolePolicy` sengaja berupa value object kecil agar perluasan ke
resource/policy authorization pada tahap berikutnya cukup dilakukan dengan
menambah aturan pada :meth:`RolePolicy.enforce` atau menyediakan policy baru
dengan bentuk yang sama — tanpa mengubah bentuk pemakaian di endpoint.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from src.services.auth.errors import AuthorizationError, AuthorizationPolicyError
from src.services.user.domain import User
from src.services.user.enums import UserRole
from src.services.user.errors import UserValidationError
from src.services.user.validation import normalize_role

__all__ = ["RolePolicy"]


@dataclass(frozen=True, slots=True)
class RolePolicy:
    """Daftar role yang diizinkan menjalankan sebuah operation.

    Policy bersifat immutable dan dapat dibagi antar endpoint
    (single-role maupun multiple-role restriction).
    """

    roles: frozenset[UserRole]

    def __post_init__(self) -> None:
        normalized = frozenset(_as_role(role) for role in self.roles)
        if not normalized:
            # Policy tanpa role akan menolak semua orang; itu hampir selalu
            # salah tulis saat wiring endpoint, sehingga lebih baik gagal saat
            # policy didefinisikan (import time) daripada menghasilkan 403
            # yang menyesatkan saat runtime.
            raise AuthorizationPolicyError("role policy harus memuat minimal satu role")
        object.__setattr__(self, "roles", normalized)

    @classmethod
    def for_roles(cls, *roles: UserRole | str) -> "RolePolicy":
        """Bentuk policy dari satu atau beberapa role.

        Role divalidasi di sini, sehingga nilai yang tidak dikenal (misalnya
        ``"SUPERADMIN"``) langsung ditolak di tempat policy didefinisikan.
        """
        return cls(frozenset(_as_role(role) for role in roles))

    def allows(self, role: UserRole | str) -> bool:
        """Apakah role ini termasuk role yang diizinkan policy."""
        return _as_role(role) in self.roles

    def allows_user(self, user: User) -> bool:
        """Apakah user diizinkan, berdasarkan role pada record-nya.

        Tidak ada parameter role yang berasal dari request: role yang dipakai
        selalu ``user.role`` milik current user.
        """
        return user.role in self.roles

    def enforce(self, user: User) -> User:
        """Kembalikan user bila diizinkan; selain itu lempar :class:`AuthorizationError`.

        Mengembalikan user (bukan hanya ``None``) supaya dependency dapat
        meneruskan identitas yang sudah diotorisasi ke handler.
        """
        if not self.allows_user(user):
            raise AuthorizationError(
                user_id=user.id,
                user_role=user.role,
                required_roles=self.roles,
            )
        return user


def _as_role(role: UserRole | str) -> UserRole:
    """Normalisasi role memakai aturan domain User (sumber tunggal nilai role)."""
    try:
        return normalize_role(role)
    except UserValidationError as exc:
        raise AuthorizationPolicyError(f"role tidak dikenal pada role policy: {exc}") from exc
