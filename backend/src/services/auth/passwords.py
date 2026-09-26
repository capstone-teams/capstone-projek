"""Password hashing untuk local authentication (BE-03.3).

Mekanisme authentication final aplikasi memakai credential lokal, sehingga
``User.password_hash`` diisi hash bcrypt — password mentah tidak pernah
disimpan. Modul ini tidak menyentuh database maupun HTTP.
"""

from __future__ import annotations

from passlib.context import CryptContext

__all__ = ["MAX_PASSWORD_LENGTH", "MIN_PASSWORD_LENGTH", "hash_password", "verify_password"]

_password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

MIN_PASSWORD_LENGTH = 8

# bcrypt hanya memakai 72 byte pertama password; batas ini juga mencegah
# percobaan login dengan input sangat panjang.
MAX_PASSWORD_LENGTH = 72


def hash_password(password: str) -> str:
    """Bentuk hash bcrypt untuk disimpan pada ``User.password_hash``."""
    _validate_password(password)
    return _password_context.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    """Verifikasi password terhadap hash tersimpan.

    ``password_hash`` kosong berarti user tidak memiliki credential lokal
    (lihat catatan BE-03.1) dan selalu gagal. Dalam kasus itu verifikasi dummy
    tetap dijalankan agar waktu respons tidak membocorkan apakah user/credential
    ada atau tidak.
    """
    if not password_hash:
        _password_context.dummy_verify()
        return False

    try:
        return _password_context.verify(password, password_hash)
    except (TypeError, ValueError):
        # Hash tersimpan rusak atau bukan format yang dikenali: perlakukan
        # sebagai kredensial tidak valid tanpa membocorkan detailnya.
        return False


def _validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"password minimal {MIN_PASSWORD_LENGTH} karakter")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"password maksimal {MAX_PASSWORD_LENGTH} karakter")
