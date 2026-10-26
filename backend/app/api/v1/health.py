"""Process health and safe configuration diagnostics endpoints."""

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.core.config import Settings
from app.core.exceptions import StorageUnavailableError
from app.schemas.errors import ErrorResponse
from app.schemas.health import (
    ApiHealthResponse,
    ConfigurationStatusResponse,
    DatabaseHealthResponse,
    HealthResponse,
    LLMConfigurationStatus,
)

basic_router = APIRouter(tags=["health"])
api_router = APIRouter(tags=["health"])


@basic_router.get(
    "/",
    include_in_schema=False,
    summary="Service entry point",
)
def service_entry_point() -> dict[str, str]:
    """Point browser visitors to the health and API documentation endpoints."""
    return {
        "service": "Festivo AI",
        "health": "/health",
        "docs": "/docs",
        "api_health": "/api/v1/health",
    }


@basic_router.get(
    "/health",
    response_model=HealthResponse,
    summary="Basic process health",
    description="Returns a minimal status payload without configuration or infrastructure data.",
)
def basic_health() -> HealthResponse:
    """Report that the application process can serve requests."""
    return HealthResponse()


@api_router.get(
    "/health",
    response_model=ApiHealthResponse,
    summary="Versioned API health",
    description="Returns API version identity only. External providers are not checked.",
)
def api_health(request: Request) -> ApiHealthResponse:
    """Report API health without asserting external service availability."""
    settings: Settings = request.app.state.settings
    return ApiHealthResponse(service=settings.app_name)


@api_router.get(
    "/health/database",
    response_model=DatabaseHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Database readiness",
    description=(
        "Checks whether the configured persistence backend is reachable. "
        "Returns HTTP 503 when PostgreSQL is unavailable."
    ),
)
def database_health(request: Request, response: Response) -> DatabaseHealthResponse:
    """Report database connectivity without exposing connection details."""
    settings: Settings = request.app.state.settings
    database = request.app.state.database
    if settings.storage_backend == "memory":
        return DatabaseHealthResponse(status="ok", database="memory")

    if database is None:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return DatabaseHealthResponse(status="unavailable", database="postgres")

    try:
        database.check_connection()
    except StorageUnavailableError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return DatabaseHealthResponse(status="unavailable", database="postgres")

    return DatabaseHealthResponse(status="ok", database="postgres")


@api_router.get(
    "/config/status",
    response_model=ConfigurationStatusResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Safe configuration diagnostics",
    description=(
        "Reports configuration presence only. Provider connectivity is never implied or "
        "checked by this endpoint. Disabled by default in production."
    ),
)
def configuration_status(request: Request) -> ConfigurationStatusResponse:
    """Return non-sensitive configuration state for development or operations."""
    settings: Settings = request.app.state.settings
    if not settings.config_status_available:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested resource was not found.",
        )

    return ConfigurationStatusResponse(
        environment=settings.app_env,
        llm=LLMConfigurationStatus(
            provider=settings.llm_provider,
            enabled=settings.llm_enabled,
            model=settings.llm_model,
            credential_configured=settings.credential_configured,
            configuration_status=settings.llm_configuration_state,
            connectivity="not_checked",
        ),
    )
