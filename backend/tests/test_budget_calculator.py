"""Pure budget calculation rules and deterministic issue generation."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.budget import (
    DEFAULT_EXPENSE_CATEGORIES,
    BudgetStatus,
    Expense,
    ExpenseStatus,
    IssueSeverity,
    ReserveType,
)
from app.services.budget_calculator import BudgetCalculationError, calculate_budget_summary

_NOW = datetime(2030, 5, 15, 8, 0, tzinfo=UTC)


def make_expense(amount: str, category: str = "Venue and Logistics") -> Expense:
    return Expense(
        expense_id=uuid4(),
        budget_id=uuid4(),
        category=category,
        name="Test expense",
        amount=Decimal(amount),
        amount_status=ExpenseStatus.ESTIMATED,
        notes=None,
        created_at=_NOW,
        updated_at=_NOW,
    )


def calculate(**overrides: object):
    values: dict[str, object] = {
        "total_limit": Decimal("1000.00"),
        "reserve_type": ReserveType.PERCENTAGE,
        "reserve_value": Decimal("10.00"),
        "currency": "inr",
        "expenses": (),
        "guest_count": 5,
    }
    values.update(overrides)
    return calculate_budget_summary(**values)


def test_within_allocation_summary() -> None:
    result = calculate(
        expenses=(
            make_expense("250.00"),
            make_expense("150.00", "Catering and Refreshments"),
        )
    )

    assert result.total_limit == Decimal("1000.00")
    assert result.reserve_amount == Decimal("100.00")
    assert result.available_for_planning == Decimal("900.00")
    assert result.planned_spending == Decimal("400.00")
    assert result.remaining_total == Decimal("600.00")
    assert result.remaining_after_reserve == Decimal("500.00")
    assert result.budget_overrun == Decimal("0.00")
    assert result.reserve_consumed == Decimal("0.00")
    assert result.cost_per_guest == Decimal("80.00")
    assert result.status == BudgetStatus.WITHIN_ALLOCATION
    assert result.issues == ()
    assert [total.category for total in result.category_totals] == [
        "Venue and Logistics",
        "Catering and Refreshments",
    ]


def test_spending_exactly_at_available_limit_does_not_consume_reserve() -> None:
    result = calculate(expenses=(make_expense("900.00"),))

    assert result.reserve_consumed == Decimal("0.00")
    assert result.remaining_after_reserve == Decimal("0.00")
    assert result.status == BudgetStatus.WITHIN_ALLOCATION


def test_spending_above_available_consumes_reserve() -> None:
    result = calculate(expenses=(make_expense("950.00"),))

    assert result.remaining_total == Decimal("50.00")
    assert result.remaining_after_reserve == Decimal("-50.00")
    assert result.budget_overrun == Decimal("0.00")
    assert result.reserve_consumed == Decimal("50.00")
    assert result.status == BudgetStatus.RESERVE_CONSUMED
    assert [issue.code for issue in result.issues] == ["reserve_consumed"]
    assert result.issues[0].severity == IssueSeverity.WARNING
    assert "INR 50.00" in result.issues[0].message


def test_spending_above_total_is_over_budget() -> None:
    result = calculate(expenses=(make_expense("1100.00"),))

    assert result.remaining_total == Decimal("-100.00")
    assert result.remaining_after_reserve == Decimal("-200.00")
    assert result.budget_overrun == Decimal("100.00")
    assert result.reserve_consumed == Decimal("200.00")
    assert result.status == BudgetStatus.OVER_BUDGET
    assert [issue.code for issue in result.issues] == ["total_budget_exceeded"]
    assert result.issues[0].severity == IssueSeverity.ERROR
    assert "exceeds the total budget" in result.issues[0].message


def test_fixed_reserve_is_supported() -> None:
    result = calculate(
        reserve_type=ReserveType.FIXED_AMOUNT,
        reserve_value=Decimal("250.00"),
    )

    assert result.reserve_amount == Decimal("250.00")
    assert result.available_for_planning == Decimal("750.00")


def test_zero_reserve_is_supported() -> None:
    result = calculate(reserve_value=Decimal("0.00"), expenses=(make_expense("1000.00"),))

    assert result.reserve_amount == Decimal("0.00")
    assert result.reserve_consumed == Decimal("0.00")
    assert result.status == BudgetStatus.WITHIN_ALLOCATION


def test_percentage_reserve_rounds_half_up() -> None:
    result = calculate(
        total_limit=Decimal("100.05"),
        reserve_value=Decimal("10.00"),
    )

    assert result.reserve_amount == Decimal("10.01")


def test_expense_amounts_round_half_up_before_totals() -> None:
    result = calculate(
        expenses=(
            make_expense("10.005"),
            make_expense("0.005"),
        )
    )

    assert result.planned_spending == Decimal("10.02")


def test_cost_per_guest_is_none_for_zero_or_missing_guests() -> None:
    assert calculate(guest_count=None).cost_per_guest is None
    assert calculate(guest_count=0).cost_per_guest is None


def test_category_totals_group_and_order_defaults_before_custom_categories() -> None:
    result = calculate(
        expenses=(
            make_expense("10.00", "Zebra custom"),
            make_expense("20.00", "Catering and Refreshments"),
            make_expense("5.00", "Venue and Logistics"),
            make_expense("15.00", "alpha custom"),
            make_expense("1.00", "Catering and Refreshments"),
        )
    )

    assert [total.category for total in result.category_totals] == [
        "Venue and Logistics",
        "Catering and Refreshments",
        "alpha custom",
        "Zebra custom",
    ]
    assert [total.amount for total in result.category_totals] == [
        Decimal("5.00"),
        Decimal("21.00"),
        Decimal("15.00"),
        Decimal("10.00"),
    ]
    assert sum((total.amount for total in result.category_totals), Decimal("0.00")) == (
        result.planned_spending
    )


def test_all_default_categories_are_available_for_planners() -> None:
    assert len(DEFAULT_EXPENSE_CATEGORIES) == 7
    assert len(set(DEFAULT_EXPENSE_CATEGORIES)) == len(DEFAULT_EXPENSE_CATEGORIES)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"total_limit": Decimal("0")}, "greater than zero"),
        ({"total_limit": Decimal("-1")}, "greater than zero"),
        ({"total_limit": Decimal("NaN")}, "finite"),
        ({"total_limit": 100}, "must be a Decimal"),
        ({"reserve_value": Decimal("100.01")}, "between 0 and 100"),
        ({"reserve_value": Decimal("-0.01")}, "between 0 and 100"),
        ({"reserve_value": Decimal("NaN")}, "finite"),
        (
            {"reserve_type": ReserveType.FIXED_AMOUNT, "reserve_value": Decimal("1000.01")},
            "cannot exceed the total limit",
        ),
        ({"expenses": (make_expense("0.00"),)}, "greater than zero"),
        ({"expenses": (make_expense("-1.00"),)}, "greater than zero"),
    ],
)
def test_invalid_financial_inputs_are_rejected(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(BudgetCalculationError, match=message):
        calculate(**overrides)


def test_unsupported_reserve_type_is_rejected() -> None:
    with pytest.raises(BudgetCalculationError, match="Unsupported reserve type"):
        calculate(reserve_type="unknown")


@pytest.mark.parametrize("currency", ["", "IN", "INRR", "1NR", "I1R"])
def test_invalid_currency_is_rejected(currency: str) -> None:
    with pytest.raises(BudgetCalculationError, match="three-letter"):
        calculate(currency=currency)
