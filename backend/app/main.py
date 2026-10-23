"""Festivo AI ASGI application factory."""

from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.budgets import router as budgets_router
from app.api.v1.events import router as events_router
from app.api.v1.health import api_router, basic_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.timelines import router as timelines_router
from app.core.auth import (
    RejectAllTokenVerifier,
    SupabaseTokenVerifier,
    TokenVerifier,
)
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.db.postgres import PostgresDatabase
from app.repositories.event_repository import InMemoryEventRepository
from app.repositories.memory_budget_repository import InMemoryBudgetRepository
from app.repositories.memory_planning_repository import InMemoryPlanningRepository
from app.repositories.postgres_budget_repository import PostgresBudgetRepository
from app.repositories.postgres_event_repository import PostgresEventRepository
from app.repositories.postgres_planning_repository import PostgresPlanningRepository
from app.services.budget_service import BudgetService
from app.services.event_service import EventService
from app.services.task_service import TaskService
from app.services.timeline_service import TimelineService

APP_VERSION = "0.5.0"

_CORS_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
_CORS_HEADERS = ["Accept", "Authorization", "Content-Type"]


def create_app(
    settings: Settings | None = None,
    event_service: EventService | None = None,
    budget_service: BudgetService | None = None,
    timeline_service: TimelineService | None = None,
    task_service: TaskService | None = None,
    auth_verifier: TokenVerifier | None = None,
) -> FastAPI:
    """Create an application instance with explicit, secure configuration."""
    resolved_settings = settings or get_settings()
    custom_services = (event_service, budget_service, timeline_service, task_service)
    if any(service is not None for service in custom_services) and not all(
        service is not None for service in custom_services
    ):
        raise ValueError(
            "Custom event, budget, timeline, and task services must be provided together."
        )

    if auth_verifier is None:
        if resolved_settings.auth_configured:
            assert resolved_settings.resolved_jwks_url is not None
            assert resolved_settings.resolved_jwt_issuer is not None
            resolved_auth_verifier: TokenVerifier = SupabaseTokenVerifier(
                jwks_url=resolved_settings.resolved_jwks_url,
                issuer=resolved_settings.resolved_jwt_issuer,
                audience=resolved_settings.supabase_jwt_audience,
                leeway_seconds=resolved_settings.supabase_jwt_leeway_seconds,
            )
        else:
            resolved_auth_verifier = RejectAllTokenVerifier()
    else:
        resolved_auth_verifier = auth_verifier

    if event_service is None:
        if resolved_settings.storage_backend == "postgres":
            if resolved_settings.supabase_db_url is None:
                raise RuntimeError("SUPABASE_DB_URL is required for the postgres backend.")
            database = PostgresDatabase(
                resolved_settings.supabase_db_url,
                resolved_settings.supabase_db_connect_timeout_seconds,
            )
            event_repository = PostgresEventRepository(database)
            budget_repository = PostgresBudgetRepository(database)
            planning_repository = PostgresPlanningRepository(database)
        else:
            event_repository = InMemoryEventRepository()
            budget_repository = InMemoryBudgetRepository()
            planning_repository = InMemoryPlanningRepository()

        resolved_event_service = EventService(
            event_repository,
            ZoneInfo(resolved_settings.app_timezone),
        )
        resolved_budget_service = BudgetService(event_repository, budget_repository)
        resolved_timeline_service = TimelineService(
            event_repository,
            planning_repository,
            resolved_event_service,
        )
        resolved_task_service = TaskService(
            event_repository,
            planning_repository,
            resolved_event_service,
        )
    else:
        assert budget_service is not None
        assert timeline_service is not None
        assert task_service is not None
        resolved_event_service = event_service
        resolved_budget_service = budget_service
        resolved_timeline_service = timeline_service
        resolved_task_service = task_service

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
    application.state.timeline_service = resolved_timeline_service
    application.state.task_service = resolved_task_service
    application.state.auth_verifier = resolved_auth_verifier

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
    application.include_router(
        timelines_router,
        prefix=resolved_settings.api_v1_prefix,
    )
    application.include_router(
        tasks_router,
        prefix=resolved_settings.api_v1_prefix,
    )
    return application


app = create_app()
