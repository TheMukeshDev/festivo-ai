"""Festivo AI ASGI application factory."""

from dataclasses import dataclass
from datetime import timedelta
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from starlette.middleware.base import RequestResponseEndpoint

from app.api.v1.ai_planning import router as ai_planning_router
from app.api.v1.budgets import router as budgets_router
from app.api.v1.events import router as events_router
from app.api.v1.exports import router as exports_router
from app.api.v1.health import api_router, basic_router, compatibility_router
from app.api.v1.proposals import router as proposals_router
from app.api.v1.timelines import router as timelines_router
from app.api.v1.vendors import router as vendors_router
from app.core.auth import (
    FirebaseTokenVerifier,
    RejectAllTokenVerifier,
    TokenVerifier,
)
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.db.postgres import PostgresDatabase
from app.repositories.budget_repository import BudgetRepository
from app.repositories.event_repository import EventRepository, InMemoryEventRepository
from app.repositories.memory_budget_repository import InMemoryBudgetRepository
from app.repositories.memory_planning_repository import InMemoryPlanningRepository
from app.repositories.memory_proposal_repository import InMemoryProposalRepository
from app.repositories.memory_vendor_repository import InMemoryVendorRepository
from app.repositories.planning_repository import PlanningRepository
from app.repositories.postgres_budget_repository import PostgresBudgetRepository
from app.repositories.postgres_event_repository import PostgresEventRepository
from app.repositories.postgres_planning_repository import PostgresPlanningRepository
from app.repositories.postgres_proposal_repository import PostgresProposalRepository
from app.repositories.postgres_vendor_repository import PostgresVendorRepository
from app.repositories.proposal_repository import ProposalRepository
from app.repositories.vendor_repository import VendorRepository
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.planning_service import AIPlanningService
from app.services.budget_service import BudgetService
from app.services.event_service import EventService
from app.services.planning_orchestration_service import PlanningOrchestrationService
from app.services.proposal_service import ProposalService
from app.services.report_service import ReportService
from app.services.task_service import TaskService
from app.services.timeline_service import TimelineService
from app.services.vendor_service import VendorService

APP_VERSION = "0.8.0"

_CORS_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
_CORS_HEADERS = ["Accept", "Authorization", "Content-Type", "apikey", "x-client-info"]
_CORE_SERVICE_ERROR = "Custom event, budget, timeline, and task services must be provided together."


@dataclass(frozen=True)
class ServiceOverrides:
    """Optional dependency overrides, used by tests and custom wiring.

    The core bundle (event, budget, timeline, task) must be provided as a set.
    """

    event: EventService | None = None
    budget: BudgetService | None = None
    timeline: TimelineService | None = None
    task: TaskService | None = None
    vendor: VendorService | None = None
    auth_verifier: TokenVerifier | None = None
    proposal: ProposalService | None = None
    ai_planning: AIPlanningService | None = None
    orchestration: PlanningOrchestrationService | None = None
    report: ReportService | None = None

    def validate(self) -> None:
        """Reject partial core bundles before any dependency is resolved."""
        core = (self.event, self.budget, self.timeline, self.task)
        if any(service is not None for service in core) and not all(
            service is not None for service in core
        ):
            raise ValueError(_CORE_SERVICE_ERROR)


@dataclass(frozen=True)
class _Repositories:
    event: EventRepository
    budget: BudgetRepository
    planning: PlanningRepository
    vendor: VendorRepository
    proposal: ProposalRepository


@dataclass(frozen=True)
class _CoreServices:
    event_repository: EventRepository
    event: EventService
    budget: BudgetService
    timeline: TimelineService
    task: TaskService
    vendor: VendorService


@dataclass(frozen=True)
class _Dependencies:
    settings: Settings
    database: PostgresDatabase | None
    auth_verifier: TokenVerifier
    event: EventService
    budget: BudgetService
    timeline: TimelineService
    task: TaskService
    vendor: VendorService
    proposal: ProposalService
    ai_planning: AIPlanningService
    orchestration: PlanningOrchestrationService
    report: ReportService


def _resolve_auth_verifier(settings: Settings, override: TokenVerifier | None) -> TokenVerifier:
    """Use the override when given, otherwise trust a configured Firebase project."""
    if override is not None:
        return override
    if settings.firebase_auth_configured and settings.firebase_project_id:
        return FirebaseTokenVerifier(
            project_id=settings.firebase_project_id,
            client_email=settings.firebase_client_email or None,
            private_key=(
                settings.firebase_private_key.get_secret_value()
                if settings.firebase_private_key
                else None
            ),
        )
    return RejectAllTokenVerifier()


def _build_database(settings: Settings) -> PostgresDatabase | None:
    """Create the pooled Supabase database when postgres storage is enabled."""
    if settings.storage_backend != "postgres":
        return None
    if settings.supabase_db_url is None:
        raise RuntimeError("SUPABASE_DB_URL is required for the postgres backend.")
    return PostgresDatabase(
        settings.supabase_db_url,
        settings.supabase_db_connect_timeout_seconds,
    )


def _build_repositories(database: PostgresDatabase | None) -> _Repositories:
    """Pick postgres or in-memory repositories for the active storage backend."""
    if database is None:
        return _Repositories(
            event=InMemoryEventRepository(),
            budget=InMemoryBudgetRepository(),
            planning=InMemoryPlanningRepository(),
            vendor=InMemoryVendorRepository(),
            proposal=InMemoryProposalRepository(),
        )
    return _Repositories(
        event=PostgresEventRepository(database),
        budget=PostgresBudgetRepository(database),
        planning=PostgresPlanningRepository(database),
        vendor=PostgresVendorRepository(database),
        proposal=PostgresProposalRepository(database),
    )


def _build_core_services(
    settings: Settings,
    repositories: _Repositories,
    overrides: ServiceOverrides,
) -> _CoreServices:
    """Build the core service bundle from overrides or default repositories."""
    if overrides.event is None:
        event_service = EventService(repositories.event, ZoneInfo(settings.app_timezone))
        budget_service = BudgetService(repositories.event, repositories.budget)
        timeline_service = TimelineService(repositories.event, repositories.planning, event_service)
        task_service = TaskService(repositories.event, repositories.planning, event_service)
        event_repository: EventRepository = repositories.event
    else:
        if overrides.budget is None or overrides.timeline is None or overrides.task is None:
            raise ValueError(_CORE_SERVICE_ERROR)
        event_service = overrides.event
        budget_service = overrides.budget
        timeline_service = overrides.timeline
        task_service = overrides.task
        event_repository = event_service.repository
    vendor_service = overrides.vendor or VendorService(
        event_repository,
        repositories.vendor,
        event_service,
        task_service,
    )
    return _CoreServices(
        event_repository=event_repository,
        event=event_service,
        budget=budget_service,
        timeline=timeline_service,
        task=task_service,
        vendor=vendor_service,
    )


def _build_ai_planning_service(
    settings: Settings,
    core: _CoreServices,
) -> AIPlanningService:
    """Create the AI planning service, enabling Gemini only when configured."""
    provider = None
    if settings.llm_enabled and settings.llm_configuration_state == "configured":
        try:
            provider = GeminiProvider(settings)
        except Exception:
            provider = None
    return AIPlanningService(
        provider=provider,
        settings=settings,
        event_service=core.event,
        budget_service=core.budget,
        timeline_service=core.timeline,
        task_service=core.task,
        vendor_service=core.vendor,
    )


def _resolve_dependencies(settings: Settings, overrides: ServiceOverrides) -> _Dependencies:
    """Resolve every application dependency in a fixed, testable order."""
    auth_verifier = _resolve_auth_verifier(settings, overrides.auth_verifier)
    database = _build_database(settings)
    repositories = _build_repositories(database)
    core = _build_core_services(settings, repositories, overrides)

    proposal = overrides.proposal or ProposalService(
        proposal_repository=repositories.proposal,
        event_service=core.event,
        budget_service=core.budget,
        task_service=core.task,
        vendor_service=core.vendor,
        ttl=timedelta(hours=settings.proposal_ttl_hours),
    )
    ai_planning = overrides.ai_planning or _build_ai_planning_service(settings, core)
    orchestration = overrides.orchestration or PlanningOrchestrationService(proposal, ai_planning)
    report = overrides.report or ReportService(
        event_service=core.event,
        budget_service=core.budget,
        task_service=core.task,
        vendor_service=core.vendor,
        timeline_service=core.timeline,
        proposal_service=proposal,
    )

    return _Dependencies(
        settings=settings,
        database=database,
        auth_verifier=auth_verifier,
        event=core.event,
        budget=core.budget,
        timeline=core.timeline,
        task=core.task,
        vendor=core.vendor,
        proposal=proposal,
        ai_planning=ai_planning,
        orchestration=orchestration,
        report=report,
    )


def _add_docs_redirects(application: FastAPI) -> None:
    """Mirror the Swagger/OpenAPI docs under /api and the legacy //docs path."""
    redirects = (
        ("/api/docs", "/docs"),
        ("/api/openapi.json", "/openapi.json"),
        ("//docs", "/docs"),
    )
    for path, target in redirects:
        application.add_api_route(
            path,
            lambda target=target: RedirectResponse(url=target, status_code=307),
            methods=["GET"],
            include_in_schema=False,
        )


def _create_fastapi(settings: Settings) -> FastAPI:
    """Instantiate the FastAPI app with docs availability applied."""
    docs_available = settings.docs_available
    application = FastAPI(
        title=settings.app_name,
        summary="GenAI-powered celebration and event planning API.",
        version=APP_VERSION,
        debug=settings.debug,
        docs_url="/docs" if docs_available else None,
        redoc_url="/redoc" if docs_available else None,
        openapi_url="/openapi.json" if docs_available else None,
    )
    if docs_available:
        _add_docs_redirects(application)
    return application


def _attach_state(application: FastAPI, dependencies: _Dependencies) -> None:
    """Expose resolved dependencies on application.state for routes/tests."""
    application.state.settings = dependencies.settings
    application.state.database = dependencies.database
    application.state.event_service = dependencies.event
    application.state.budget_service = dependencies.budget
    application.state.timeline_service = dependencies.timeline
    application.state.task_service = dependencies.task
    application.state.vendor_service = dependencies.vendor
    application.state.proposal_service = dependencies.proposal
    application.state.ai_planning_service = dependencies.ai_planning
    application.state.planning_orchestration_service = dependencies.orchestration
    application.state.report_service = dependencies.report
    application.state.auth_verifier = dependencies.auth_verifier


def _bind_request_database(application: FastAPI, database: PostgresDatabase | None) -> None:
    """Scope one pooled connection per request when postgres storage is active."""
    if database is None:
        return

    @application.middleware("http")
    async def bind_request_database(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # One pooled connection per request: repositories reuse it instead
        # of paying a fresh Supabase round trip (hundreds of ms) each.
        with database.request_scope():
            return await call_next(request)


def _configure_cors(application: FastAPI, settings: Settings) -> None:
    """Apply the browser CORS policy for the configured frontend origins."""
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origins,
        allow_credentials=False,
        allow_methods=_CORS_METHODS,
        allow_headers=_CORS_HEADERS,
        expose_headers=[],
        max_age=600,
    )


def _include_routers(application: FastAPI, settings: Settings) -> None:
    """Register health, compatibility, and v1 feature routers."""
    application.include_router(basic_router)
    application.include_router(
        api_router,
        prefix=settings.api_v1_prefix,
        tags=["v1"],
    )
    application.include_router(compatibility_router, prefix="/api")
    for router in (
        events_router,
        budgets_router,
        timelines_router,
        vendors_router,
        ai_planning_router,
        proposals_router,
        exports_router,
    ):
        application.include_router(
            router,
            prefix=settings.api_v1_prefix,
        )


def create_app(
    settings: Settings | None = None,
    *,
    services: ServiceOverrides | None = None,
) -> FastAPI:
    """Create an application instance with explicit, secure configuration."""
    overrides = services or ServiceOverrides()
    overrides.validate()
    resolved_settings = settings or get_settings()
    dependencies = _resolve_dependencies(resolved_settings, overrides)

    application = _create_fastapi(resolved_settings)
    _attach_state(application, dependencies)
    _bind_request_database(application, dependencies.database)
    _configure_cors(application, resolved_settings)
    register_exception_handlers(application)
    _include_routers(application, resolved_settings)
    return application


app = create_app()
