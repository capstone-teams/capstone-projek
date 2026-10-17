import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.services.auth.errors import AuthDomainError
from src.services.llm.base import LLMProviderError
from src.services.rps.errors import RPSDomainError
from src.services.user.errors import UserNotFoundError

logger = logging.getLogger(__name__)


def _error_response(
    *,
    status_code: int,
    error_code: str,
    message: str,
    headers: dict[str, str] | None = None,
    details: list[dict[str, str]] | None = None,
) -> JSONResponse:
    """Build the standard API error envelope (design-api §18)."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": error_code,
                "message": message,
                "details": details or [],
            }
        },
        headers=headers,
    )


def _validation_details(exc: RequestValidationError) -> list[dict[str, str]]:
    """Ringkas error validasi request menjadi ``details`` yang aman.

    Hanya lokasi dan pesan validasi yang dikembalikan. Nilai input sengaja
    **tidak** disalin ke response: body login memuat password, sehingga echo
    input akan membocorkan credential ke response dan melanggar design-api §23.
    """
    details: list[dict[str, str]] = []
    for error in exc.errors():
        location = [str(part) for part in error.get("loc", ()) if part != "body"]
        details.append(
            {
                "field": ".".join(location) or "body",
                "message": str(error.get("msg", "Nilai tidak valid.")),
            }
        )
    return details


async def request_validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Kembalikan 422 ``VALIDATION_FAILED`` dengan amplop error standar.

    Tanpa handler ini FastAPI memakai bentuk default ``{"detail": [...]}`` yang
    berbeda dari design-api §18, sehingga frontend harus menangani dua bentuk
    error. Handler ini menyatukannya untuk seluruh endpoint, dan tidak pernah
    mengembalikan nilai input yang dikirim client.
    """
    logger.info("Request validation failed on %s", request.url.path)
    return _error_response(
        status_code=422,
        error_code="VALIDATION_FAILED",
        message="Data request tidak valid.",
        details=_validation_details(exc),
    )


async def llm_provider_error_handler(request: Request, exc: LLMProviderError) -> JSONResponse:
    """Translate an LLM provider failure into the standard API error format.

    The provider detail is logged server-side; the client only receives the
    generic public message so upstream payloads and credentials cannot leak
    through an error response.
    """
    logger.warning("LLM provider failure on %s: %s", request.url.path, exc)
    return _error_response(
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.public_message,
    )


async def auth_error_handler(request: Request, exc: AuthDomainError) -> JSONResponse:
    """Translate an authentication/authorization failure into the API error format.

    Authentication failures return 401 ``AUTHENTICATION_FAILED``. Every cause
    (unknown email, wrong password, inactive user, missing or invalid token)
    returns the same public message, so the response cannot be used to
    enumerate users or credentials. The specific cause is only logged
    server-side, and never contains a credential or token value.

    Authorization failures (BE-03.4) return 403 ``AUTHORIZATION_DENIED``: the
    caller is already identified, so this is not an authentication failure and
    the response carries no ``WWW-Authenticate`` challenge. It also does not
    reveal which role would have been required.
    """
    logger.warning(
        "Authentication/authorization failure on %s: %s", request.url.path, exc.log_message
    )
    return _error_response(
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.public_message,
        headers={"WWW-Authenticate": "Bearer"} if exc.challenge else None,
    )


async def user_not_found_error_handler(request: Request, exc: UserNotFoundError) -> JSONResponse:
    """Translate a missing domain resource into 404 RESOURCE_NOT_FOUND.

    The requested identifier stays server-side, so the response carries no
    entity detail.
    """
    logger.warning("Resource not found on %s: %s", request.url.path, exc)
    return _error_response(
        status_code=404,
        error_code="RESOURCE_NOT_FOUND",
        message="Resource tidak ditemukan.",
    )


async def rps_error_handler(request: Request, exc: RPSDomainError) -> JSONResponse:
    """Translate an RPS domain failure into the standard API error format (BE-05).

    Every RPS error already carries its public contract (``error_code``,
    ``status_code``, ``public_message``), so this handler only applies it:
    invalid uploads become 400 ``INVALID_FILE``, missing documents 404
    ``RESOURCE_NOT_FOUND``, conflicting state 409 ``INVALID_REQUEST``, and a
    failed conversion 500 ``RPS_PROCESSING_FAILED``.

    The underlying cause — a conversion library message, a filesystem path, or
    part of the document — is logged server-side only and never returned.
    """
    logger.warning("RPS failure on %s: %s", request.url.path, exc.log_message)
    return _error_response(
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.public_message,
    )


ERROR_RESPONSE_SCHEMA_REF = "#/components/schemas/ErrorResponse"


def _document_standard_validation_error(app: FastAPI) -> None:
    """Ganti schema 422 default FastAPI dengan amplop error design-api §18.

    ``request_validation_error_handler`` membuat response 422 yang sebenarnya
    memakai amplop standar. OpenAPI, bagaimanapun, tetap menyertakan
    ``HTTPValidationError`` default pada setiap endpoint yang memiliki body atau
    path parameter. Tanpa penyesuaian ini dokumentasi endpoint selain
    authentication akan menampilkan bentuk error yang tidak pernah dikirim
    server.

    Response 422 yang sudah didokumentasikan eksplisit (mis. login) dibiarkan,
    sehingga contoh dan deskripsinya tidak tertimpa.
    """
    original_openapi = app.openapi

    def openapi() -> dict:
        schema = original_openapi()
        for path_item in schema.get("paths", {}).values():
            for operation in path_item.values():
                if not isinstance(operation, dict):
                    continue
                response = operation.get("responses", {}).get("422")
                if response is None:
                    continue
                media_type = response.setdefault("content", {}).setdefault(
                    "application/json", {}
                )
                current_ref = media_type.get("schema", {}).get("$ref", "")
                if current_ref.endswith("/ErrorResponse"):
                    continue

                media_type["schema"] = {"$ref": ERROR_RESPONSE_SCHEMA_REF}
                response["description"] = (
                    "Request tidak valid. Body mengikuti design-api §18; "
                    "`error.code` adalah `VALIDATION_FAILED` untuk schema request "
                    "atau `INVALID_REQUEST` untuk nilai domain."
                )
        return schema

    app.openapi = openapi  # type: ignore[method-assign]


def register_exception_handlers(app: FastAPI) -> None:
    """Register the application-wide exception handlers.

    Handler validasi request juga menyelaraskan schema 422 pada OpenAPI, supaya
    dokumentasi menampilkan amplop error yang benar-benar dikirim server.
    """
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)
    app.add_exception_handler(LLMProviderError, llm_provider_error_handler)
    app.add_exception_handler(AuthDomainError, auth_error_handler)
    app.add_exception_handler(UserNotFoundError, user_not_found_error_handler)
    app.add_exception_handler(RPSDomainError, rps_error_handler)
    _document_standard_validation_error(app)
