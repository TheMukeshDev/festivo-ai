"""Shared isolated test configuration and clients."""

from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth import AuthenticatedUser, TokenVerifier
from app.core.config import Settings
from app.main import create_app
from app.repositories.event_repository import InMemoryEventRepository
from app.repositories.memory_budget_repository import InMemoryBudgetRepository
from app.repositories.memory_planning_repository import InMemoryPlanningRepository
from app.services.budget_service import BudgetService
from app.services.event_service import EventService
from app.services.task_service import TaskService
from app.services.timeline_service import TimelineService

SENSITIVE_TEST_KEY = "test-only-gemini-credential-9f3a7c1d"
TEST_DATABASE_URL = "postgresql://festivo:test-password@localhost:5432/festivo_test"
FIXED_NOW = datetime(2030, 5, 15, 8, 0, tzinfo=UTC)
FIXED_EVENT_DATE = date(2030, 6, 15)
TEST_TIMEZONE = "Asia/Kolkata"
TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

_ENV_KEYS = (
    "APP_NAME",
    "APP_ENV",
    "API_V1_PREFIX",
    "APP_TIMEZONE",
    "STORAGE_BACKEND",
    "SUPABASE_DB_URL",
    "SUPABASE_DB_CONNECT_TIMEOUT_SECONDS",
    "FRONTEND_ORIGIN",
    "FRONTEND_ORIGINS",
    "LLM_PROVIDER",
    "LLM_MODEL",
    "GEMINI_API_KEY",
    "LLM_ENABLED",
    "LLM_TIMEOUT_SECONDS",
    "LLM_MAX_RETRIES",
    "LLM_MAX_OUTPUT_TOKENS",
    "LLM_TEMPERATURE",
    "PROPOSAL_TTL_HOURS",
    "DEBUG",
    "DOCS_ENABLED",
    "CONFIG_STATUS_ENABLED",
    "SUPABASE_URL",
    "SUPABASE_JWKS_URL",
    "SUPABASE_JWT_ISSUER",
    "SUPABASE_JWT_AUDIENCE",
    "FIREBASE_PROJECT_ID",
    "FIREBASE_CLIENT_EMAIL",
    "FIREBASE_PRIVATE_KEY",
)


class MutableClock:
    """Deterministic, adjustable event clock for tests."""

    def __init__(self, now: datetime = FIXED_NOW) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


class PermissiveTokenVerifier:
    def __init__(self, user_id: UUID = TEST_USER_ID) -> None:
        self.user_id = user_id

    def verify(self, token: str) -> AuthenticatedUser:
        return AuthenticatedUser(user_id=self.user_id)


@pytest.fixture(autouse=True)
def isolate_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent real environment variables from affecting deterministic tests."""
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def make_settings() -> Callable[..., Settings]:
    """Build isolated settings that never read the developer's `.env` file."""

    def factory(**overrides: Any) -> Settings:
        values: dict[str, Any] = {
            "_env_file": None,
            "app_env": "test",
            "frontend_origins": ["http://localhost:5173"],
        }
        values.update(overrides)
        if values.get("app_env") == "production":
            values.setdefault("firebase_project_id", "test-project")
            values.setdefault(
                "firebase_client_email", "firebase-adminsdk@test-project.iam.gserviceaccount.com"
            )
            values.setdefault("firebase_private_key", "test-private-key")
        return Settings(**values)

    return factory


@pytest.fixture
def clock() -> MutableClock:
    """Fixture clock fixed well in the future so date policies stay deterministic."""
    return MutableClock()


@pytest.fixture
def event_repository() -> InMemoryEventRepository:
    """Isolated event store shared by event and budget services."""
    return InMemoryEventRepository()


@pytest.fixture
def planning_repository() -> InMemoryPlanningRepository:
    return InMemoryPlanningRepository()


@pytest.fixture
def event_service(
    clock: MutableClock,
    event_repository: InMemoryEventRepository,
) -> EventService:
    return EventService(event_repository, ZoneInfo(TEST_TIMEZONE), clock)


@pytest.fixture
def budget_service(
    clock: MutableClock,
    event_repository: InMemoryEventRepository,
) -> BudgetService:
    return BudgetService(event_repository, InMemoryBudgetRepository(), clock)


@pytest.fixture
def timeline_service(
    event_repository: InMemoryEventRepository,
    planning_repository: InMemoryPlanningRepository,
    event_service: EventService,
    clock: MutableClock,
) -> TimelineService:
    return TimelineService(event_repository, planning_repository, event_service, clock)


@pytest.fixture
def task_service(
    event_repository: InMemoryEventRepository,
    planning_repository: InMemoryPlanningRepository,
    event_service: EventService,
    clock: MutableClock,
) -> TaskService:
    return TaskService(event_repository, planning_repository, event_service, clock)


@pytest.fixture
def event_payload() -> Callable[..., dict[str, Any]]:
    def factory(**overrides: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": "Ananya and Rohan Wedding",
            "event_type": "wedding",
            "event_date": FIXED_EVENT_DATE.isoformat(),
            "location": "Bengaluru",
            "guest_count": 150,
            "budget_amount": "750000.00",
            "currency": "INR",
            "description": "A relaxed celebration with family and friends.",
            "preferences": ["Pastel decor", "Vegetarian menu"],
            "constraints": ["No loud music after 10 PM"],
        }
        payload.update(overrides)
        return payload

    return factory


@pytest.fixture
def auth_verifier() -> TokenVerifier:
    return PermissiveTokenVerifier()


@pytest.fixture
def app(
    make_settings: Callable[..., Settings],
    event_service: EventService,
    budget_service: BudgetService,
    timeline_service: TimelineService,
    task_service: TaskService,
    auth_verifier: TokenVerifier,
) -> FastAPI:
    return create_app(
        make_settings(),
        event_service,
        budget_service,
        timeline_service,
        task_service,
        auth_verifier=auth_verifier,
    )


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        test_client.headers.update({"Authorization": "Bearer test-token"})
        yield test_client
