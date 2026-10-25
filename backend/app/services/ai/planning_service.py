"""Personalized AI planning context and validation service."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from app.core.config import Settings
from app.core.exceptions import ResourceNotFoundError
from app.services.ai.base import AIOutputValidationError, AIProvider, AIProviderError
from app.services.ai.prompt_templates import SYSTEM_PROMPT, build_user_prompt
from app.services.ai.schemas import AIPlanResponse


class AIPlanningService:
    """Gather owner-scoped context, call Gemini, and validate its JSON output."""

    def __init__(
        self,
        provider: AIProvider | None = None,
        settings: Settings | None = None,
        event_service: Any = None,
        budget_service: Any = None,
        timeline_service: Any = None,
        task_service: Any = None,
        vendor_service: Any = None,
    ) -> None:
        self._provider = provider
        self._settings = settings
        self._event_service = event_service
        self._budget_service = budget_service
        self._timeline_service = timeline_service
        self._task_service = task_service
        self._vendor_service = vendor_service

    def build_context(
        self,
        user_id: UUID,
        event_id: str,
        preferences: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Load only the event data needed to personalize a proposal."""
        event = self._event_service.get(user_id, event_id)
        context: dict[str, Any] = {
            "event": {
                "name": event.name,
                "event_type": event.event_type.value,
                "event_date": event.event_date.isoformat(),
                "location": event.location,
                "guest_count": event.guest_count,
                "budget_amount": str(event.budget_amount),
                "currency": event.currency,
                "description": event.description,
                "preferences": list(event.preferences),
                "constraints": list(event.constraints),
            }
        }

        try:
            budget_view = self._budget_service.get(user_id, event_id)
        except ResourceNotFoundError:
            context["budget"] = None
        else:
            context["budget"] = {
                "total_limit": str(budget_view.budget.total_limit),
                "currency": budget_view.budget.currency,
                "reserve_type": budget_view.budget.reserve_type.value,
                "reserve_value": str(budget_view.budget.reserve_value),
                "reserve_amount": str(budget_view.calculation.reserve_amount),
                "available_for_planning": str(
                    budget_view.calculation.available_for_planning
                ),
                "planned_spending": str(budget_view.calculation.planned_spending),
                "remaining_total": str(budget_view.calculation.remaining_total),
                "status": budget_view.calculation.status.value,
                "expenses_count": len(budget_view.expenses),
            }

        try:
            timeline = self._timeline_service.get(user_id, event_id)
        except ResourceNotFoundError:
            context["timeline"] = None
        else:
            context["timeline"] = {
                "start_date": timeline.start_date.isoformat(),
                "end_date": timeline.end_date.isoformat(),
            }

        tasks, total = self._task_service.list_tasks(
            user_id,
            event_id,
            status=None,
            priority=None,
            timeline_id=None,
            limit=50,
            offset=0,
        )
        context["tasks"] = {
            "total": total,
            "items": [
                {
                    "title": task.title,
                    "status": task.status.value,
                    "priority": task.priority.value,
                    "due_at": task.due_at.isoformat() if task.due_at else None,
                }
                for task in tasks[:30]
            ],
        }

        if self._vendor_service is not None:
            vendors, vendor_total = self._vendor_service.list(
                user_id,
                event_id,
                category=None,
                status=None,
                min_price=None,
                max_price=None,
                name=None,
                limit=50,
                offset=0,
            )
            context["vendors"] = {
                "total": vendor_total,
                "items": [
                    {
                        "name": vendor.name,
                        "category": vendor.category.value,
                        "status": vendor.status.value,
                        "currency": vendor.currency,
                    }
                    for vendor in vendors[:30]
                ],
            }

        if preferences:
            context["user_preferences"] = preferences
        return context

    def generate_plan(
        self,
        user_id: UUID,
        event_id: str,
        preferences: dict[str, Any] | None = None,
    ) -> AIPlanResponse:
        """Request and validate one structured plan; never persist it."""
        if self._provider is None:
            raise AIProviderError("AI provider is not configured.")

        context = self.build_context(user_id, event_id, preferences)
        user_prompt = build_user_prompt(json.dumps(context, default=str))
        try:
            raw = self._provider.generate_structured(system=SYSTEM_PROMPT, user=user_prompt)
        except AIOutputValidationError:
            repair_prompt = (
                user_prompt
                + "\n\nReturn ONLY valid JSON with every required field. No markdown."
            )
            raw = self._provider.generate_structured(
                system=SYSTEM_PROMPT,
                user=repair_prompt,
            )

        if not isinstance(raw, dict):
            raise AIOutputValidationError("AI response was not a JSON object.")
        candidate = dict(raw)
        candidate.setdefault("event_id", str(event_id))
        candidate.setdefault("generated_at", datetime.now(UTC).isoformat())
        candidate.setdefault("model_used", self._model_used())
        try:
            return AIPlanResponse.model_validate(candidate)
        except ValidationError as exc:
            raise AIOutputValidationError("AI response could not be validated.") from exc

    def refine_plan(
        self,
        user_id: UUID,
        event_id: str,
        preferences: dict[str, Any] | None = None,
        additional_notes: str | None = None,
    ) -> AIPlanResponse:
        prefs = dict(preferences or {})
        if additional_notes:
            prefs["additional_notes"] = additional_notes
        return self.generate_plan(user_id, event_id, prefs)

    def _model_used(self) -> str:
        model = getattr(self._settings, "llm_model", None) if self._settings else None
        return model if isinstance(model, str) and model else "unknown"
