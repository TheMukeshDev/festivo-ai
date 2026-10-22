"""Immutable budget domain models and financial constants."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

MAX_MONEY = Decimal("100000000.00")
MAX_RESERVE_PERCENTAGE = Decimal("100.00")

DEFAULT_EXPENSE_CATEGORIES = (
    "Venue and Logistics",
    "Catering and Refreshments",
    "Decoration and Theme",
    "Photography and Videography",
    "Entertainment and Activities",
    "Transportation",
    "Miscellaneous",
)


class ReserveType(StrEnum):
    """How a contingency reserve is configured."""

    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"


class ExpenseStatus(StrEnum):
    """Confidence level recorded for an expense amount."""

    ESTIMATED = "estimated"
    QUOTED = "quoted"
    CONFIRMED = "confirmed"


class BudgetStatus(StrEnum):
    """Authoritative budget state derived from current expenses."""

    WITHIN_ALLOCATION = "within_allocation"
    RESERVE_CONSUMED = "reserve_consumed"
    OVER_BUDGET = "over_budget"


class IssueSeverity(StrEnum):
    """Severity of a deterministic budget explanation."""

    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Budget:
    """A one-per-event spending plan."""

    budget_id: UUID
    event_id: UUID
    total_limit: Decimal
    currency: str
    reserve_type: ReserveType
    reserve_value: Decimal
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Expense:
    """A planned budget line item in the budget currency."""

    expense_id: UUID
    budget_id: UUID
    category: str
    name: str
    amount: Decimal
    amount_status: ExpenseStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime
