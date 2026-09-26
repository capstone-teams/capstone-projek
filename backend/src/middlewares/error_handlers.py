import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.services.auth.errors import AuthDomainError
from src.services.llm.base import LLMProviderError

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
    """Translate an authentication failure into 401 AUTHENTICATION_FAILED.

    Every cause (unknown email, wrong password, inactive user, missing or
    invalid token) returns the same public message, so the response cannot be
    used to enumerate users or credentials. The specific cause is only logged
    server-side, and never contains a credential or token value.
    """
    logger.warning("Authentication failure on %s: %s", request.url.path, exc.log_message)
    return _error_response(
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.public_message,
        headers={"WWW-Authenticate": "Bearer"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register the application-wide exception handlers."""
    app.add_exception_handler(LLMProviderError, llm_provider_error_handler)
    app.add_exception_handler(AuthDomainError, auth_error_handler)
