"""Shared isolated test configuration and clients."""

from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.repositories.event_repository import InMemoryEventRepository
from app.repositories.memory_budget_repository import InMemoryBudgetRepository
from app.services.budget_service import BudgetService
from app.services.event_service import EventService

SENSITIVE_TEST_KEY = "test-only-gemini-credential-9f3a7c1d"
TEST_DATABASE_URL = "postgresql://festivo:test-password@localhost:5432/festivo_test"
FIXED_NOW = datetime(2030, 5, 15, 8, 0, tzinfo=UTC)
FIXED_EVENT_DATE = date(2030, 6, 15)
TEST_TIMEZONE = "Asia/Kolkata"

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
    "DEBUG",
    "DOCS_ENABLED",
    "CONFIG_STATUS_ENABLED",
)


class MutableClock:
    """Deterministic, adjustable event clock for tests."""

    def __init__(self, now: datetime = FIXED_NOW) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


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
def event_service(
    clock: MutableClock,
    event_repository: InMemoryEventRepository,
) -> EventService:
    """Event service backed by isolated storage and a deterministic clock."""
    return EventService(
        event_repository,
        ZoneInfo(TEST_TIMEZONE),
        clock,
    )


@pytest.fixture
def budget_service(
    clock: MutableClock,
    event_repository: InMemoryEventRepository,
) -> BudgetService:
    """Budget service sharing the isolated event store and deterministic clock."""
    return BudgetService(
        event_repository,
        InMemoryBudgetRepository(),
        clock,
    )


@pytest.fixture
def event_payload() -> Callable[..., dict[str, Any]]:
    """Build valid event request payloads with optional overrides."""

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
def app(
    make_settings: Callable[..., Settings],
    event_service: EventService,
    budget_service: BudgetService,
) -> FastAPI:
    """Application instance using isolated test settings and storage."""
    return create_app(make_settings(), event_service, budget_service)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """Synchronous HTTP client for API tests."""
    with TestClient(app) as test_client:
        yield test_client
