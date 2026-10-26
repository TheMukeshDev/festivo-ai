"""Security-focused tests for secrets, CORS, logs, and production errors."""

import json
import logging
from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app
from tests.conftest import SENSITIVE_TEST_KEY, TEST_DATABASE_URL


def test_configured_cors_origin_is_allowed_without_credentials(
    make_settings: Callable[..., Settings],
) -> None:
    settings = make_settings(frontend_origins=["https://festivo.example"])

    with TestClient(create_app(settings)) as test_client:
        response = test_client.get(
            "/api/v1/health",
            headers={"Origin": "https://festivo.example"},
        )
        preflight = test_client.options(
            "/api/v1/health",
            headers={
                "Origin": "https://festivo.example",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.headers["access-control-allow-origin"] == "https://festivo.example"
    assert "access-control-allow-credentials" not in response.headers
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "https://festivo.example"
    assert "GET" in preflight.headers["access-control-allow-methods"]
    assert "access-control-allow-credentials" not in preflight.headers


def test_authenticated_preflight_allows_frontend_origin(
    make_settings: Callable[..., Settings],
) -> None:
    settings = make_settings(frontend_origins=["https://festivoai01.vercel.app"])

    with TestClient(create_app(settings)) as test_client:
        preflight = test_client.options(
            "/api/v1/events",
            headers={
                "Origin": "https://festivoai01.vercel.app",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )

    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "https://festivoai01.vercel.app"
    assert "authorization" in preflight.headers["access-control-allow-headers"].lower()
    assert "content-type" in preflight.headers["access-control-allow-headers"].lower()


def test_unconfigured_cors_origin_is_not_authorized(make_settings: Callable[..., Settings]) -> None:
    settings = make_settings(frontend_origins=["https://festivo.example"])

    with TestClient(create_app(settings)) as test_client:
        response = test_client.get(
            "/api/v1/health",
            headers={"Origin": "https://attacker.example"},
        )
        preflight = test_client.options(
            "/api/v1/health",
            headers={
                "Origin": "https://attacker.example",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert "access-control-allow-origin" not in response.headers
    assert "access-control-allow-origin" not in preflight.headers
    assert preflight.status_code != 200


def test_wildcard_origins_are_rejected(make_settings: Callable[..., Settings]) -> None:
    with pytest.raises(ValidationError, match="Wildcard CORS origins"):
        make_settings(frontend_origins=["*"])


def test_configured_secret_is_masked_in_settings_representation(
    make_settings: Callable[..., Settings],
) -> None:
    settings = make_settings(
        llm_enabled=True,
        gemini_api_key=SENSITIVE_TEST_KEY,
        llm_model="test-gemini-model",
    )

    assert SENSITIVE_TEST_KEY not in repr(settings)
    assert SENSITIVE_TEST_KEY not in str(settings)


def test_configured_secret_is_never_returned(
    make_settings: Callable[..., Settings],
) -> None:
    settings = make_settings(
        llm_enabled=True,
        gemini_api_key=SENSITIVE_TEST_KEY,
        llm_model="test-gemini-model",
    )

    with TestClient(create_app(settings)) as test_client:
        responses = [
            test_client.get("/health"),
            test_client.get("/api/v1/health"),
            test_client.get("/api/v1/config/status"),
            test_client.get("/openapi.json"),
        ]

    for response in responses:
        assert response.status_code == 200
        assert SENSITIVE_TEST_KEY not in response.text
        assert SENSITIVE_TEST_KEY not in json.dumps(dict(response.headers))


def test_configuration_diagnostics_do_not_dump_environment(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/config/status")

    payload = response.json()
    assert set(payload) == {"environment", "llm"}
    assert set(payload["llm"]) == {
        "provider",
        "enabled",
        "model",
        "credential_configured",
        "configuration_status",
        "connectivity",
    }
    assert "key" not in json.dumps(payload).lower()
    assert "secret" not in json.dumps(payload).lower()


def test_sensitive_values_are_not_logged_on_unhandled_errors(
    app: FastAPI,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.ERROR)

    def explode() -> None:
        raise RuntimeError(f"provider failed with credential {SENSITIVE_TEST_KEY}")

    app.add_api_route("/test/log-error", explode, methods=["GET"], include_in_schema=False)

    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.get("/test/log-error")

    assert response.status_code == 500
    assert SENSITIVE_TEST_KEY not in caplog.text
    assert "test/log-error" in caplog.text


def test_production_errors_do_not_expose_stack_traces_or_paths(
    make_settings: Callable[..., Settings],
) -> None:
    settings = make_settings(
        app_env="production",
        storage_backend="postgres",
        supabase_db_url=TEST_DATABASE_URL,
    )
    application = create_app(settings)
    filesystem_path = "C:\\Users\\private\\festivo\\keys.txt"

    def explode() -> None:
        raise RuntimeError(f"broken at {filesystem_path}")

    application.add_api_route(
        "/test/production-error",
        explode,
        methods=["GET"],
        include_in_schema=False,
    )

    with TestClient(application, raise_server_exceptions=False) as test_client:
        response = test_client.get("/test/production-error")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert filesystem_path not in response.text
    assert "C:\\Users" not in response.text
    assert "C:/Users" not in response.text
    assert "Traceback" not in response.text
    assert "RuntimeError" not in response.text



def test_production_debug_mode_is_disabled(make_settings: Callable[..., Settings]) -> None:
    with pytest.raises(ValidationError, match="DEBUG must be false"):
        make_settings(
            app_env="production",
            debug=True,
            storage_backend="postgres",
            supabase_db_url=TEST_DATABASE_URL,
        )
