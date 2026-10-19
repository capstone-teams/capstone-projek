from __future__ import annotations

import logging
import time
from collections.abc import Mapping
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
_PERMISSION_ERROR_CODES = frozenset({"accessexception", "nopermissions"})
_PERMISSION_EXCEPTION_NAMES = frozenset(
    {"webservice_access_exception", "required_capability_exception"}
)

# HTTP statuses that indicate a temporary problem on the server side.
_RETRYABLE_HTTP_STATUSES = frozenset({429, 502, 503, 504})


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
    ) -> None:
        base_url = (base_url or "").strip().rstrip("/")
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("Moodle base URL must start with http:// or https://")
        if not token or not token.strip():
            raise ValueError("Moodle web service token must not be empty")
        if timeout <= 0:
            raise ValueError("Moodle timeout must be greater than zero")

        self._base_url = base_url
        self._token = token.strip()
        self._endpoint = f"{base_url}{WEBSERVICE_PATH}"
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            verify=verify,
            transport=transport,
            follow_redirects=False,
        )

    @classmethod
    def from_settings(cls, settings: Any, **kwargs: Any) -> MoodleClient:
        """Build a client from `src.config.settings.Settings`."""
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
    ) -> Any:
        """Call one Moodle Web Service function and return its parsed JSON.

        Raises a `MoodleError` subclass on any failure. Never returns
        credentials, and never raises raw httpx or Moodle payloads.
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

        started = time.perf_counter()
        try:
            result = await self._request(wsfunction, form)
        except MoodleError as exc:
            logger.warning(
                "Moodle call failed: wsfunction=%s type=%s code=%s "
                "http_status=%s duration_ms=%d",
                wsfunction,
                exc.error_type,
                exc.code,
                exc.http_status,
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