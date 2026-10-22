"""PostgreSQL failure translation and optional live integration coverage."""

import os
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import SecretStr

from app.core.exceptions import ResourceConflictError, StorageUnavailableError
from app.db.postgres import PostgresDatabase
from app.models.budget import Budget, Expense, ExpenseStatus, ReserveType
from app.models.event import Event, EventType
from app.repositories.postgres_budget_repository import PostgresBudgetRepository
from app.repositories.postgres_event_repository import PostgresEventRepository

INTEGRATION_ENV = "TEST_SUPABASE_DB_URL"


def test_connection_failures_are_translated_without_exposing_the_dsn() -> None:
    secret = "super-secret-database-password"
    database = PostgresDatabase(
        SecretStr(f"postgresql://festivo:{secret}@127.0.0.1:1/festivo_test"),
        1,
    )

    with pytest.raises(StorageUnavailableError) as error, database.connection():
        pass

    assert secret not in str(error.value)
    assert "127.0.0.1" not in str(error.value)


@pytest.mark.skipif(
    not os.getenv(INTEGRATION_ENV),
    reason=f"{INTEGRATION_ENV} is not configured; live Supabase integration not tested.",
)
def test_live_postgres_event_and_budget_lifecycle() -> None:
    database = PostgresDatabase(SecretStr(os.environ[INTEGRATION_ENV]), 10)
    event_repository = PostgresEventRepository(database)
    budget_repository = PostgresBudgetRepository(database)
    now = datetime.now(UTC)
    event = Event(
        event_id=uuid4(),
        name="Integration test event",
        event_type=EventType.WEDDING,
        event_date=date(2030, 6, 15),
        location="Test location",
        guest_count=10,
        budget_amount=Decimal("1000.00"),
        currency="INR",
        description=None,
        preferences=("Integration",),
        constraints=("Delete after test",),
        created_at=now,
        updated_at=now,
    )
    budget = Budget(
        budget_id=uuid4(),
        event_id=event.event_id,
        total_limit=Decimal("1000.00"),
        currency="INR",
        reserve_type=ReserveType.PERCENTAGE,
        reserve_value=Decimal("10.00"),
        version=1,
        created_at=now,
        updated_at=now,
    )
    expense = Expense(
        expense_id=uuid4(),
        budget_id=budget.budget_id,
        category="Miscellaneous",
        name="Integration expense",
        amount=Decimal("100.00"),
        amount_status=ExpenseStatus.ESTIMATED,
        notes=None,
        created_at=now,
        updated_at=now,
    )

    try:
        assert event_repository.save(event) == event
        assert event_repository.get(event.event_id) == event
        listed, total = event_repository.list(limit=10, offset=0)
        assert event.event_id in {item.event_id for item in listed}
        assert total >= 1

        aggregate = budget_repository.create(budget)
        assert aggregate.budget == budget
        assert aggregate.expenses == ()

        aggregate = budget_repository.add_expense(
            budget.budget_id,
            1,
            expense=expense,
            updated_at=now,
        )
        assert aggregate.budget.version == 2
        assert aggregate.expenses == (expense,)

        fetched = budget_repository.get_by_event(event.event_id)
        assert fetched == aggregate

        with pytest.raises(ResourceConflictError):
            budget_repository.delete_expense(
                budget.budget_id,
                expense.expense_id,
                1,
                updated_at=now,
            )

        deleted = budget_repository.delete_expense(
            budget.budget_id,
            expense.expense_id,
            2,
            updated_at=now,
        )
        assert deleted.budget.version == 3
        assert deleted.expenses == ()
    finally:
        event_repository.delete(event.event_id)

    assert budget_repository.get_by_event(event.event_id) is None
