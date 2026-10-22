"""Health and safe configuration diagnostic response models."""

from typing import Literal

from pydantic import BaseModel, Field

ConfigurationState = Literal["disabled", "incomplete", "configured"]
ConnectivityState = Literal["not_checked"]


class HealthResponse(BaseModel):
    """Minimal process health response."""

    status: Literal["ok"] = Field(default="ok", description="Process status.")


class ApiHealthResponse(HealthResponse):
    """Versioned API health response."""

    service: str = Field(description="Application name.")
    api_version: Literal["v1"] = Field(default="v1", description="API major version.")


class LLMConfigurationStatus(BaseModel):
    """Safe LLM configuration details that do not expose credentials."""

    provider: str = Field(description="Configured LLM provider.")
    enabled: bool = Field(description="Whether LLM features are enabled.")
    model: str | None = Field(description="Configured provider model identifier.")
    credential_configured: bool = Field(
        description="Whether an API credential is present. The value is never returned."
    )
    configuration_status: ConfigurationState = Field(
        description="Configuration completeness; this does not imply provider connectivity."
    )
    connectivity: ConnectivityState = Field(
        default="not_checked",
        description="Provider connectivity is not verified by this endpoint.",
    )


class ConfigurationStatusResponse(BaseModel):
    """Safe configuration diagnostics for development or authorized operations."""

    environment: str = Field(description="Deployment environment name.")
    llm: LLMConfigurationStatus
