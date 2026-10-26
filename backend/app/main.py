"""Festivo AI ASGI application factory."""

from datetime import timedelta
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.v1.ai_planning import router as ai_planning_router
from app.api.v1.budgets import router as budgets_router
from app.api.v1.events import router as events_router
from app.api.v1.exports import router as exports_router
from app.api.v1.health import api_router, basic_router
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
from app.repositories.event_repository import InMemoryEventRepository
from app.repositories.memory_budget_repository import InMemoryBudgetRepository
from app.repositories.memory_planning_repository import InMemoryPlanningRepository
from app.repositories.memory_proposal_repository import InMemoryProposalRepository
from app.repositories.memory_vendor_repository import InMemoryVendorRepository
from app.repositories.postgres_budget_repository import PostgresBudgetRepository
from app.repositories.postgres_event_repository import PostgresEventRepository
from app.repositories.postgres_planning_repository import PostgresPlanningRepository
from app.repositories.postgres_proposal_repository import PostgresProposalRepository
from app.repositories.postgres_vendor_repository import PostgresVendorRepository
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


def create_app(
    settings: Settings | None = None,
    event_service: EventService | None = None,
    budget_service: BudgetService | None = None,
    timeline_service: TimelineService | None = None,
    task_service: TaskService | None = None,
    vendor_service: VendorService | None = None,
    auth_verifier: TokenVerifier | None = None,
    proposal_service: ProposalService | None = None,
    ai_planning_service: AIPlanningService | None = None,
    orchestration_service: PlanningOrchestrationService | None = None,
    report_service: ReportService | None = None,
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
        if (
            resolved_settings.firebase_auth_configured
            and resolved_settings.firebase_project_id
        ):
            resolved_auth_verifier = FirebaseTokenVerifier(
                project_id=resolved_settings.firebase_project_id,
                client_email=(
                    resolved_settings.firebase_client_email
                    if resolved_settings.firebase_client_email
                    else None
                ),
                private_key=(
                    resolved_settings.firebase_private_key.get_secret_value()
                    if resolved_settings.firebase_private_key
                    else None
                ),
            )
        else:
            resolved_auth_verifier = RejectAllTokenVerifier()
    else:
        resolved_auth_verifier = auth_verifier

    database: PostgresDatabase | None = None
    if resolved_settings.storage_backend == "postgres":
        if resolved_settings.supabase_db_url is None:
            raise RuntimeError("SUPABASE_DB_URL is required for the postgres backend.")
        database = PostgresDatabase(
            resolved_settings.supabase_db_url,
            resolved_settings.supabase_db_connect_timeout_seconds,
        )

    if event_service is None:
        if database is not None:
            event_repository = PostgresEventRepository(database)
            budget_repository = PostgresBudgetRepository(database)
            planning_repository = PostgresPlanningRepository(database)
            vendor_repository = PostgresVendorRepository(database)
            proposal_repository = PostgresProposalRepository(database)
        else:
            event_repository = InMemoryEventRepository()
            budget_repository = InMemoryBudgetRepository()
            planning_repository = InMemoryPlanningRepository()
            vendor_repository = InMemoryVendorRepository()
            proposal_repository = InMemoryProposalRepository()

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
        resolved_vendor_service = vendor_service or VendorService(
            event_repository,
            vendor_repository,
            resolved_event_service,
            resolved_task_service,
        )
    else:
        if budget_service is None or timeline_service is None or task_service is None:
            raise ValueError(
                "Custom event, budget, timeline, and task services must be provided together."
            )
        resolved_event_service = event_service
        resolved_budget_service = budget_service
        resolved_timeline_service = timeline_service
        resolved_task_service = task_service
        if database is not None:
            proposal_repository = PostgresProposalRepository(database)
            vendor_repository = PostgresVendorRepository(database)
        else:
            proposal_repository = InMemoryProposalRepository()
            vendor_repository = InMemoryVendorRepository()
        event_repository = resolved_event_service._repository
        resolved_vendor_service = vendor_service or VendorService(
            event_repository,
            vendor_repository,
            resolved_event_service,
            resolved_task_service,
        )

    if proposal_service is None:
        resolved_proposal_service = ProposalService(
            proposal_repository,
            resolved_event_service,
            resolved_budget_service,
            resolved_task_service,
            resolved_vendor_service,
            ttl=timedelta(hours=resolved_settings.proposal_ttl_hours),
        )
    else:
        resolved_proposal_service = proposal_service

    if ai_planning_service is None:
        provider = None
        if resolved_settings.llm_enabled and resolved_settings.llm_configuration_state == "configured":
            try:
                provider = GeminiProvider(resolved_settings)
            except Exception:
                provider = None
        resolved_ai_planning_service = AIPlanningService(
            provider=provider,
            settings=resolved_settings,
            event_service=resolved_event_service,
            budget_service=resolved_budget_service,
            timeline_service=resolved_timeline_service,
            task_service=resolved_task_service,
            vendor_service=resolved_vendor_service,
        )
    else:
        resolved_ai_planning_service = ai_planning_service

    resolved_orchestration_service = orchestration_service or PlanningOrchestrationService(
        resolved_proposal_service,
        resolved_ai_planning_service,
    )
    resolved_report_service = report_service or ReportService(
        resolved_event_service,
        resolved_budget_service,
        resolved_task_service,
        resolved_vendor_service,
        resolved_timeline_service,
        resolved_proposal_service,
    )

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
    if docs_available:
        application.add_api_route(
            "/api/docs",
            lambda: RedirectResponse(url="/docs", status_code=307),
            methods=["GET"],
            include_in_schema=False,
        )
        application.add_api_route(
            "/api/openapi.json",
            lambda: RedirectResponse(url="/openapi.json", status_code=307),
            methods=["GET"],
            include_in_schema=False,
        )
        application.add_api_route(
            "//docs",
            lambda: RedirectResponse(url="/docs", status_code=307),
            methods=["GET"],
            include_in_schema=False,
        )
    application.state.settings = resolved_settings
    application.state.event_service = resolved_event_service
    application.state.budget_service = resolved_budget_service
    application.state.timeline_service = resolved_timeline_service
    application.state.task_service = resolved_task_service
    application.state.vendor_service = resolved_vendor_service
    application.state.proposal_service = resolved_proposal_service
    application.state.ai_planning_service = resolved_ai_planning_service
    application.state.planning_orchestration_service = resolved_orchestration_service
    application.state.report_service = resolved_report_service
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
            prefix=resolved_settings.api_v1_prefix,
        )
    return application


app = create_app()
