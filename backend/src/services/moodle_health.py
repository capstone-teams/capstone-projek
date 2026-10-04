from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from src.services.moodle_client import MoodleClient
from src.services.moodle_error_normalizer import normalize_moodle_error
from src.services.moodle_exceptions import MoodleError

SITE_INFO_FUNCTION = "core_webservice_get_site_info"


@dataclass(frozen=True)
class MoodleHealth:
    available: bool
    release: str | None = None
    latency_ms: int | None = None
    error_category: str | None = None
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "release": self.release,
            "latency_ms": self.latency_ms,
            "error_category": self.error_category,
            "message": self.message,
        }


class MoodleHealthChecker:
    def __init__(self, client: MoodleClient) -> None:
        self._client = client

    async def check(self) -> MoodleHealth:
        started = time.perf_counter()
        try:
            info = await self._client.call(SITE_INFO_FUNCTION)
        except MoodleError as exc:
            error = normalize_moodle_error(exc, SITE_INFO_FUNCTION)
            return MoodleHealth(
                available=False,
                latency_ms=_elapsed_ms(started),
                error_category=error.category.value,
                message=str(error),
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
        return MoodleHealth(available=True, release=str(release), latency_ms=latency)


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)