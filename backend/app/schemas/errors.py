"""Stable error response schemas shared by API endpoints."""

from pydantic import BaseModel, Field


class FieldError(BaseModel):
    """A validation error associated with a request field."""

    field: str = Field(description="Dot-separated location of the invalid field.")
    message: str = Field(description="Human-readable validation message.")
    type: str = Field(description="Machine-readable validation error type.")


class ErrorDetail(BaseModel):
    """Machine-readable and human-readable error metadata."""

    code: str = Field(description="Stable machine-readable error code.")
    message: str = Field(description="Safe human-readable error message.")
    fields: list[FieldError] | None = Field(
        default=None,
        description="Field-level validation errors, when applicable.",
    )


class ErrorResponse(BaseModel):
    """Consistent error envelope returned by the API."""

    error: ErrorDetail
