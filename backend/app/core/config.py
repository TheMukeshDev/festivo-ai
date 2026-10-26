"""Validated, environment-driven application configuration."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"

ConfigurationState = Literal["disabled", "incomplete", "configured"]
DEFAULT_FRONTEND_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://festivoai01.vercel.app",
]


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables and a local `.env` file."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        enable_decoding=False,
    )

    app_name: str = Field(default="Festivo AI", min_length=1, max_length=100)
    app_env: Literal["development", "test", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    app_timezone: str = Field(default="Asia/Kolkata", min_length=1, max_length=100)

    storage_backend: Literal["memory", "postgres"] = "memory"
    supabase_db_url: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("SUPABASE_DB_URL", "DATABASE_URL"),
    )
    supabase_db_connect_timeout_seconds: int = Field(default=10, ge=1, le=60)

    supabase_url: str | None = None
    supabase_jwks_url: str | None = None
    supabase_jwt_issuer: str | None = None
    supabase_jwt_audience: str = Field(default="authenticated", min_length=1, max_length=100)
    supabase_jwt_leeway_seconds: int = Field(default=30, ge=0, le=300)
    firebase_project_id: str | None = None
    firebase_client_email: str | None = None
    firebase_private_key: SecretStr | None = None

    frontend_origins: list[str] = Field(
        default_factory=lambda: list(DEFAULT_FRONTEND_ORIGINS),
        validation_alias=AliasChoices(
            "FRONTEND_ORIGINS",
            "FRONTEND_ORIGIN",
            "CORS_ORIGINS",
        ),
        description=(
            "Comma-separated or JSON-array list of explicit browser origins allowed by CORS."
        ),
    )

    llm_provider: Literal["gemini"] = "gemini"
    llm_model: str | None = Field(default=None, max_length=200)
    gemini_api_key: SecretStr | None = None
    llm_enabled: bool = False
    llm_timeout_seconds: float = Field(default=30, gt=0, le=300)
    llm_max_retries: int = Field(default=2, ge=0, le=10)
    llm_max_output_tokens: int = Field(default=2048, ge=1, le=8192)
    llm_temperature: float = Field(default=0.4, ge=0.0, le=2.0)

    proposal_ttl_hours: int = Field(default=168, ge=1, le=720)

    debug: bool = False
    docs_enabled: bool | None = None
    config_status_enabled: bool | None = None

    @field_validator("app_name")
    @classmethod
    def validate_app_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("APP_NAME must not be blank.")
        return value

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        value = value.strip()
        segments = value.split("/")[1:] if value.startswith("/") else []
        if (
            not value.startswith("/")
            or value == "/"
            or value.endswith("/")
            or not segments
            or any(not segment.replace("-", "").replace("_", "").isalnum() for segment in segments)
        ):
            raise ValueError("API_V1_PREFIX must be a path such as '/api/v1'.")
        return value

    @field_validator("app_timezone")
    @classmethod
    def validate_app_timezone(cls, value: str) -> str:
        candidate = value.strip()
        try:
            return ZoneInfo(candidate).key
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(
                "APP_TIMEZONE must be a valid IANA timezone such as 'Asia/Kolkata'."
            ) from exc

    @field_validator("supabase_db_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> object:
        if value is None:
            return None
        raw_value = value.get_secret_value() if isinstance(value, SecretStr) else str(value)
        candidate = raw_value.strip()
        if not candidate:
            return None

        try:
            parsed = urlsplit(candidate)
        except ValueError as exc:
            raise ValueError("SUPABASE_DB_URL must be a valid PostgreSQL connection URL.") from exc

        if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
            raise ValueError("SUPABASE_DB_URL must be a valid PostgreSQL connection URL.")
        return candidate

    @field_validator("supabase_url")
    @classmethod
    def validate_supabase_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        candidate = value.strip().rstrip("/")
        parsed = urlsplit(candidate)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("SUPABASE_URL must be an http(s) project URL without a path.")
        return candidate

    @field_validator("supabase_jwks_url", "supabase_jwt_issuer")
    @classmethod
    def validate_auth_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        candidate = value.strip().rstrip("/")
        if not candidate:
            return None
        parsed = urlsplit(candidate)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.fragment
        ):
            raise ValueError("Supabase authentication URLs must be valid http(s) URLs.")
        return candidate

    @field_validator("frontend_origins", mode="before")
    @classmethod
    def parse_frontend_origins(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                try:
                    value = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        "FRONTEND_ORIGINS must be a comma-separated list or a JSON array."
                    ) from exc
            else:
                value = [origin.strip() for origin in stripped.split(",") if origin.strip()]
        if not isinstance(value, (list, tuple)):
            raise ValueError("FRONTEND_ORIGINS must contain one or more origins.")
        return list(value)

    @field_validator("frontend_origins")
    @classmethod
    def validate_frontend_origins(cls, origins: list[str]) -> list[str]:
        if not origins:
            raise ValueError("At least one frontend origin must be configured.")

        normalized: list[str] = []
        for origin in origins:
            if not isinstance(origin, str):
                raise ValueError("Each frontend origin must be a string.")
            candidate = origin.strip()
            if "*" in candidate:
                raise ValueError("Wildcard CORS origins are not allowed.")

            parsed = urlsplit(candidate)
            try:
                port = parsed.port
            except ValueError as exc:
                raise ValueError(f"Invalid port in frontend origin: {candidate!r}.") from exc

            if (
                parsed.scheme.lower() not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError(
                    "Each frontend origin must be an http(s) origin without a path, "
                    "query, fragment, or credentials."
                )

            host = parsed.hostname.lower()
            netloc = f"[{host}]" if ":" in host else host
            if port is not None:
                netloc = f"{netloc}:{port}"
            normalized.append(f"{parsed.scheme.lower()}://{netloc}")

        return list(dict.fromkeys(normalized))

    @field_validator("llm_model", mode="before")
    @classmethod
    def normalize_model(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("LLM_MODEL must be a string.")
        stripped = value.strip()
        return stripped or None

    @field_validator("gemini_api_key", mode="before")
    @classmethod
    def normalize_api_key(cls, value: object) -> object:
        if value is None:
            return None
        raw_value = value.get_secret_value() if isinstance(value, SecretStr) else str(value)
        stripped = raw_value.strip()
        return stripped or None

    @model_validator(mode="after")
    def validate_cross_field_settings(self) -> Self:
        if self.app_env == "production" and self.debug:
            raise ValueError("DEBUG must be false in production.")
        if self.app_env == "production" and self.storage_backend != "postgres":
            raise ValueError("STORAGE_BACKEND must be 'postgres' in production.")
        if self.storage_backend == "postgres" and self.supabase_db_url is None:
            raise ValueError("SUPABASE_DB_URL is required when STORAGE_BACKEND is 'postgres'.")
        if self.app_env == "production" and not self.firebase_project_id:
            raise ValueError(
                "FIREBASE_PROJECT_ID is required "
                "in production."
            )

        if self.llm_enabled:
            if self.gemini_api_key is None:
                raise ValueError("GEMINI_API_KEY is required when LLM_ENABLED is true.")
            if self.llm_model is None:
                raise ValueError("LLM_MODEL is required when LLM_ENABLED is true.")
            if self.llm_model.startswith("replace_with"):
                raise ValueError(
                    "LLM_MODEL must be a provider-supported model when LLM_ENABLED is true."
                )

        return self

    @property
    def is_production(self) -> bool:
        """Whether the application is running in production mode."""
        return self.app_env == "production"

    @property
    def docs_available(self) -> bool:
        """Expose API documentation unless explicitly overridden or in production."""
        if self.docs_enabled is None:
            return not self.is_production
        return self.docs_enabled

    @property
    def config_status_available(self) -> bool:
        """Expose configuration diagnostics unless explicitly overridden or in production."""
        if self.config_status_enabled is None:
            return not self.is_production
        return self.config_status_enabled

    @property
    def credential_configured(self) -> bool:
        """Whether a non-empty Gemini credential is present, without exposing it."""
        return self.gemini_api_key is not None

    @property
    def database_configured(self) -> bool:
        """Whether a PostgreSQL connection URL is present, without exposing it."""
        return self.supabase_db_url is not None

    @property
    def resolved_jwks_url(self) -> str | None:
        """Return the configured JWKS URL or derive it from the project URL."""
        if self.supabase_jwks_url is not None:
            return self.supabase_jwks_url
        if self.supabase_url is not None:
            return f"{self.supabase_url}/auth/v1/.well-known/jwks.json"
        return None

    @property
    def resolved_jwt_issuer(self) -> str | None:
        """Return the configured token issuer or derive it from the project URL."""
        if self.supabase_jwt_issuer is not None:
            return self.supabase_jwt_issuer
        if self.supabase_url is not None:
            return f"{self.supabase_url}/auth/v1"
        return None

    @property
    def auth_configured(self) -> bool:
        """Backward-compatible alias for Firebase authentication configuration."""
        return self.firebase_auth_configured

    @property
    def firebase_auth_configured(self) -> bool:
        """Whether Firebase Admin token verification can be configured safely."""
        return bool(self.firebase_project_id)

    @property
    def llm_configuration_state(self) -> ConfigurationState:
        """Report configuration completeness, not provider connectivity."""
        if not self.llm_enabled:
            return "disabled"
        if self.credential_configured and self.llm_model is not None:
            return "configured"
        return "incomplete"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings for the current process."""
    return Settings()
