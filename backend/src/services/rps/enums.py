"""Sumber tunggal nilai status RPS.

Nilai status didefinisikan pada BE-02 di ``src.models.rps`` karena sekaligus
dipakai sebagai tipe kolom database (native enum PostgreSQL: ``rps_status``).
Modul ini hanya me-*re-export* nilai tersebut agar layer domain — dan
konsumennya seperti :class:`~src.services.rps.service.RPSService` — tidak perlu
mengimpor modul ORM, dan agar tidak ada nilai status yang diduplikasi.
"""

from src.models.rps import RPSStatus

__all__ = ["RPSStatus"]
