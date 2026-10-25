"""Gemini provider implementation using google-genai when available."""

from __future__ import annotations

import json
import time
from typing import Any

from app.core.config import Settings
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


class GeminiProvider(AIProvider):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = None
        if not settings.llm_enabled:
            raise AIConfigurationError("LLM is disabled")
        if settings.gemini_api_key is None:
            raise AIConfigurationError("GEMINI_API_KEY is required when LLM_ENABLED is true")
        if settings.llm_model is None or settings.llm_model.startswith("replace_with"):
            raise AIConfigurationError(
                "LLM_MODEL must be a provider-supported model when LLM_ENABLED is true"
            )
        try:
            from google import genai

            self._genai = genai
            self._client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
        except Exception as exc:
            raise AIConfigurationError(
                "Gemini SDK is not available or could not be configured."
            ) from exc

    def generate_structured(
        self,
        *,
        system: str,
        user: str,
        schema: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        model = self._settings.llm_model
        max_retries = int(self._settings.llm_max_retries)
        max_tokens = int(self._settings.llm_max_output_tokens)
        temperature = float(self._settings.llm_temperature)

        for attempt in range(max_retries + 1):
            try:
                config: dict[str, Any] = {
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                    "system_instruction": system,
                }
                if schema is not None:
                    config["response_mime_type"] = "application/json"
                    config["response_schema"] = schema
                response = self._client.models.generate_content(
                    model=model,
                    contents=user,
                    config=config,
                )
                return self._parse_response(response)
            except (AIAuthenticationError, AIRateLimitError):
                raise
            except (
                AIConfigurationError,
                AITimeoutError,
                AINetworkError,
                AIServiceError,
                AIOutputValidationError,
            ):
                if attempt >= max_retries:
                    raise
                self._backoff(attempt)
            except Exception as exc:
                provider_error = self._classify_error(exc)
                if isinstance(provider_error, (AIAuthenticationError, AIRateLimitError)):
                    raise provider_error from exc
                if attempt >= max_retries:
                    raise provider_error from exc
                self._backoff(attempt)
        raise AIServiceError("Provider request failed")

    @staticmethod
    def _parse_response(response: Any) -> dict[str, Any]:
        text = getattr(response, "text", None)
        if not text:
            candidates = getattr(response, "candidates", None) or []
            if candidates:
                content = getattr(candidates[0], "content", None)
                parts = getattr(content, "parts", None) or []
                text = "".join(getattr(part, "text", "") or "" for part in parts)
        if not text:
            raise AIOutputValidationError("Empty response from Gemini")
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AIOutputValidationError("Malformed JSON from Gemini") from exc
        if not isinstance(parsed, dict):
            raise AIOutputValidationError("Gemini response is not a JSON object")
        return parsed

    @staticmethod
    def _classify_error(exc: Exception) -> AIProviderError:
        message = str(exc).lower()
        if "timeout" in message:
            return AITimeoutError("Request timed out")
        if "rate" in message and "limit" in message:
            return AIRateLimitError("Rate limit exceeded")
        if "auth" in message or "api key" in message or "permission" in message:
            return AIAuthenticationError("Authentication failed")
        if "network" in message or "connection" in message:
            return AINetworkError("Network error")
        return AIServiceError("Provider error")

    @staticmethod
    def _backoff(attempt: int) -> None:
        time.sleep((2**attempt) * 0.1)
