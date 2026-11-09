
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import httpx

from .moodle_exceptions import (
    MoodleAPIError,
    MoodleAuthenticationError,
    MoodleConnectionError,
    MoodleError,
    MoodlePermissionError,
    MoodleTimeoutError,
)

logger = logging.getLogger(__name__)

WEBSERVICE_PATH = "/webservice/rest/server.php"
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_BACKOFF_SECONDS = 0.5
MAX_BACKOFF_SECONDS = 5.0
REDACTED = "***"

# Parameters owned by the client. Callers may not set them, otherwise a caller
# could override the token or the requested function.
_RESERVED_PARAMS = frozenset({"wstoken", "wsfunction", "moodlewsrestformat"})

# Standard Moodle error codes. Moodle version of ITK is still TBD (see
# moodle-integration.md, section 4), so verify these against the target server.
_AUTHENTICATION_ERROR_CODES = frozenset(
    {
        "invalidtoken",
        "invalidtimedtoken",
        "wsaccessuserdeleted",
        "wsaccessuserexpired",
        "wsaccessusersuspended",
        "wsaccessusernologin",
    }
)
_PERMISSION_ERROR_CODES = frozenset(
    {
        "accessexception",
        "nopermissions",
        # User tidak terdaftar di course / belum login ke course tersebut.
        "errorcoursecontextnotvalid",
        "requireloginerror",
    }
)
_PERMISSION_EXCEPTION_NAMES = frozenset(
    {"webservice_access_exception", "required_capability_exception"}
)

# HTTP statuses that indicate a temporary problem on the server side.
_RETRYABLE_HTTP_STATUSES = frozenset({429, 502, 503, 504})


# Operasi tulis yang aman diulang: hasil akhirnya sama walaupun dijalankan dua kali.
_IDEMPOTENT_WRITE_FUNCTIONS = frozenset(
    {
        "core_course_update_courses",
        "core_update_inplace_editable",
        "enrol_manual_enrol_users",
    }
)
_IDEMPOTENT_WRITE_PREFIXES = ("local_capstonebridge_update_",)
# Create plugin aman diulang hanya bila membawa idempotency key (ID number):
# percobaan ulang mengembalikan activity yang sama, bukan membuat baru.
_KEYED_CREATE_PREFIX = "local_capstonebridge_create_"


def is_safe_to_retry(wsfunction: str, params: Mapping[str, Any] | None = None) -> bool:
    """Apakah ``wsfunction`` aman diulang otomatis setelah error transient.

    Operasi baca selalu aman. Operasi tulis hanya aman bila idempotent; contoh
    yang **tidak** aman: ``core_course_create_courses`` dan
    ``core_courseformat_update_course`` (setiap pemanggilan menambah objek baru).
    """
    name = wsfunction.strip()
    if "_get_" in name:
        return True
    if name in _IDEMPOTENT_WRITE_FUNCTIONS or name.startswith(_IDEMPOTENT_WRITE_PREFIXES):
        return True
    if name.startswith(_KEYED_CREATE_PREFIX):
        return bool(str((params or {}).get("idnumber") or "").strip())
    return False


def redact_token(text: str, token: str) -> str:
    """Replace every occurrence of `token` in `text` with a placeholder."""
    if not token:
        return text
    return text.replace(token, REDACTED)


def flatten_params(params: Mapping[str, Any]) -> dict[str, str]:
    """Encode nested params the way the Moodle REST endpoint expects.

    Moodle uses PHP-style keys, so:

        {"courseids": [1, 2]}
            -> {"courseids[0]": "1", "courseids[1]": "2"}
        {"courses": [{"fullname": "A", "visible": True}]}
            -> {"courses[0][fullname]": "A", "courses[0][visible]": "1"}

    `None` values are skipped and booleans become "1"/"0".
    """
    flat: dict[str, str] = {}

    def walk(prefix: str, value: Any) -> None:
        if value is None:
            return
        if isinstance(value, Mapping):
            for key, item in value.items():
                walk(f"{prefix}[{key}]", item)
        elif isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                walk(f"{prefix}[{index}]", item)
        elif isinstance(value, bool):
            flat[prefix] = "1" if value else "0"
        else:
            flat[prefix] = str(value)

    for key, value in params.items():
        walk(str(key), value)
    return flat


class MoodleClient:
    """Async, business-agnostic client for Moodle Web Service functions."""

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        verify: bool = True,
        transport: httpx.AsyncBaseTransport | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        base_url = (base_url or "").strip().rstrip("/")
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("Moodle base URL must start with http:// or https://")
        if not token or not token.strip():
            raise ValueError("Moodle web service token must not be empty")
        if timeout <= 0:
            raise ValueError("Moodle timeout must be greater than zero")
        if max_retries < 0:
            raise ValueError("Moodle max_retries must not be negative")
        if backoff_seconds < 0:
            raise ValueError("Moodle backoff_seconds must not be negative")

        self._base_url = base_url
        self._token = token.strip()
        self._endpoint = f"{base_url}{WEBSERVICE_PATH}"
        self._max_retries = max_retries
        self._backoff_seconds = backoff_seconds
        self._sleep = sleep
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            verify=verify,
            transport=transport,
            follow_redirects=False,
        )

    @classmethod
    def from_settings(cls, settings: Any, **kwargs: Any) -> MoodleClient:
        """Build a client from `src.config.settings.Settings`.

        Timeout diambil dari ``MOODLE_TIMEOUT_SECONDS`` (default 10 detik)
        kecuali caller memberikan ``timeout`` secara eksplisit.
        """
        kwargs.setdefault(
            "timeout",
            getattr(settings, "moodle_timeout_seconds", None) or DEFAULT_TIMEOUT_SECONDS,
        )
        return cls(
            settings.MOODLE_BASE_URL,
            settings.MOODLE_WEB_SERVICE_TOKEN,
            **kwargs,
        )

    def __repr__(self) -> str:
        return f"MoodleClient(base_url={self._base_url!r})"

    __str__ = __repr__

    async def __aenter__(self) -> MoodleClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def call(
        self,
        wsfunction: str,
        params: Mapping[str, Any] | None = None,
        *,
        retry: bool | None = None,
    ) -> Any:
        """Call one Moodle Web Service function and return its parsed JSON.

        Raises a `MoodleError` subclass on any failure. Never returns
        credentials, and never raises raw httpx or Moodle payloads.

        Error transient (timeout, koneksi, HTTP 429/502/503/504) diulang paling
        banyak ``max_retries`` kali dengan backoff eksponensial, **hanya** bila
        operasinya aman diulang (lihat :func:`is_safe_to_retry`). ``retry``
        memaksa keputusan itu. Error authentication, permission, dan validation
        tidak pernah diulang.
        """
        if not wsfunction or not wsfunction.strip():
            raise ValueError("wsfunction must not be empty")
        params = params or {}
        clashing = _RESERVED_PARAMS.intersection(params)
        if clashing:
            raise ValueError(
                f"Params must not contain client-owned keys: {sorted(clashing)}"
            )

        form = {
            "wstoken": self._token,
            "wsfunction": wsfunction,
            "moodlewsrestformat": "json",
            **flatten_params(params),
        }

        retry_allowed = is_safe_to_retry(wsfunction, params) if retry is None else retry
        attempts = 1 + (self._max_retries if retry_allowed else 0)
        started = time.perf_counter()
        for attempt in range(1, attempts + 1):
            try:
                result = await self._request(wsfunction, form)
                break
            except MoodleError as exc:
                if exc.retryable and attempt < attempts:
                    delay = min(self._backoff_seconds * 2 ** (attempt - 1), MAX_BACKOFF_SECONDS)
                    logger.info(
                        "Moodle call retrying: wsfunction=%s type=%s code=%s "
                        "attempt=%d/%d delay_s=%.2f",
                        wsfunction,
                        exc.error_type,
                        exc.code,
                        attempt,
                        attempts,
                        delay,
                    )
                    await self._sleep(delay)
                    continue
                logger.warning(
                    "Moodle call failed: wsfunction=%s type=%s code=%s "
                    "http_status=%s attempts=%d duration_ms=%d",
                    wsfunction,
                    exc.error_type,
                    exc.code,
                    exc.http_status,
                    attempt,
                    _elapsed_ms(started),
                )
                raise

        logger.debug(
            "Moodle call succeeded: wsfunction=%s duration_ms=%d",
            wsfunction,
            _elapsed_ms(started),
        )
        return result

    async def _request(self, wsfunction: str, form: dict[str, str]) -> Any:
        try:
            response = await self._http.post(self._endpoint, data=form)
        except httpx.TimeoutException as exc:
            raise MoodleTimeoutError(
                "Moodle did not respond in time",
                wsfunction=wsfunction,
            ) from exc
        except httpx.TransportError as exc:
            raise MoodleConnectionError(
                f"Could not connect to Moodle: {self._safe(str(exc))}",
                wsfunction=wsfunction,
            ) from exc
        except httpx.HTTPError as exc:
            raise MoodleAPIError(
                f"HTTP error while calling Moodle: {self._safe(str(exc))}",
                wsfunction=wsfunction,
            ) from exc

        self._raise_for_http_status(response, wsfunction)

        try:
            payload = response.json()
        except ValueError as exc:
            raise MoodleAPIError(
                "Moodle returned a response that is not valid JSON",
                code="invalid_response",
                http_status=response.status_code,
                wsfunction=wsfunction,
            ) from exc

        self._raise_for_moodle_error(payload, response.status_code, wsfunction)
        return payload

    def _raise_for_http_status(self, response: httpx.Response, wsfunction: str) -> None:
        status = response.status_code
        if status < 400:
            return
        if status == 401:
            raise MoodleAuthenticationError(
                "Moodle rejected the credential (HTTP 401)",
                http_status=status,
                wsfunction=wsfunction,
            )
        if status == 403:
            raise MoodlePermissionError(
                "Moodle denied access (HTTP 403)",
                http_status=status,
                wsfunction=wsfunction,
            )
        raise MoodleAPIError(
            f"Moodle returned HTTP {status}",
            http_status=status,
            wsfunction=wsfunction,
            retryable=status in _RETRYABLE_HTTP_STATUSES,
        )

    def _raise_for_moodle_error(
        self, payload: Any, http_status: int, wsfunction: str
    ) -> None:
        """Moodle reports most errors as HTTP 200 with an `exception` payload."""
        if not (
            isinstance(payload, dict) and "exception" in payload and "errorcode" in payload
        ):
            return

        code = self._safe(str(payload.get("errorcode")))
        exception_name = str(payload.get("exception"))
        message = self._safe(str(payload.get("message") or "Unknown Moodle error"))
        # `debuginfo` is deliberately ignored: it can leak server internals.
        common = {"code": code, "http_status": http_status, "wsfunction": wsfunction}

        if code in _AUTHENTICATION_ERROR_CODES:
            raise MoodleAuthenticationError(message, **common)
        if (
            code in _PERMISSION_ERROR_CODES
            or exception_name in _PERMISSION_EXCEPTION_NAMES
        ):
            raise MoodlePermissionError(message, **common)
        raise MoodleAPIError(message, **common)

    def _safe(self, text: str) -> str:
        return redact_token(text, self._token)


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)