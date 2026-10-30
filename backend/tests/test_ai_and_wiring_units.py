"""Unit coverage for AI plumbing, auth dependencies, health, wiring, and planning context."""

from __future__ import annotations

import json
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials

import app.main as app_main
from app.api.dependencies import get_current_user
from app.api.v1.ai_planning import handle_ai_error
from app.api.v1.health import database_health
from app.core.auth import (
    AuthenticatedUser,
    AuthenticationError,
    AuthenticationUnavailableError,
)
from app.core.config import Settings
from app.core.exceptions import StorageUnavailableError
from app.schemas.event import EventCreate
from app.services.ai.base import (
    AIAuthenticationError,
    AIConfigurationError,
    AINetworkError,
    AIOutputValidationError,
    AIProvider,
    AIProviderError,
    AIRateLimitError,
    AIServiceError,
    AITimeoutError,
)
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.planning_service import AIPlanningService
from app.services.budget_service import BudgetService
from app.services.event_service import EventService
from app.services.task_service import TaskService
from app.services.timeline_service import TimelineService
from tests.conftest import TEST_USER_ID

EventPayloadFactory = Callable[..., dict[str, Any]]
ServiceFactory = Callable[..., Settings]


class _RejectingVerifier:
    """Token verifier that always fails with a fixed error."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    def verify(self, _token: str) -> AuthenticatedUser:
        raise self._error


class _FakeModels:
    """Replays canned generate_content outcomes and records each call."""

    def __init__(self, outcomes: list[Any]) -> None:
        self._outcomes = outcomes
        self.calls: list[dict[str, Any]] = []

    def generate_content(self, *, model: str, contents: str, config: dict[str, Any]) -> Any:
        self.calls.append({"model": model, "contents": contents, "config": config})
        outcome = self._outcomes.pop(0) if len(self._outcomes) > 1 else self._outcomes[0]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class _FakeClient:
    def __init__(self, outcomes: list[Any]) -> None:
        self.models = _FakeModels(outcomes)


class _StubProvider(AIProvider):
    """Provider double returning or raising scripted results."""

    supports_response_schema = False

    def __init__(self, script: list[Any]) -> None:
        self._script = script
        self.users: list[str] = []

    def generate_structured(
        self, *, system: str, user: str, schema: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        del system, schema
        self.users.append(user)
        outcome = self._script.pop(0) if len(self._script) > 1 else self._script[0]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _text_response(payload: str) -> SimpleNamespace:
    return SimpleNamespace(text=payload, candidates=None)


def _make_provider(
    make_settings: ServiceFactory,
    monkeypatch: pytest.MonkeyPatch,
    outcomes: list[Any],
    **overrides: Any,
) -> GeminiProvider:
    values: dict[str, Any] = {
        "llm_enabled": True,
        "gemini_api_key": "unit-test-key",
        "llm_model": "gemini-unit-model",
        "llm_max_retries": 2,
    }
    values.update(overrides)
    provider = GeminiProvider(make_settings(**values))
    monkeypatch.setattr(GeminiProvider, "_backoff", staticmethod(lambda _attempt: None))
    provider._client = _FakeClient(outcomes)
    return provider


def _scope_app(state_settings: Settings | None = None, database: Any = None) -> FastAPI:
    app = FastAPI()
    if state_settings is not None:
        app.state.settings = state_settings
    app.state.database = database
    return app


# --- handle_ai_error translation -------------------------------------------------


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (AIConfigurationError("missing"), status.HTTP_503_SERVICE_UNAVAILABLE),
        (AIAuthenticationError("bad key"), status.HTTP_503_SERVICE_UNAVAILABLE),
        (AIRateLimitError("quota"), status.HTTP_429_TOO_MANY_REQUESTS),
        (AITimeoutError("slow"), status.HTTP_504_GATEWAY_TIMEOUT),
        (AINetworkError("offline"), status.HTTP_503_SERVICE_UNAVAILABLE),
        (AIServiceError("down"), status.HTTP_503_SERVICE_UNAVAILABLE),
        (AIOutputValidationError("bad json"), status.HTTP_422_UNPROCESSABLE_ENTITY),
        (AIProviderError("generic"), status.HTTP_503_SERVICE_UNAVAILABLE),
    ],
)
def test_handle_ai_error_maps_every_provider_failure(
    error: Exception, expected_status: int
) -> None:
    with pytest.raises(HTTPException) as raised:
        handle_ai_error(error)

    assert raised.value.status_code == expected_status


def test_handle_ai_error_reraises_unexpected_failures() -> None:
    with pytest.raises(ValueError, match="boom"):
        handle_ai_error(ValueError("boom"))


# --- GeminiProvider construction ------------------------------------------------


def test_provider_rejects_disabled_llm(make_settings: ServiceFactory) -> None:
    with pytest.raises(AIConfigurationError, match="disabled"):
        GeminiProvider(make_settings())


def test_provider_requires_api_key(make_settings: ServiceFactory) -> None:
    settings = make_settings(llm_enabled=True, gemini_api_key="k", llm_model="m")
    settings.gemini_api_key = None

    with pytest.raises(AIConfigurationError, match="GEMINI_API_KEY"):
        GeminiProvider(settings)


def test_provider_requires_model(make_settings: ServiceFactory) -> None:
    settings = make_settings(llm_enabled=True, gemini_api_key="k", llm_model="m")
    settings.llm_model = None

    with pytest.raises(AIConfigurationError, match="LLM_MODEL"):
        GeminiProvider(settings)


def test_provider_rejects_placeholder_model(make_settings: ServiceFactory) -> None:
    settings = make_settings(llm_enabled=True, gemini_api_key="k", llm_model="m")
    settings.llm_model = "replace_with_model_name"

    with pytest.raises(AIConfigurationError, match="LLM_MODEL"):
        GeminiProvider(settings)


def test_provider_reports_unavailable_sdk(
    make_settings: ServiceFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from google import genai

    def _boom(**_kwargs: Any) -> Any:
        raise RuntimeError("sdk missing")

    monkeypatch.setattr(genai, "Client", _boom)

    with pytest.raises(AIConfigurationError, match="SDK"):
        GeminiProvider(make_settings(llm_enabled=True, gemini_api_key="k", llm_model="m"))


# --- GeminiProvider.generate_structured -----------------------------------------


def test_generate_requires_initialized_client(
    make_settings: ServiceFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _make_provider(make_settings, monkeypatch, [_text_response("{}")])
    provider._client = None

    with pytest.raises(AIConfigurationError, match="not initialized"):
        provider.generate_structured(system="s", user="u")


def test_generate_with_schema_sets_json_mime_type(
    make_settings: ServiceFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _make_provider(make_settings, monkeypatch, [_text_response('{"summary": "ok"}')])
    schema = {"type": "object"}

    result = provider.generate_structured(system="s", user="u", schema=schema)

    assert result == {"summary": "ok"}
    config = provider._client.models.calls[0]["config"]
    assert config["response_mime_type"] == "application/json"
    assert config["response_schema"] is schema
    assert config["system_instruction"] == "s"


def test_generate_without_schema_omits_mime_type(
    make_settings: ServiceFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _make_provider(make_settings, monkeypatch, [_text_response('{"a": 1}')])

    result = provider.generate_structured(system="s", user="u")

    assert result == {"a": 1}
    assert "response_mime_type" not in provider._client.models.calls[0]["config"]


def test_generate_falls_back_to_candidate_parts(
    make_settings: ServiceFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = SimpleNamespace(
        text=None,
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[SimpleNamespace(text='{"from": '), SimpleNamespace(text='"parts"}')]
                )
            )
        ],
    )
    provider = _make_provider(make_settings, monkeypatch, [response])

    assert provider.generate_structured(system="s", user="u") == {"from": "parts"}


@pytest.mark.parametrize(
    "bad_response",
    [
        SimpleNamespace(text=None, candidates=None),
        _text_response("not-json"),
        _text_response("[1, 2, 3]"),
    ],
    ids=["empty", "malformed", "not-an-object"],
)
def test_generate_rejects_unusable_responses(
    make_settings: ServiceFactory,
    monkeypatch: pytest.MonkeyPatch,
    bad_response: SimpleNamespace,
) -> None:
    provider = _make_provider(make_settings, monkeypatch, [bad_response])

    with pytest.raises(AIOutputValidationError):
        provider.generate_structured(system="s", user="u")

    # retries = 2 means three attempts before the final failure.
    assert len(provider._client.models.calls) == 3


def test_generate_retries_timeout_then_succeeds(
    make_settings: ServiceFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _make_provider(
        make_settings,
        monkeypatch,
        [TimeoutError("read timeout"), _text_response('{"summary": "second try"}')],
    )

    result = provider.generate_structured(system="s", user="u")

    assert result == {"summary": "second try"}
    assert len(provider._client.models.calls) == 2


@pytest.mark.parametrize(
    ("failure", "expected_type"),
    [
        (Exception("rate limit exceeded"), AIRateLimitError),
        (Exception("invalid api key supplied"), AIAuthenticationError),
    ],
    ids=["rate-limit", "auth"],
)
def test_generate_raises_fatal_errors_without_retrying(
    make_settings: ServiceFactory,
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
    expected_type: type[Exception],
) -> None:
    provider = _make_provider(make_settings, monkeypatch, [failure])

    with pytest.raises(expected_type):
        provider.generate_structured(system="s", user="u")

    assert len(provider._client.models.calls) == 1


@pytest.mark.parametrize(
    ("failure", "expected_type"),
    [
        (Exception("gateway timeout waiting"), AITimeoutError),
        (Exception("connection reset by peer"), AINetworkError),
        (Exception("upstream exploded"), AIServiceError),
    ],
    ids=["timeout", "network", "generic"],
)
def test_generate_classifies_failures_after_exhausting_retries(
    make_settings: ServiceFactory,
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
    expected_type: type[Exception],
) -> None:
    provider = _make_provider(make_settings, monkeypatch, [failure], llm_max_retries=0)

    with pytest.raises(expected_type):
        provider.generate_structured(system="s", user="u")


def test_generate_reraises_typed_provider_errors_without_retrying(
    make_settings: ServiceFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _make_provider(make_settings, monkeypatch, [AIRateLimitError("quota")])

    with pytest.raises(AIRateLimitError, match="quota"):
        provider.generate_structured(system="s", user="u")

    assert len(provider._client.models.calls) == 1


def test_backoff_sleeps_with_exponential_growth(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.ai.gemini_provider as gemini_module

    naps: list[float] = []
    monkeypatch.setattr(gemini_module.time, "sleep", naps.append)

    GeminiProvider._backoff(0)
    GeminiProvider._backoff(3)

    assert naps == [0.1, 0.8]


# --- get_current_user dependency -------------------------------------------------


def _auth_request(app: FastAPI) -> Request:
    return Request({"type": "http", "app": app, "headers": [], "method": "GET", "path": "/"})


def _credentials(scheme: str = "Bearer") -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme=scheme, credentials="token")


def test_authentication_errors_become_401() -> None:
    app = FastAPI()
    app.state.auth_verifier = _RejectingVerifier(AuthenticationError("expired"))

    with pytest.raises(HTTPException) as raised:
        get_current_user(_auth_request(app), _credentials())

    assert raised.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_authentication_outage_propagates_for_the_503_handler() -> None:
    app = FastAPI()
    app.state.auth_verifier = _RejectingVerifier(AuthenticationUnavailableError("keys down"))

    with pytest.raises(AuthenticationUnavailableError):
        get_current_user(_auth_request(app), _credentials())


class _StubVerifier:
    def verify(self, _token: str) -> AuthenticatedUser:
        return AuthenticatedUser(user_id=TEST_USER_ID)


def test_valid_token_resolves_the_user() -> None:
    app = FastAPI()
    app.state.auth_verifier = _StubVerifier()

    user = get_current_user(_auth_request(app), _credentials())

    assert user.user_id == TEST_USER_ID


def test_auth_outage_returns_safe_503_response(client: Any) -> None:
    app = client.app  # type: ignore[attr-defined]
    app.state.auth_verifier = _RejectingVerifier(AuthenticationUnavailableError("keys down"))

    response = client.get("/api/v1/events")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["error"]["code"] == "service_unavailable"


# --- health database readiness ---------------------------------------------------


def test_database_health_reports_memory_backend(make_settings: ServiceFactory) -> None:
    app = _scope_app(make_settings())
    response = Response()

    result = database_health(_auth_request(app), response)

    assert result.status == "ok"
    assert response.status_code == status.HTTP_200_OK


def test_database_health_reports_missing_postgres_connection(make_settings: ServiceFactory) -> None:
    settings = make_settings(storage_backend="postgres", supabase_db_url="postgresql://x/y")
    app = _scope_app(settings, database=None)
    response = Response()

    result = database_health(_auth_request(app), response)

    assert result.status == "unavailable"
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


def test_database_health_reports_unreachable_postgres(make_settings: ServiceFactory) -> None:
    settings = make_settings(storage_backend="postgres", supabase_db_url="postgresql://x/y")

    class _DownDatabase:
        def check_connection(self) -> None:
            raise StorageUnavailableError("offline")

    app = _scope_app(settings, database=_DownDatabase())
    response = Response()

    result = database_health(_auth_request(app), response)

    assert result.status == "unavailable"
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


def test_database_health_reports_reachable_postgres(make_settings: ServiceFactory) -> None:
    settings = make_settings(storage_backend="postgres", supabase_db_url="postgresql://x/y")

    class _UpDatabase:
        def check_connection(self) -> None:
            return None

    app = _scope_app(settings, database=_UpDatabase())
    response = Response()

    result = database_health(_auth_request(app), response)

    assert result.status == "ok"
    assert response.status_code == status.HTTP_200_OK


# --- application wiring guards ---------------------------------------------------


def test_partial_core_service_bundle_is_rejected(event_service: EventService) -> None:
    overrides = app_main.ServiceOverrides(event=event_service)

    with pytest.raises(ValueError, match="must be provided together"):
        overrides.validate()


def test_core_builder_requires_the_full_override_bundle(event_service: EventService) -> None:
    overrides = app_main.ServiceOverrides(event=event_service)
    settings = Settings.model_construct(_env_file=None, app_env="test")

    with pytest.raises(ValueError, match="must be provided together"):
        app_main._build_core_services(
            settings,
            app_main._build_repositories(None),
            overrides,
        )


def test_postgres_backend_requires_a_connection_string() -> None:
    settings = Settings.model_construct(storage_backend="postgres", supabase_db_url=None)

    with pytest.raises(RuntimeError, match="SUPABASE_DB_URL"):
        app_main._build_database(settings)


def test_ai_planning_survives_provider_construction_failure(
    make_settings: ServiceFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(_settings: Settings) -> Any:
        raise AIConfigurationError("sdk unavailable")

    monkeypatch.setattr("app.main.GeminiProvider", _boom)
    core = app_main._build_core_services(
        make_settings(),
        app_main._build_repositories(None),
        app_main.ServiceOverrides(),
    )
    service = app_main._build_ai_planning_service(
        make_settings(llm_enabled=True, gemini_api_key="k", llm_model="m"),
        core,
    )

    with pytest.raises(AIProviderError):
        service.generate_plan(TEST_USER_ID, "11111111-1111-1111-1111-111111111111", None)


# --- AI planning service branches ------------------------------------------------


@pytest.fixture
def ai_service(
    make_settings: ServiceFactory,
    event_service: EventService,
    budget_service: BudgetService,
    timeline_service: TimelineService,
    task_service: TaskService,
) -> AIPlanningService:
    return AIPlanningService(
        provider=None,
        settings=make_settings(llm_model="unit-model"),
        event_service=event_service,
        budget_service=budget_service,
        timeline_service=timeline_service,
        task_service=task_service,
    )


def _create_event(
    event_service: EventService,
    event_payload: EventPayloadFactory,
    **overrides: Any,
) -> UUID:
    event = event_service.create(TEST_USER_ID, EventCreate(**event_payload(**overrides)))
    return event.event_id


def test_build_context_includes_generated_timeline(
    ai_service: AIPlanningService,
    event_service: EventService,
    timeline_service: TimelineService,
    event_payload: EventPayloadFactory,
) -> None:
    event_id = _create_event(event_service, event_payload)
    timeline, _tasks = timeline_service.generate(TEST_USER_ID, str(event_id))

    context = ai_service.build_context(TEST_USER_ID, str(event_id))

    assert context["timeline"] == {
        "start_date": timeline.start_date.isoformat(),
        "end_date": timeline.end_date.isoformat(),
    }


def test_build_context_records_user_preferences(
    ai_service: AIPlanningService,
    event_service: EventService,
    event_payload: EventPayloadFactory,
) -> None:
    event_id = _create_event(event_service, event_payload)

    context = ai_service.build_context(TEST_USER_ID, str(event_id), {"style": "minimal"})

    assert context["user_preferences"] == {"style": "minimal"}


def test_generate_plan_without_provider_is_rejected(ai_service: AIPlanningService) -> None:
    with pytest.raises(AIProviderError, match="not configured"):
        ai_service.generate_plan(TEST_USER_ID, "11111111-1111-1111-1111-111111111111", None)


def test_generate_plan_repairs_invalid_provider_output(
    make_settings: ServiceFactory,
    event_service: EventService,
    budget_service: BudgetService,
    timeline_service: TimelineService,
    task_service: TaskService,
    event_payload: EventPayloadFactory,
) -> None:
    provider = _StubProvider(
        [AIOutputValidationError("bad json"), {"summary": "Recovered on retry."}]
    )
    service = AIPlanningService(
        provider=provider,
        settings=make_settings(llm_model="unit-model"),
        event_service=event_service,
        budget_service=budget_service,
        timeline_service=timeline_service,
        task_service=task_service,
    )
    event_id = _create_event(event_service, event_payload)

    plan = service.generate_plan(TEST_USER_ID, str(event_id))

    assert plan.summary == "Recovered on retry."
    assert len(provider.users) == 2
    assert provider.users[1].endswith("No markdown.")


def test_generate_plan_rejects_non_object_provider_output(
    make_settings: ServiceFactory,
    event_service: EventService,
    budget_service: BudgetService,
    timeline_service: TimelineService,
    task_service: TaskService,
    event_payload: EventPayloadFactory,
) -> None:
    provider = _StubProvider([["not", "an", "object"]])
    service = AIPlanningService(
        provider=provider,
        settings=make_settings(llm_model="unit-model"),
        event_service=event_service,
        budget_service=budget_service,
        timeline_service=timeline_service,
        task_service=task_service,
    )
    event_id = _create_event(event_service, event_payload)

    with pytest.raises(AIOutputValidationError, match="not a JSON object"):
        service.generate_plan(TEST_USER_ID, str(event_id))


def test_generate_plan_rejects_schema_violations(
    make_settings: ServiceFactory,
    event_service: EventService,
    budget_service: BudgetService,
    timeline_service: TimelineService,
    task_service: TaskService,
    event_payload: EventPayloadFactory,
) -> None:
    provider = _StubProvider([{"summary": ""}])
    service = AIPlanningService(
        provider=provider,
        settings=make_settings(llm_model="unit-model"),
        event_service=event_service,
        budget_service=budget_service,
        timeline_service=timeline_service,
        task_service=task_service,
    )
    event_id = _create_event(event_service, event_payload)

    with pytest.raises(AIOutputValidationError, match="could not be validated"):
        service.generate_plan(TEST_USER_ID, str(event_id))


def test_refine_plan_forwards_notes_into_the_prompt(
    make_settings: ServiceFactory,
    event_service: EventService,
    budget_service: BudgetService,
    timeline_service: TimelineService,
    task_service: TaskService,
    event_payload: EventPayloadFactory,
) -> None:
    provider = _StubProvider([{"summary": "Refined plan."}])
    service = AIPlanningService(
        provider=provider,
        settings=make_settings(llm_model="unit-model"),
        event_service=event_service,
        budget_service=budget_service,
        timeline_service=timeline_service,
        task_service=task_service,
    )
    event_id = _create_event(event_service, event_payload)

    plan = service.refine_plan(
        TEST_USER_ID,
        str(event_id),
        {"style": "minimal"},
        additional_notes="Keep the guest list under 80.",
    )

    assert plan.summary == "Refined plan."
    assert "Keep the guest list under 80." in provider.users[0]
    assert json.dumps({"style": "minimal"})[1:-1] in provider.users[0]
