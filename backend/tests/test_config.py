"""Configuration loading, validation, and safe diagnostics behavior."""

from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app
from tests.conftest import SENSITIVE_TEST_KEY, TEST_DATABASE_URL


def test_application_starts_without_a_gemini_key(client: TestClient) -> None:
    settings = client.app.state.settings

    assert settings.gemini_api_key is None
    assert settings.credential_configured is False

    response = client.get("/api/v1/config/status")
    assert response.status_code == 200
    assert response.json() == {
        "environment": "test",
        "llm": {
            "provider": "gemini",
            "enabled": False,
            "model": None,
            "credential_configured": False,
            "configuration_status": "disabled",
            "connectivity": "not_checked",
        },
    }


def test_empty_optional_credential_is_treated_as_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "")

    settings = Settings(_env_file=None)

    assert settings.gemini_api_key is None
    assert settings.credential_configured is False


def test_singular_frontend_origin_environment_variable_is_supported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "FRONTEND_ORIGIN",
        "https://festivo.example, http://localhost:5173/",
    )

    settings = Settings(_env_file=None)

    assert settings.frontend_origins == [
        "https://festivo.example",
        "http://localhost:5173",
    ]


def test_environment_variables_override_local_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "APP_NAME=Dotenv Festivo\nLLM_MAX_RETRIES=1\nLLM_MODEL=model-from-file\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("APP_NAME", "Environment Festivo")
    monkeypatch.setenv("LLM_MAX_RETRIES", "4")

    settings = Settings(_env_file=env_file)

    assert settings.app_name == "Environment Festivo"
    assert settings.llm_max_retries == 4
    assert settings.llm_model == "model-from-file"


def test_event_timezone_defaults_to_asia_kolkata(
    make_settings: Callable[..., Settings],
) -> None:
    settings = make_settings()

    assert settings.app_timezone == "Asia/Kolkata"


@pytest.mark.parametrize("timezone", ["Mars/Olympus", "", "../etc/passwd"])
def test_invalid_event_timezone_is_rejected(
    timezone: str,
    make_settings: Callable[..., Settings],
) -> None:
    with pytest.raises(ValidationError):
        make_settings(app_timezone=timezone)


@pytest.mark.parametrize("timeout", [0, -1, 301])
def test_invalid_timeout_is_rejected(
    timeout: float, make_settings: Callable[..., Settings]
) -> None:
    with pytest.raises(ValidationError):
        make_settings(llm_timeout_seconds=timeout)


@pytest.mark.parametrize("retries", [-1, 11])
def test_invalid_retry_count_is_rejected(
    retries: int, make_settings: Callable[..., Settings]
) -> None:
    with pytest.raises(ValidationError):
        make_settings(llm_max_retries=retries)


@pytest.mark.parametrize("ttl", [0, -1, 721])
def test_invalid_proposal_ttl_is_rejected(
    ttl: int, make_settings: Callable[..., Settings]
) -> None:
    with pytest.raises(ValidationError):
        make_settings(proposal_ttl_hours=ttl)


def test_enabling_llm_without_key_fails_with_clear_error(
    make_settings: Callable[..., Settings],
) -> None:
    with pytest.raises(ValidationError, match="GEMINI_API_KEY"):
        make_settings(llm_enabled=True, llm_model="test-gemini-model")


def test_enabling_llm_without_model_fails_with_clear_error(
    make_settings: Callable[..., Settings],
) -> None:
    with pytest.raises(ValidationError, match="LLM_MODEL"):
        make_settings(llm_enabled=True, gemini_api_key=SENSITIVE_TEST_KEY)


def test_placeholder_model_is_not_silently_replaced(make_settings: Callable[..., Settings]) -> None:
    with pytest.raises(ValidationError, match="provider-supported model"):
        make_settings(
            llm_enabled=True,
            gemini_api_key=SENSITIVE_TEST_KEY,
            llm_model="replace_with_supported_model_id",
        )


def test_config_status_distinguishes_credentials_from_connectivity(
    make_settings: Callable[..., Settings],
) -> None:
    settings = make_settings(
        llm_enabled=True,
        gemini_api_key=SENSITIVE_TEST_KEY,
        llm_model="test-gemini-model",
    )

    with TestClient(create_app(settings)) as test_client:
        response = test_client.get("/api/v1/config/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["llm"] == {
        "provider": "gemini",
        "enabled": True,
        "model": "test-gemini-model",
        "credential_configured": True,
        "configuration_status": "configured",
        "connectivity": "not_checked",
    }
    assert SENSITIVE_TEST_KEY not in response.text


def test_production_disables_docs_and_config_diagnostics_by_default(
    make_settings: Callable[..., Settings],
) -> None:
    settings = make_settings(
        app_env="production",
        storage_backend="postgres",
        supabase_db_url=TEST_DATABASE_URL,
    )

    assert settings.docs_available is False
    assert settings.config_status_available is False

    with TestClient(create_app(settings)) as test_client:
        assert test_client.get("/api/v1/config/status").status_code == 404
        assert test_client.get("/docs").status_code == 404
        assert test_client.get("/openapi.json").status_code == 404


def test_production_behavior_can_be_explicitly_overridden(
    make_settings: Callable[..., Settings],
) -> None:
    settings = make_settings(
        app_env="production",
        storage_backend="postgres",
        supabase_db_url=TEST_DATABASE_URL,
        docs_enabled=True,
        config_status_enabled=True,
    )

    with TestClient(create_app(settings)) as test_client:
        assert test_client.get("/api/v1/config/status").status_code == 200
        assert test_client.get("/openapi.json").status_code == 200


def test_debug_is_rejected_in_production(make_settings: Callable[..., Settings]) -> None:
    with pytest.raises(ValidationError, match="DEBUG must be false"):
        make_settings(
            app_env="production",
            debug=True,
            storage_backend="postgres",
            supabase_db_url=TEST_DATABASE_URL,
        )


def test_production_requires_postgres_storage(make_settings: Callable[..., Settings]) -> None:
    with pytest.raises(ValidationError, match="STORAGE_BACKEND"):
        make_settings(app_env="production")


def test_postgres_storage_requires_database_url(make_settings: Callable[..., Settings]) -> None:
    with pytest.raises(ValidationError, match="SUPABASE_DB_URL"):
        make_settings(storage_backend="postgres")


@pytest.mark.parametrize(
    "database_url",
    [
        "",
        "sqlite:///local.db",
        "postgresql://",
        "https://example.com/database",
    ],
)
def test_invalid_database_urls_are_rejected(
    database_url: str,
    make_settings: Callable[..., Settings],
) -> None:
    with pytest.raises(ValidationError):
        make_settings(storage_backend="postgres", supabase_db_url=database_url)


def test_database_url_is_secret_and_never_appears_in_safe_diagnostics(
    make_settings: Callable[..., Settings],
) -> None:
    settings = make_settings(
        storage_backend="postgres",
        supabase_db_url=TEST_DATABASE_URL,
    )

    assert settings.database_configured is True
    assert "test-password" not in repr(settings)

    with TestClient(create_app(settings)) as test_client:
        response = test_client.get("/api/v1/config/status")

    assert response.status_code == 200
    assert "test-password" not in response.text
    assert "localhost:5432" not in response.text
