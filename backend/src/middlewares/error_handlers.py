import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.services.llm.base import LLMProviderError

logger = logging.getLogger(__name__)


async def llm_provider_error_handler(request: Request, exc: LLMProviderError) -> JSONResponse:
    """Translate an LLM provider failure into the standard API error format.

    The provider detail is logged server-side; the client only receives the
    generic public message so upstream payloads and credentials cannot leak
    through an error response.
    """
    logger.warning("LLM provider failure on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.public_message,
                "details": [],
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register the application-wide exception handlers."""
    app.add_exception_handler(LLMProviderError, llm_provider_error_handler)
