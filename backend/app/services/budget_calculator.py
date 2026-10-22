"""Pure Decimal-safe budget calculations and deterministic explanations."""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app.core.money import quantize_money
from app.models.budget import (
    DEFAULT_EXPENSE_CATEGORIES,
    MAX_MONEY,
    MAX_RESERVE_PERCENTAGE,
    BudgetStatus,
    Expense,
    IssueSeverity,
    ReserveType,
)


class BudgetCalculationError(ValueError):
    """Invalid financial input supplied directly to the calculator."""


@dataclass(frozen=True, slots=True)
class BudgetIssue:
    """A deterministic explanation of the current budget state."""

    code: str
    severity: IssueSeverity
    message: str


@dataclass(frozen=True, slots=True)
class CategoryTotal:
    """Planned spending grouped by category."""

    category: str
    amount: Decimal


@dataclass(frozen=True, slots=True)
class BudgetCalculation:
    """All server-derived budget summary values."""

    total_limit: Decimal
    reserve_amount: Decimal
    available_for_planning: Decimal
    planned_spending: Decimal
    remaining_total: Decimal
    remaining_after_reserve: Decimal
    budget_overrun: Decimal
    reserve_consumed: Decimal
    cost_per_guest: Decimal | None
    status: BudgetStatus
    issues: tuple[BudgetIssue, ...]
    category_totals: tuple[CategoryTotal, ...]


def _validated_money(value: Decimal, *, field: str, allow_zero: bool) -> Decimal:
    if not isinstance(value, Decimal):
        raise BudgetCalculationError(f"{field} must be a Decimal.")
    if not value.is_finite():
        raise BudgetCalculationError(f"{field} must be finite.")
    if value < 0 or (not allow_zero and value == 0):
        comparison = "zero or greater" if allow_zero else "greater than zero"
        raise BudgetCalculationError(f"{field} must be {comparison}.")
    if value > MAX_MONEY:
        raise BudgetCalculationError(f"{field} exceeds the supported monetary limit.")
    try:
        return quantize_money(value)
    except InvalidOperation as exc:
        raise BudgetCalculationError(f"{field} cannot be represented as money.") from exc


def calculate_budget_summary(
    *,
    total_limit: Decimal,
    reserve_type: ReserveType,
    reserve_value: Decimal,
    currency: str,
    expenses: Iterable[Expense],
    guest_count: int | None,
) -> BudgetCalculation:
    """Calculate a budget summary from authoritative server-side inputs."""
    normalized_currency = currency.strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", normalized_currency):
        raise BudgetCalculationError("Currency must be a three-letter code.")

    total = _validated_money(total_limit, field="Total limit", allow_zero=False)

    if not isinstance(reserve_value, Decimal) or not reserve_value.is_finite():
        raise BudgetCalculationError("Reserve value must be a finite Decimal.")
    if reserve_type == ReserveType.PERCENTAGE:
        if reserve_value < 0 or reserve_value > MAX_RESERVE_PERCENTAGE:
            raise BudgetCalculationError("Reserve percentage must be between 0 and 100.")
        reserve_amount = quantize_money(total * reserve_value / Decimal("100"))
    elif reserve_type == ReserveType.FIXED_AMOUNT:
        reserve_amount = _validated_money(
            reserve_value,
            field="Reserve amount",
            allow_zero=True,
        )
        if reserve_amount > total:
            raise BudgetCalculationError("Reserve amount cannot exceed the total limit.")
    else:
        raise BudgetCalculationError("Unsupported reserve type.")

    category_sums: dict[str, Decimal] = {}
    planned = Decimal("0")
    for expense in expenses:
        amount = _validated_money(expense.amount, field="Expense amount", allow_zero=False)
        planned += amount
        category_sums[expense.category] = category_sums.get(expense.category, Decimal("0")) + amount

    planned = quantize_money(planned)
    available = quantize_money(total - reserve_amount)
    remaining_total = quantize_money(total - planned)
    remaining_after_reserve = quantize_money(total - planned - reserve_amount)
    overrun = quantize_money(max(Decimal("0"), planned - total))
    reserve_consumed = quantize_money(max(Decimal("0"), planned - available))

    category_totals = tuple(
        CategoryTotal(category=category, amount=quantize_money(amount))
        for category, amount in sorted(
            category_sums.items(),
            key=_category_sort_key,
        )
    )

    cost_per_guest: Decimal | None = None
    if guest_count is not None and guest_count > 0:
        cost_per_guest = quantize_money(planned / Decimal(guest_count))

    issues: list[BudgetIssue] = []
    if overrun > 0:
        status = BudgetStatus.OVER_BUDGET
        issues.append(
            BudgetIssue(
                code="total_budget_exceeded",
                severity=IssueSeverity.ERROR,
                message=(
                    f"Planned spending exceeds the total budget by "
                    f"{normalized_currency} {overrun:.2f}."
                ),
            )
        )
    elif reserve_consumed > 0:
        status = BudgetStatus.RESERVE_CONSUMED
        issues.append(
            BudgetIssue(
                code="reserve_consumed",
                severity=IssueSeverity.WARNING,
                message=(
                    f"Planned spending uses {normalized_currency} "
                    f"{reserve_consumed:.2f} of the contingency reserve."
                ),
            )
        )
    else:
        status = BudgetStatus.WITHIN_ALLOCATION

    return BudgetCalculation(
        total_limit=total,
        reserve_amount=reserve_amount,
        available_for_planning=available,
        planned_spending=planned,
        remaining_total=remaining_total,
        remaining_after_reserve=remaining_after_reserve,
        budget_overrun=overrun,
        reserve_consumed=reserve_consumed,
        cost_per_guest=cost_per_guest,
        status=status,
        issues=tuple(issues),
        category_totals=category_totals,
    )


def _category_sort_key(item: tuple[str, Decimal]) -> tuple[int, str, str]:
    category = item[0]
    try:
        return (DEFAULT_EXPENSE_CATEGORIES.index(category), "", category)
    except ValueError:
        return (len(DEFAULT_EXPENSE_CATEGORIES), category.casefold(), category)
