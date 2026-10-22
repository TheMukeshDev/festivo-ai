"""Safe, consistent HTTP error responses."""

import logging
from collections.abc import Iterable
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.errors import ErrorDetail, ErrorResponse, FieldError

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """A domain validation failure tied to a request field."""

    field: str
    message: str
    type: str = "value_error"


class DomainValidationError(Exception):
    """Validation that depends on server state or policy."""

    def __init__(self, issues: Iterable[ValidationIssue]) -> None:
        self.issues = tuple(issues)
        super().__init__("Request validation failed.")


class ResourceNotFoundError(Exception):
    """A requested resource does not exist or its identifier is invalid."""


class ResourceConflictError(Exception):
    """A mutation conflicts with current resource state."""


class StorageUnavailableError(Exception):
    """The persistent data store cannot be reached safely."""


_HTTP_ERROR_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_error",
    429: "too_many_requests",
}

_HTTP_ERROR_MESSAGES = {
    400: "The request is invalid.",
    401: "Authentication is required.",
    403: "You are not authorized to perform this action.",
    404: "The requested resource was not found.",
    405: "The HTTP method is not allowed for this resource.",
    409: "The request conflicts with the current resource state.",
    413: "The request payload is too large.",
    415: "The request media type is not supported.",
    422: "Request validation failed.",
    429: "Too many requests.",
}


def _json_error(
    *,
    status_code: int,
    code: str,
    message: str,
    fields: list[FieldError] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(error=ErrorDetail(code=code, message=message, fields=fields))
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(exclude_none=True),
        headers=headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register handlers that prevent internals and secrets from reaching clients."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        fields = [
            FieldError(
                field=".".join(str(part) for part in error.get("loc", ())),
                message=str(error.get("msg", "Invalid value.")),
                type=str(error.get("type", "value_error")),
            )
            for error in exc.errors()
        ]
        return _json_error(
            status_code=422,
            code="validation_error",
            message="Request validation failed.",
            fields=fields,
        )

    @app.exception_handler(DomainValidationError)
    async def domain_validation_exception_handler(
        _request: Request, exc: DomainValidationError
    ) -> JSONResponse:
        fields = [
            FieldError(field=issue.field, message=issue.message, type=issue.type)
            for issue in exc.issues
        ]
        return _json_error(
            status_code=422,
            code="validation_error",
            message="Request validation failed.",
            fields=fields,
        )

    @app.exception_handler(ResourceNotFoundError)
    async def resource_not_found_exception_handler(
        _request: Request, _exc: ResourceNotFoundError
    ) -> JSONResponse:
        return _json_error(
            status_code=404,
            code="not_found",
            message="The requested resource was not found.",
        )

    @app.exception_handler(ResourceConflictError)
    async def resource_conflict_exception_handler(
        _request: Request, _exc: ResourceConflictError
    ) -> JSONResponse:
        return _json_error(
            status_code=409,
            code="conflict",
            message="The request conflicts with the current resource state.",
        )

    @app.exception_handler(StorageUnavailableError)
    async def storage_unavailable_exception_handler(
        _request: Request, _exc: StorageUnavailableError
    ) -> JSONResponse:
        return _json_error(
            status_code=503,
            code="service_unavailable",
            message="The database is temporarily unavailable.",
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = _HTTP_ERROR_CODES.get(exc.status_code, "http_error")
        message = _HTTP_ERROR_MESSAGES.get(
            exc.status_code,
            "An internal server error occurred."
            if exc.status_code >= 500
            else "The request could not be completed.",
        )
        return _json_error(
            status_code=exc.status_code,
            code=code,
            message=message,
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, _exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled exception while processing %s %s",
            request.method,
            request.url.path,
        )
        return _json_error(
            status_code=500,
            code="internal_error",
            message="An internal server error occurred.",
        )
