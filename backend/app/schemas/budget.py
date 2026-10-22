"""Validated budget, reserve, and expense API contracts."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StringConstraints,
)

from app.core.money import quantize_money
from app.models.budget import (
    MAX_MONEY,
    MAX_RESERVE_PERCENTAGE,
    BudgetStatus,
    ExpenseStatus,
    IssueSeverity,
    ReserveType,
)


def _normalize_percentage(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


PositiveMoney = Annotated[
    Decimal,
    Field(
        gt=Decimal("0"),
        le=MAX_MONEY,
        max_digits=12,
        decimal_places=2,
        allow_inf_nan=False,
        description="Positive monetary amount with at most two decimal places.",
    ),
    AfterValidator(quantize_money),
]
NonNegativeMoney = Annotated[
    Decimal,
    Field(
        ge=Decimal("0"),
        le=MAX_MONEY,
        max_digits=12,
        decimal_places=2,
        allow_inf_nan=False,
        description="Non-negative monetary amount with at most two decimal places.",
    ),
    AfterValidator(quantize_money),
]
ReservePercentage = Annotated[
    Decimal,
    Field(
        ge=Decimal("0"),
        le=MAX_RESERVE_PERCENTAGE,
        max_digits=5,
        decimal_places=2,
        allow_inf_nan=False,
        description="Reserve percentage from 0 to 100.",
    ),
    AfterValidator(_normalize_percentage),
]
ExpenseCategory = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=80),
    Field(description="Default or custom expense category."),
]
ExpenseName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=120),
    Field(description="User-facing expense name."),
]
ExpenseNotes = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=500),
    Field(description="Optional notes about the expense."),
]
ExpectedVersion = Annotated[
    StrictInt,
    Field(ge=1, description="Current budget version used for optimistic concurrency."),
]


class PercentageReserve(BaseModel):
    """Reserve configured as a percentage of the total limit."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["percentage"] = "percentage"
    value: ReservePercentage


class FixedReserve(BaseModel):
    """Reserve configured as an absolute amount in the budget currency."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["fixed_amount"] = "fixed_amount"
    value: NonNegativeMoney


ReserveInput = Annotated[
    PercentageReserve | FixedReserve,
    Field(discriminator="type"),
]


class BudgetCreate(BaseModel):
    """Create the single budget associated with an event."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "total_limit": "750000.00",
                "reserve": {"type": "percentage", "value": "10.00"},
            }
        },
    )

    total_limit: PositiveMoney | None = None
    reserve: ReserveInput | None = None


class BudgetUpdate(BaseModel):
    """Partially update budget limits with optimistic concurrency."""

    model_config = ConfigDict(extra="forbid")

    expected_version: ExpectedVersion
    total_limit: PositiveMoney | None = None
    reserve: ReserveInput | None = None


class ExpenseCreate(BaseModel):
    """Add a planned expense to an existing budget."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "expected_version": 1,
                "category": "Catering and Refreshments",
                "name": "Dinner service",
                "amount": "180000.00",
                "amount_status": "quoted",
                "notes": "Venue catering proposal, not independently verified.",
            }
        },
    )

    expected_version: ExpectedVersion
    category: ExpenseCategory
    name: ExpenseName
    amount: PositiveMoney
    amount_status: ExpenseStatus = ExpenseStatus.ESTIMATED
    notes: ExpenseNotes | None = None


class ExpenseUpdate(BaseModel):
    """Partially update an expense with optimistic concurrency."""

    model_config = ConfigDict(extra="forbid")

    expected_version: ExpectedVersion
    category: ExpenseCategory | None = None
    name: ExpenseName | None = None
    amount: PositiveMoney | None = None
    amount_status: ExpenseStatus | None = None
    notes: ExpenseNotes | None = None


class ReserveResponse(BaseModel):
    """Configured reserve and its calculated monetary amount."""

    model_config = ConfigDict(extra="forbid")

    type: ReserveType
    value: Decimal
    amount: Decimal


class ExpenseResponse(BaseModel):
    """A stored budget expense."""

    model_config = ConfigDict(extra="forbid")

    expense_id: str
    category: str
    name: str
    amount: Decimal
    amount_status: ExpenseStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime


class CategoryTotalResponse(BaseModel):
    """Planned spending grouped by expense category."""

    model_config = ConfigDict(extra="forbid")

    category: str
    amount: Decimal


class BudgetIssueResponse(BaseModel):
    """A deterministic explanation of a budget issue."""

    model_config = ConfigDict(extra="forbid")

    code: str
    severity: IssueSeverity
    message: str


class BudgetResponse(BaseModel):
    """Authoritative, server-calculated budget summary."""

    model_config = ConfigDict(extra="forbid")

    budget_id: str
    event_id: str
    total_limit: Decimal
    currency: str
    reserve: ReserveResponse
    planned_spending: Decimal
    available_for_planning: Decimal
    remaining_total: Decimal
    remaining_after_reserve: Decimal
    budget_overrun: Decimal
    reserve_consumed: Decimal
    cost_per_guest: Decimal | None
    status: BudgetStatus
    version: int
    issues: list[BudgetIssueResponse]
    category_totals: list[CategoryTotalResponse]
    expenses: list[ExpenseResponse]
    created_at: datetime
    updated_at: datetime
