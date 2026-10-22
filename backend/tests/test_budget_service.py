"""Budget service lifecycle, validation, and optimistic concurrency."""

from decimal import Decimal

import pytest

from app.core.exceptions import (
    DomainValidationError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.models.budget import BudgetStatus, ExpenseStatus, ReserveType
from app.schemas.budget import (
    BudgetCreate,
    BudgetUpdate,
    ExpenseCreate,
    ExpenseUpdate,
    FixedReserve,
    PercentageReserve,
)
from app.schemas.event import EventCreate
from app.services.budget_service import BudgetService
from app.services.event_service import EventService


@pytest.fixture
def event(
    event_service: EventService,
    event_payload,
):
    return event_service.create(EventCreate.model_validate(event_payload()))


@pytest.fixture
def budget(budget_service: BudgetService, event):
    return budget_service.create(
        str(event.event_id),
        BudgetCreate(
            total_limit=Decimal("1000.00"),
            reserve=PercentageReserve(value=Decimal("10.00")),
        ),
    )


def add_expense(
    budget_service: BudgetService,
    event_id: str,
    expected_version: int,
    amount: str = "100.00",
    **overrides: object,
):
    values: dict[str, object] = {
        "expected_version": expected_version,
        "category": "Catering and Refreshments",
        "name": "Dinner",
        "amount": Decimal(amount),
    }
    values.update(overrides)
    return budget_service.add_expense(event_id, ExpenseCreate(**values))


def test_create_uses_event_budget_and_currency_by_default(
    budget_service: BudgetService,
    event,
) -> None:
    view = budget_service.create(str(event.event_id), BudgetCreate())

    assert view.budget.total_limit == event.budget_amount
    assert view.budget.currency == event.currency
    assert view.budget.reserve_type == ReserveType.PERCENTAGE
    assert view.budget.reserve_value == Decimal("0.00")
    assert view.budget.version == 1
    assert view.expenses == ()
    assert view.calculation.planned_spending == Decimal("0.00")
    assert view.calculation.status == BudgetStatus.WITHIN_ALLOCATION
    assert view.calculation.cost_per_guest == Decimal("0.00")


def test_create_supports_custom_limit_and_fixed_reserve(
    budget_service: BudgetService,
    event,
) -> None:
    view = budget_service.create(
        str(event.event_id),
        BudgetCreate(
            total_limit=Decimal("2000.00"),
            reserve=FixedReserve(value=Decimal("300.00")),
        ),
    )

    assert view.budget.total_limit == Decimal("2000.00")
    assert view.budget.reserve_type == ReserveType.FIXED_AMOUNT
    assert view.budget.reserve_value == Decimal("300.00")
    assert view.calculation.available_for_planning == Decimal("1700.00")


def test_only_one_budget_can_exist_per_event(
    budget_service: BudgetService,
    event,
) -> None:
    budget_service.create(str(event.event_id), BudgetCreate())

    with pytest.raises(ResourceConflictError):
        budget_service.create(str(event.event_id), BudgetCreate())


def test_create_rejects_fixed_reserve_above_total(
    budget_service: BudgetService,
    event,
) -> None:
    with pytest.raises(DomainValidationError) as error:
        budget_service.create(
            str(event.event_id),
            BudgetCreate(
                total_limit=Decimal("100.00"),
                reserve=FixedReserve(value=Decimal("100.01")),
            ),
        )

    assert error.value.issues[0].field == "body.reserve.value"
    with pytest.raises(ResourceNotFoundError):
        budget_service.get(str(event.event_id))


def test_get_returns_recalculated_summary(
    budget_service: BudgetService,
    event,
    budget,
) -> None:
    add_expense(budget_service, str(event.event_id), 1, "950.00")

    view = budget_service.get(str(event.event_id))

    assert view.budget.version == 2
    assert view.calculation.planned_spending == Decimal("950.00")
    assert view.calculation.status == BudgetStatus.RESERVE_CONSUMED


def test_missing_event_and_budget_are_distinct_not_found_errors(
    budget_service: BudgetService,
    event,
) -> None:
    with pytest.raises(ResourceNotFoundError):
        budget_service.get("not-a-valid-id")
    with pytest.raises(ResourceNotFoundError):
        budget_service.get(str(event.event_id))


def test_update_changes_settings_and_increments_version(
    budget_service: BudgetService,
    event,
    budget,
) -> None:
    view = budget_service.update(
        str(event.event_id),
        BudgetUpdate(
            expected_version=1,
            total_limit=Decimal("1500.00"),
            reserve=FixedReserve(value=Decimal("100.00")),
        ),
    )

    assert view.budget.total_limit == Decimal("1500.00")
    assert view.budget.reserve_type == ReserveType.FIXED_AMOUNT
    assert view.budget.version == 2


def test_stale_budget_version_is_rejected(
    budget_service: BudgetService,
    event,
    budget,
) -> None:
    budget_service.update(
        str(event.event_id),
        BudgetUpdate(expected_version=1, total_limit=Decimal("1200.00")),
    )

    with pytest.raises(ResourceConflictError):
        budget_service.update(
            str(event.event_id),
            BudgetUpdate(expected_version=1, total_limit=Decimal("1300.00")),
        )


def test_noop_budget_update_does_not_increment_version(
    budget_service: BudgetService,
    event,
    budget,
) -> None:
    view = budget_service.update(
        str(event.event_id),
        BudgetUpdate(expected_version=1, total_limit=Decimal("1000.00")),
    )

    assert view.budget.version == 1


def test_stale_noop_budget_update_is_rejected(
    budget_service: BudgetService,
    event,
    budget,
) -> None:
    with pytest.raises(ResourceConflictError):
        budget_service.update(
            str(event.event_id),
            BudgetUpdate(expected_version=2),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("total_limit", None),
        ("reserve", None),
    ],
)
def test_budget_update_rejects_explicit_nulls(
    field: str,
    value: object,
    budget_service: BudgetService,
    event,
    budget,
) -> None:
    payload = BudgetUpdate(expected_version=1, **{field: value})

    with pytest.raises(DomainValidationError) as error:
        budget_service.update(str(event.event_id), payload)

    assert error.value.issues[0].field == f"body.{field}"


def test_budget_update_rejects_fixed_reserve_above_new_total(
    budget_service: BudgetService,
    event,
) -> None:
    budget_service.create(
        str(event.event_id),
        BudgetCreate(
            total_limit=Decimal("1000.00"),
            reserve=FixedReserve(value=Decimal("500.00")),
        ),
    )

    with pytest.raises(DomainValidationError):
        budget_service.update(
            str(event.event_id),
            BudgetUpdate(expected_version=1, total_limit=Decimal("400.00")),
        )


def test_add_expense_recalculates_totals_and_cost_per_guest(
    budget_service: BudgetService,
    event,
    budget,
) -> None:
    view = add_expense(
        budget_service,
        str(event.event_id),
        1,
        "250.00",
        amount_status=ExpenseStatus.QUOTED,
        notes="Vendor proposal, not independently verified.",
    )

    assert view.budget.version == 2
    assert len(view.expenses) == 1
    assert view.expenses[0].amount_status == ExpenseStatus.QUOTED
    assert view.expenses[0].notes == "Vendor proposal, not independently verified."
    assert view.calculation.planned_spending == Decimal("250.00")
    assert view.calculation.cost_per_guest == Decimal("1.67")


def test_add_expense_with_stale_version_is_rejected(
    budget_service: BudgetService,
    event,
    budget,
) -> None:
    with pytest.raises(ResourceConflictError):
        add_expense(budget_service, str(event.event_id), 2)


def test_update_expense_changes_fields_and_increments_version(
    budget_service: BudgetService,
    event,
    budget,
) -> None:
    added = add_expense(budget_service, str(event.event_id), 1)
    expense_id = str(added.expenses[0].expense_id)

    view = budget_service.update_expense(
        str(event.event_id),
        expense_id,
        ExpenseUpdate(
            expected_version=2,
            category="Venue and Logistics",
            name="Updated dinner",
            amount=Decimal("350.00"),
            amount_status=ExpenseStatus.CONFIRMED,
            notes=None,
        ),
    )

    assert view.budget.version == 3
    assert view.expenses[0].category == "Venue and Logistics"
    assert view.expenses[0].name == "Updated dinner"
    assert view.expenses[0].amount == Decimal("350.00")
    assert view.expenses[0].amount_status == ExpenseStatus.CONFIRMED
    assert view.expenses[0].notes is None


def test_update_expense_rejects_explicit_nulls_except_notes(
    budget_service: BudgetService,
    event,
    budget,
) -> None:
    added = add_expense(budget_service, str(event.event_id), 1)
    expense_id = str(added.expenses[0].expense_id)

    with pytest.raises(DomainValidationError) as error:
        budget_service.update_expense(
            str(event.event_id),
            expense_id,
            ExpenseUpdate(expected_version=2, name=None),
        )

    assert error.value.issues[0].field == "body.name"


def test_noop_expense_update_does_not_increment_version(
    budget_service: BudgetService,
    event,
    budget,
) -> None:
    added = add_expense(budget_service, str(event.event_id), 1)
    expense_id = str(added.expenses[0].expense_id)

    view = budget_service.update_expense(
        str(event.event_id),
        expense_id,
        ExpenseUpdate(expected_version=2, name="Dinner"),
    )

    assert view.budget.version == 2


def test_update_or_delete_unknown_expense_is_not_found(
    budget_service: BudgetService,
    event,
    budget,
) -> None:
    unknown_id = "00000000-0000-4000-8000-000000000000"

    with pytest.raises(ResourceNotFoundError):
        budget_service.update_expense(
            str(event.event_id),
            unknown_id,
            ExpenseUpdate(expected_version=1, amount=Decimal("10.00")),
        )
    with pytest.raises(ResourceNotFoundError):
        budget_service.delete_expense(str(event.event_id), unknown_id, 1)


def test_delete_expense_increments_version_and_recalculates(
    budget_service: BudgetService,
    event,
    budget,
) -> None:
    added = add_expense(budget_service, str(event.event_id), 1, "200.00")
    expense_id = str(added.expenses[0].expense_id)

    view = budget_service.delete_expense(str(event.event_id), expense_id, 2)

    assert view.budget.version == 3
    assert view.expenses == ()
    assert view.calculation.planned_spending == Decimal("0.00")


def test_delete_expense_with_stale_version_is_rejected(
    budget_service: BudgetService,
    event,
    budget,
) -> None:
    added = add_expense(budget_service, str(event.event_id), 1)
    expense_id = str(added.expenses[0].expense_id)

    with pytest.raises(ResourceConflictError):
        budget_service.delete_expense(str(event.event_id), expense_id, 1)


def test_custom_category_and_invalid_expense_ids(
    budget_service: BudgetService,
    event,
    budget,
) -> None:
    view = add_expense(
        budget_service,
        str(event.event_id),
        1,
        category="Mehndi artists",
    )

    assert view.expenses[0].category == "Mehndi artists"
    with pytest.raises(ResourceNotFoundError):
        budget_service.delete_expense(str(event.event_id), "bad-id", 2)
