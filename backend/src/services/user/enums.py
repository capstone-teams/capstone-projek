"""Sumber tunggal nilai role dan status User.

Nilai role/status didefinisikan pada BE-02 di ``src.models.user`` karena
sekaligus dipakai sebagai tipe kolom database (native enum PostgreSQL:
``userrole`` dan ``userstatus``). Modul ini hanya me-*re-export* keduanya agar
layer domain — dan konsumennya seperti User Service, authentication, serta
authorization — tidak perlu mengimpor modul ORM, dan agar tidak ada nilai role
atau status yang diduplikasi di tempat lain.
"""

from src.models.user import UserRole, UserStatus

__all__ = ["UserRole", "UserStatus"]
