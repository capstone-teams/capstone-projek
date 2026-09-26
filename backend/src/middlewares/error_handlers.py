import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.services.auth.errors import AuthDomainError
from src.services.llm.base import LLMProviderError
from src.services.user.errors import UserNotFoundError

logger = logging.getLogger(__name__)


def _error_response(
    *,
    status_code: int,
    error_code: str,
    message: str,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Build the standard API error envelope (design-api §18)."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": error_code,
                "message": message,
                "details": [],
            }
        },
        headers=headers,
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


def register_exception_handlers(app: FastAPI) -> None:
    """Register the application-wide exception handlers."""
    app.add_exception_handler(LLMProviderError, llm_provider_error_handler)
    app.add_exception_handler(AuthDomainError, auth_error_handler)
    app.add_exception_handler(UserNotFoundError, user_not_found_error_handler)
