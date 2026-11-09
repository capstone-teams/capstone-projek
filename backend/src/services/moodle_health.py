"""Pemeriksaan koneksi ke Moodle Web Service.

Memanggil ``core_webservice_get_site_info`` satu kali (tanpa retry) lalu
melaporkan versi Moodle, daftar function yang tersedia untuk token, dan function
wajib yang belum terdaftar pada external service. Kegagalan dilaporkan sebagai
hasil, bukan exception, dan tidak pernah memuat token.
"""

from __future__ import annotations

import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from src.services.moodle_client import MoodleClient
from src.services.moodle_exceptions import (
    MoodleAuthenticationError,
    MoodleError,
    MoodlePermissionError,
)

SITE_INFO_FUNCTION = "core_webservice_get_site_info"

# Function minimum yang dibutuhkan Moodle Integration Layer
# (lihat docs/02. design/moodle-integration-contract.md).
REQUIRED_FUNCTIONS = (
    SITE_INFO_FUNCTION,
    "core_course_get_courses",
    "core_course_get_courses_by_field",
    "core_course_create_courses",
    "core_course_update_courses",
    "core_course_get_contents",
    "local_capstonebridge_create_page",
    "local_capstonebridge_create_assign",
)


@dataclass(frozen=True)
class MoodleHealth:
    available: bool
    site_name: str | None = None
    release: str | None = None
    version: str | None = None
    latency_ms: int | None = None
    functions: tuple[str, ...] = ()
    missing_functions: tuple[str, ...] = ()
    error_category: str | None = None
    message: str | None = None

    @property
    def ready(self) -> bool:
        """Moodle terjangkau dan seluruh function wajib tersedia."""
        return self.available and not self.missing_functions

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "ready": self.ready,
            "site_name": self.site_name,
            "release": self.release,
            "version": self.version,
            "latency_ms": self.latency_ms,
            "functions": list(self.functions),
            "missing_functions": list(self.missing_functions),
            "error_category": self.error_category,
            "message": self.message,
        }


class MoodleHealthChecker:
    def __init__(
        self,
        client: MoodleClient,
        required_functions: Iterable[str] = REQUIRED_FUNCTIONS,
    ) -> None:
        self._client = client
        self._required_functions = tuple(required_functions)

    async def check(self) -> MoodleHealth:
        started = time.perf_counter()
        try:
            info = await self._client.call(SITE_INFO_FUNCTION, retry=False)
        except MoodleError as exc:
            return MoodleHealth(
                available=False,
                latency_ms=_elapsed_ms(started),
                error_category=_category(exc),
                message=exc.message,
            )

        latency = _elapsed_ms(started)
        release = info.get("release") if isinstance(info, dict) else None
        if not release:
            return MoodleHealth(
                available=False,
                latency_ms=latency,
                error_category="execution",
                message="Moodle menjawab tetapi isi site info tidak valid.",
            )

        functions = _function_names(info)
        missing = tuple(name for name in self._required_functions if name not in functions)
        version = info.get("version")
        return MoodleHealth(
            available=True,
            site_name=info.get("sitename") or None,
            release=str(release),
            version=str(version) if version is not None else None,
            latency_ms=latency,
            functions=tuple(sorted(functions)),
            missing_functions=missing,
        )


def _category(error: MoodleError) -> str:
    if isinstance(error, MoodleAuthenticationError):
        return "authentication"
    if isinstance(error, MoodlePermissionError):
        return "permission"
    if error.retryable:
        return "transient"
    return "execution"


def _function_names(info: dict[str, Any]) -> set[str]:
    entries = info.get("functions") or []
    return {entry["name"] for entry in entries if isinstance(entry, dict) and "name" in entry}


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)