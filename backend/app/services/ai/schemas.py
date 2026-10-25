"""Pydantic schemas for AI planning outputs."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BudgetSource(StrEnum):
    SUGGESTED_ALLOCATION = "suggested_allocation"
    USER_PROVIDED_BUDGET = "user_provided_budget"
    EXISTING_ESTIMATE_OR_QUOTE = "existing_estimate_or_quote"
    CONFIRMED_EXPENSE = "confirmed_expense"


class Recommendation(BaseModel):
    category: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=2000)
    rationale: str = Field(min_length=1, max_length=2000)
    priority: Priority = Priority.MEDIUM
    assumptions: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("assumptions")
    @classmethod
    def validate_assumptions(cls, v: list[str]) -> list[str]:
        cleaned = []
        for item in v:
            if isinstance(item, str) and item.strip():
                cleaned.append(item.strip())
        return cleaned[:20]


class TaskSuggestion(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    explanation: str = Field(min_length=1, max_length=2000)
    suggested_timing: str | None = Field(default=None, max_length=200)
    relative_deadline: str | None = Field(default=None, max_length=200)
    priority: Priority = Priority.MEDIUM
    category: str | None = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def validate_timing(self) -> TaskSuggestion:
        if self.suggested_timing is None and self.relative_deadline is None:
            # allow either; keep flexible
            pass
        return self


class BudgetSuggestion(BaseModel):
    category: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=1000)
    source: BudgetSource = BudgetSource.SUGGESTED_ALLOCATION
    suggested_amount: Decimal | None = None
    currency: str = Field(min_length=3, max_length=3)
    rationale: str = Field(min_length=1, max_length=2000)
    exceeds_available: bool = False
    assumptions: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        v = v.strip().upper()
        if len(v) != 3 or not v.isalpha():
            raise ValueError("currency must be a 3-letter ISO code")
        return v

    @field_validator("suggested_amount")
    @classmethod
    def validate_amount(cls, v: Decimal | None) -> Decimal | None:
        if v is None:
            return None
        if v < 0:
            raise ValueError("suggested_amount must be non-negative")
        return v


class VendorCategorySuggestion(BaseModel):
    category: str = Field(min_length=1, max_length=80)
    rationale: str = Field(min_length=1, max_length=1000)
    priority: Priority = Priority.MEDIUM
    notes: str | None = Field(default=None, max_length=1000)


class AIPlanResponse(BaseModel):
    event_id: str
    summary: str = Field(min_length=1, max_length=3000)
    theme_ideas: list[str] = Field(default_factory=list, max_length=30)
    recommendations: list[Recommendation] = Field(default_factory=list, max_length=80)
    budget_suggestions: list[BudgetSuggestion] = Field(default_factory=list, max_length=80)
    timeline_suggestions: list[str] = Field(default_factory=list, max_length=80)
    task_suggestions: list[TaskSuggestion] = Field(default_factory=list, max_length=80)
    vendor_category_suggestions: list[VendorCategorySuggestion] = Field(default_factory=list, max_length=80)
    risks_and_constraints: list[str] = Field(default_factory=list, max_length=80)
    assumptions: list[str] = Field(default_factory=list, max_length=80)
    next_steps: list[str] = Field(default_factory=list, max_length=80)
    generated_at: datetime
    model_used: str = Field(min_length=1, max_length=200)

    @field_validator("theme_ideas", "timeline_suggestions", "risks_and_constraints", "assumptions", "next_steps")
    @classmethod
    def validate_string_lists(cls, v: list[str]) -> list[str]:
        cleaned = []
        for item in v:
            if isinstance(item, str) and item.strip():
                cleaned.append(item.strip())
            if len(cleaned) >= 80:
                break
        return cleaned

    @model_validator(mode="after")
    def validate_sanity(self) -> AIPlanResponse:
        # ensure no obvious bad values
        if not self.event_id:
            raise ValueError("event_id required")
        return self


class AIPlanRequest(BaseModel):
    preferences: dict[str, Any] = Field(default_factory=dict)
    focus_areas: list[str] = Field(default_factory=list, max_length=20)
    additional_notes: str | None = Field(default=None, max_length=2000)

