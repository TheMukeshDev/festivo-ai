"""Abstract base classes for AI providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AIProvider(ABC):
    @abstractmethod
    def generate_structured(
        self,
        *,
        system: str,
        user: str,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError


class AIProviderError(Exception):
    """Base class for AI provider errors."""


class AIConfigurationError(AIProviderError):
    """Missing or invalid AI configuration."""


class AIAuthenticationError(AIProviderError):
    """Authentication failure with provider."""


class AIRateLimitError(AIProviderError):
    """Rate limit exceeded."""


class AITimeoutError(AIProviderError):
    """Request timed out."""


class AINetworkError(AIProviderError):
    """Network/transport error."""


class AIServiceError(AIProviderError):
    """Generic provider service error."""


class AIOutputValidationError(AIProviderError):
    """Output could not be validated/parsed."""
