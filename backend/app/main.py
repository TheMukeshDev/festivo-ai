"""Festivo AI ASGI application factory."""

from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.budgets import router as budgets_router
from app.api.v1.events import router as events_router
from app.api.v1.health import api_router, basic_router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.db.postgres import PostgresDatabase
from app.repositories.event_repository import InMemoryEventRepository
from app.repositories.memory_budget_repository import InMemoryBudgetRepository
from app.repositories.postgres_budget_repository import PostgresBudgetRepository
from app.repositories.postgres_event_repository import PostgresEventRepository
from app.services.budget_service import BudgetService
from app.services.event_service import EventService

APP_VERSION = "0.3.0"

_CORS_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
_CORS_HEADERS = ["Accept", "Authorization", "Content-Type"]


def create_app(
    settings: Settings | None = None,
    event_service: EventService | None = None,
    budget_service: BudgetService | None = None,
) -> FastAPI:
    """Create an application instance with explicit, secure configuration."""
    resolved_settings = settings or get_settings()
    if (event_service is None) != (budget_service is None):
        raise ValueError("Custom event_service and budget_service must be provided together.")

    if event_service is None or budget_service is None:
        if resolved_settings.storage_backend == "postgres":
            if resolved_settings.supabase_db_url is None:
                raise RuntimeError("SUPABASE_DB_URL is required for the postgres backend.")
            database = PostgresDatabase(
                resolved_settings.supabase_db_url,
                resolved_settings.supabase_db_connect_timeout_seconds,
            )
            event_repository = PostgresEventRepository(database)
            budget_repository = PostgresBudgetRepository(database)
        else:
            event_repository = InMemoryEventRepository()
            budget_repository = InMemoryBudgetRepository()

        resolved_event_service = EventService(
            event_repository,
            ZoneInfo(resolved_settings.app_timezone),
        )
        resolved_budget_service = BudgetService(event_repository, budget_repository)
    else:
        resolved_event_service = event_service
        resolved_budget_service = budget_service

    docs_available = resolved_settings.docs_available

    application = FastAPI(
        title=resolved_settings.app_name,
        summary="GenAI-powered celebration and event planning API.",
        version=APP_VERSION,
        debug=resolved_settings.debug,
        docs_url="/docs" if docs_available else None,
        redoc_url="/redoc" if docs_available else None,
        openapi_url="/openapi.json" if docs_available else None,
    )
    application.state.settings = resolved_settings
    application.state.event_service = resolved_event_service
    application.state.budget_service = resolved_budget_service

    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.frontend_origins,
        allow_credentials=False,
        allow_methods=_CORS_METHODS,
        allow_headers=_CORS_HEADERS,
        expose_headers=[],
        max_age=600,
    )

    register_exception_handlers(application)

    application.include_router(basic_router)
    application.include_router(
        api_router,
        prefix=resolved_settings.api_v1_prefix,
        tags=["v1"],
    )
    application.include_router(
        events_router,
        prefix=resolved_settings.api_v1_prefix,
    )
    application.include_router(
        budgets_router,
        prefix=resolved_settings.api_v1_prefix,
    )
    return application


app = create_app()
