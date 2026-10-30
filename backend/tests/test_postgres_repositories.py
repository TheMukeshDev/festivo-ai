"""PostgreSQL repository SQL paths exercised against a scripted cursor.

Every statement the repositories issue is replayed from a queue, so conflict,
missing-row, and filter branches are covered without a live Supabase instance.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from psycopg.errors import ForeignKeyViolation, UniqueViolation

from app.core.exceptions import ResourceConflictError, ResourceNotFoundError
from app.models.budget import Budget, Expense, ExpenseStatus, ReserveType
from app.models.event import Event, EventType
from app.models.proposal import Proposal, ProposalStatus, ProposalType
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.timeline import Timeline
from app.models.vendor import Vendor, VendorCategory, VendorStatus
from app.repositories.postgres_budget_repository import PostgresBudgetRepository
from app.repositories.postgres_event_repository import PostgresEventRepository
from app.repositories.postgres_planning_repository import PostgresPlanningRepository
from app.repositories.postgres_proposal_repository import PostgresProposalRepository
from app.repositories.postgres_vendor_repository import PostgresVendorRepository
from tests.fakes import FakeDatabase

NOW = datetime(2030, 5, 15, 8, 0, tzinfo=UTC)
OWNER_ID = UUID("00000000-0000-0000-0000-0000000000aa")
EVENT_ID = UUID("00000000-0000-0000-0000-0000000000bb")
TIMELINE_ID = UUID("00000000-0000-0000-0000-0000000000cc")
TASK_ID = UUID("00000000-0000-0000-0000-0000000000dd")
VENDOR_ID = UUID("00000000-0000-0000-0000-0000000000ee")
BUDGET_ID = UUID("00000000-0000-0000-0000-0000000000ff")
EXPENSE_ID = UUID("00000000-0000-0000-0000-000000000010")
PROPOSAL_ID = UUID("00000000-0000-0000-0000-000000000011")


def event_row(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": EVENT_ID,
        "owner_id": OWNER_ID,
        "name": "Ananya and Rohan Wedding",
        "event_type": "wedding",
        "event_date": date(2030, 6, 15),
        "location": "Bengaluru",
        "guest_count": 150,
        "budget_amount": Decimal("750000.00"),
        "currency": "INR",
        "timezone": "Asia/Kolkata",
        "description": "A relaxed celebration.",
        "preferences": ["Pastel decor"],
        "event_constraints": ["No loud music"],
        "created_at": NOW,
        "updated_at": NOW,
    }
    row.update(overrides)
    return row


def vendor_row(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": VENDOR_ID,
        "event_id": EVENT_ID,
        "owner_id": OWNER_ID,
        "name": "Lotus Banquets",
        "category": "venue",
        "description": "Garden venue",
        "contact_name": "Priya",
        "email": "priya@example.com",
        "phone": "+91 90000 00000",
        "website_url": "https://example.com",
        "service_area": "Bengaluru",
        "price_min": Decimal("100000.00"),
        "price_max": Decimal("500000.00"),
        "currency": "INR",
        "estimated_cost": None,
        "quoted_cost": None,
        "final_cost": None,
        "pricing_notes": None,
        "status": "discovered",
        "rating": Decimal("4.50"),
        "notes": None,
        "availability": "Weekends",
        "created_at": NOW,
        "updated_at": NOW,
    }
    row.update(overrides)
    return row


def budget_row(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": BUDGET_ID,
        "event_id": EVENT_ID,
        "total_limit": Decimal("750000.00"),
        "currency": "INR",
        "reserve_type": "percentage",
        "reserve_value": Decimal("10.00"),
        "version": 1,
        "created_at": NOW,
        "updated_at": NOW,
    }
    row.update(overrides)
    return row


def expense_row(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": EXPENSE_ID,
        "budget_id": BUDGET_ID,
        "category": "Catering",
        "name": "Dinner buffet",
        "amount": Decimal("120000.00"),
        "amount_status": "estimated",
        "notes": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    row.update(overrides)
    return row


def proposal_row(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": PROPOSAL_ID,
        "event_id": EVENT_ID,
        "owner_id": OWNER_ID,
        "proposal_type": "ai_planning",
        "title": "Rebalance the decor budget",
        "summary": "Shift surplus from transport to decor.",
        "payload": {"actions": []},
        "status": "pending",
        "version": 1,
        "source_snapshot": {"budget_version": 1},
        "created_at": NOW,
        "updated_at": NOW,
        "expires_at": NOW,
        "approved_at": None,
        "rejected_at": None,
    }
    row.update(overrides)
    return row


def timeline_row(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": TIMELINE_ID,
        "event_id": EVENT_ID,
        "owner_id": OWNER_ID,
        "start_date": date(2030, 5, 20),
        "end_date": date(2030, 6, 15),
        "timezone": "Asia/Kolkata",
        "generated_at": NOW,
        "created_at": NOW,
        "updated_at": NOW,
    }
    row.update(overrides)
    return row


def task_row(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": TASK_ID,
        "event_id": EVENT_ID,
        "owner_id": OWNER_ID,
        "timeline_id": TIMELINE_ID,
        "template_key": "book_venue",
        "title": "Book the venue",
        "description": "Confirm the contract.",
        "status": "pending",
        "priority": "high",
        "due_at": NOW,
        "assigned_to": "Rohan",
        "estimated_cost": Decimal("200000.00"),
        "actual_cost": None,
        "currency": "INR",
        "sort_order": 1,
        "completed_at": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    row.update(overrides)
    return row


def make_event() -> Event:
    return Event(
        event_id=EVENT_ID,
        owner_id=OWNER_ID,
        name="Ananya and Rohan Wedding",
        event_type=EventType.WEDDING,
        event_date=date(2030, 6, 15),
        location="Bengaluru",
        guest_count=150,
        budget_amount=Decimal("750000.00"),
        currency="INR",
        timezone="Asia/Kolkata",
        description="A relaxed celebration.",
        preferences=("Pastel decor",),
        constraints=("No loud music",),
        created_at=NOW,
        updated_at=NOW,
    )


def make_vendor(**overrides: Any) -> Vendor:
    values: dict[str, Any] = {
        "vendor_id": VENDOR_ID,
        "event_id": EVENT_ID,
        "owner_id": OWNER_ID,
        "name": "Lotus Banquets",
        "category": VendorCategory.VENUE,
        "description": "Garden venue",
        "contact_name": "Priya",
        "email": "priya@example.com",
        "phone": "+91 90000 00000",
        "website_url": "https://example.com",
        "service_area": "Bengaluru",
        "price_min": Decimal("100000.00"),
        "price_max": Decimal("500000.00"),
        "currency": "INR",
        "estimated_cost": None,
        "quoted_cost": None,
        "final_cost": None,
        "pricing_notes": None,
        "status": VendorStatus.DISCOVERED,
        "rating": Decimal("4.50"),
        "notes": None,
        "availability": "Weekends",
        "created_at": NOW,
        "updated_at": NOW,
    }
    values.update(overrides)
    return Vendor(**values)


def make_budget(version: int = 1) -> Budget:
    return Budget(
        budget_id=BUDGET_ID,
        event_id=EVENT_ID,
        total_limit=Decimal("750000.00"),
        currency="INR",
        reserve_type=ReserveType.PERCENTAGE,
        reserve_value=Decimal("10.00"),
        version=version,
        created_at=NOW,
        updated_at=NOW,
    )


def make_expense() -> Expense:
    return Expense(
        expense_id=EXPENSE_ID,
        budget_id=BUDGET_ID,
        category="Catering",
        name="Dinner buffet",
        amount=Decimal("120000.00"),
        amount_status=ExpenseStatus.ESTIMATED,
        notes=None,
        created_at=NOW,
        updated_at=NOW,
    )


def make_proposal() -> Proposal:
    return Proposal(
        proposal_id=PROPOSAL_ID,
        event_id=EVENT_ID,
        owner_id=OWNER_ID,
        proposal_type=ProposalType.AI_PLANNING,
        title="Rebalance the decor budget",
        summary="Shift surplus from transport to decor.",
        payload={"actions": []},
        status=ProposalStatus.PENDING,
        version=1,
        source_snapshot={"budget_version": 1},
        created_at=NOW,
        updated_at=NOW,
        expires_at=NOW,
    )


def make_timeline() -> Timeline:
    return Timeline(
        timeline_id=TIMELINE_ID,
        event_id=EVENT_ID,
        owner_id=OWNER_ID,
        start_date=date(2030, 5, 20),
        end_date=date(2030, 6, 15),
        timezone="Asia/Kolkata",
        generated_at=NOW,
        created_at=NOW,
        updated_at=NOW,
    )


def make_task() -> Task:
    return Task(
        task_id=TASK_ID,
        event_id=EVENT_ID,
        owner_id=OWNER_ID,
        timeline_id=TIMELINE_ID,
        template_key="book_venue",
        title="Book the venue",
        description="Confirm the contract.",
        status=TaskStatus.PENDING,
        priority=TaskPriority.HIGH,
        due_at=NOW,
        assigned_to="Rohan",
        estimated_cost=Decimal("200000.00"),
        actual_cost=None,
        currency="INR",
        sort_order=1,
        completed_at=None,
        created_at=NOW,
        updated_at=NOW,
    )


class TestPostgresEventRepository:
    def test_save_returns_the_inserted_event(self) -> None:
        database = FakeDatabase().queue(event_row())
        repository = PostgresEventRepository(database)

        saved = repository.save(make_event())

        assert saved.event_id == EVENT_ID
        assert saved.preferences == ("Pastel decor",)
        assert database.executed_sql[0].startswith("INSERT INTO public.events")

    def test_save_translates_a_duplicate_identifier(self) -> None:
        database = FakeDatabase().queue(UniqueViolation())
        repository = PostgresEventRepository(database)

        with pytest.raises(ResourceConflictError):
            repository.save(make_event())

    def test_save_rejects_an_insert_without_a_returning_row(self) -> None:
        database = FakeDatabase().queue(None)
        repository = PostgresEventRepository(database)

        with pytest.raises(RuntimeError, match="returned no row"):
            repository.save(make_event())

    def test_get_returns_none_when_the_event_is_absent(self) -> None:
        database = FakeDatabase().queue(None)
        repository = PostgresEventRepository(database)

        assert repository.get(EVENT_ID, OWNER_ID) is None

    def test_list_returns_rows_and_the_matching_total(self) -> None:
        database = FakeDatabase().queue({"total": 1}, [event_row()])
        repository = PostgresEventRepository(database)

        events, total = repository.list(OWNER_ID, limit=10, offset=0)

        assert total == 1
        assert [item.name for item in events] == ["Ananya and Rohan Wedding"]

    def test_list_treats_a_missing_count_as_zero(self) -> None:
        database = FakeDatabase().queue(None, [])
        repository = PostgresEventRepository(database)

        events, total = repository.list(OWNER_ID, limit=10, offset=0)

        assert (events, total) == ([], 0)

    def test_update_returns_none_for_a_foreign_event(self) -> None:
        database = FakeDatabase().queue(None)
        repository = PostgresEventRepository(database)

        assert repository.update(uuid4(), make_event()) is None

    def test_delete_reports_whether_a_row_was_removed(self) -> None:
        database = FakeDatabase().queue({"id": EVENT_ID}, None)
        repository = PostgresEventRepository(database)

        assert repository.delete(EVENT_ID, OWNER_ID) is True
        assert repository.delete(EVENT_ID, OWNER_ID) is False


class TestPostgresVendorRepository:
    def test_create_returns_the_inserted_vendor(self) -> None:
        database = FakeDatabase().queue(vendor_row())
        repository = PostgresVendorRepository(database)

        created = repository.create(make_vendor())

        assert created.category is VendorCategory.VENUE
        assert database.executed_sql[0].startswith("INSERT INTO public.event_vendors")

    def test_create_rejects_an_insert_without_a_returning_row(self) -> None:
        database = FakeDatabase().queue(None)
        repository = PostgresVendorRepository(database)

        with pytest.raises(RuntimeError, match="returned no row"):
            repository.create(make_vendor())

    def test_get_returns_none_for_an_unknown_vendor(self) -> None:
        database = FakeDatabase().queue(None)
        repository = PostgresVendorRepository(database)

        assert repository.get(VENDOR_ID, EVENT_ID, OWNER_ID) is None

    def test_list_filters_in_sql_and_returns_the_total(self) -> None:
        database = FakeDatabase().queue({"total": 1}, [vendor_row()])
        repository = PostgresVendorRepository(database)

        vendors, total = repository.list(
            OWNER_ID,
            EVENT_ID,
            category=VendorCategory.VENUE,
            status=VendorStatus.SHORTLISTED,
            min_price=None,
            max_price=None,
            name_query="lotus",
            limit=10,
            offset=0,
        )

        assert total == 1
        assert vendors[0].name == "Lotus Banquets"
        count_sql = database.executed_sql[0]
        assert "category = %s" in count_sql
        assert "status = %s" in count_sql
        assert "lower(name) LIKE %s" in count_sql

    def test_list_price_filter_applies_python_side(self) -> None:
        rows = [
            vendor_row(id=uuid4(), quoted_cost=Decimal("5000.00")),
            vendor_row(
                id=uuid4(),
                quoted_cost=None,
                estimated_cost=Decimal("3000.00"),
            ),
            vendor_row(
                id=uuid4(),
                quoted_cost=None,
                estimated_cost=None,
                price_min=Decimal("4000.00"),
            ),
            vendor_row(
                id=uuid4(),
                quoted_cost=None,
                estimated_cost=None,
                price_min=None,
            ),
            vendor_row(id=uuid4(), quoted_cost=Decimal("1000.00")),
        ]
        database = FakeDatabase().queue({"total": 5}, rows)
        repository = PostgresVendorRepository(database)

        vendors, total = repository.list(
            OWNER_ID,
            EVENT_ID,
            category=None,
            status=None,
            min_price=2500.0,
            max_price=8000.0,
            name_query=None,
            limit=10,
            offset=0,
        )

        assert total == 3
        assert len(vendors) == 3

    def test_list_price_filter_rejects_prices_above_the_maximum(self) -> None:
        rows = [
            vendor_row(id=uuid4(), quoted_cost=Decimal("9000.00")),
            vendor_row(id=uuid4(), quoted_cost=Decimal("1000.00")),
        ]
        database = FakeDatabase().queue({"total": 2}, rows)
        repository = PostgresVendorRepository(database)

        vendors, total = repository.list(
            OWNER_ID,
            EVENT_ID,
            category=None,
            status=None,
            min_price=None,
            max_price=8000.0,
            name_query=None,
            limit=10,
            offset=0,
        )

        assert (len(vendors), total) == (1, 1)

    def test_list_treats_a_missing_count_as_zero(self) -> None:
        database = FakeDatabase().queue(None, [])
        repository = PostgresVendorRepository(database)

        vendors, total = repository.list(
            OWNER_ID,
            EVENT_ID,
            category=None,
            status=None,
            min_price=None,
            max_price=None,
            name_query=None,
            limit=10,
            offset=0,
        )

        assert (vendors, total) == ([], 0)

    def test_update_returns_none_for_a_foreign_vendor(self) -> None:
        database = FakeDatabase().queue(None)
        repository = PostgresVendorRepository(database)

        assert repository.update(uuid4(), make_vendor()) is None

    def test_delete_reports_whether_a_row_was_removed(self) -> None:
        database = FakeDatabase().queue({"id": VENDOR_ID}, None)
        repository = PostgresVendorRepository(database)

        assert repository.delete(VENDOR_ID, EVENT_ID, OWNER_ID) is True
        assert repository.delete(VENDOR_ID, EVENT_ID, OWNER_ID) is False


class TestPostgresBudgetRepository:
    def test_create_returns_an_expense_free_aggregate(self) -> None:
        database = FakeDatabase().queue(budget_row())
        repository = PostgresBudgetRepository(database)

        aggregate = repository.create(make_budget())

        assert aggregate.budget.version == 1
        assert aggregate.expenses == ()

    def test_create_translates_duplicate_and_foreign_key_violations(self) -> None:
        conflict = PostgresBudgetRepository(FakeDatabase().queue(UniqueViolation()))
        with pytest.raises(ResourceConflictError):
            conflict.create(make_budget())

        missing = PostgresBudgetRepository(FakeDatabase().queue(ForeignKeyViolation()))
        with pytest.raises(ResourceNotFoundError):
            missing.create(make_budget())

    def test_create_rejects_an_insert_without_a_returning_row(self) -> None:
        repository = PostgresBudgetRepository(FakeDatabase().queue(None))

        with pytest.raises(RuntimeError, match="returned no row"):
            repository.create(make_budget())

    def test_get_by_event_returns_none_when_absent(self) -> None:
        repository = PostgresBudgetRepository(FakeDatabase().queue(None))

        assert repository.get_by_event(EVENT_ID) is None

    def test_get_by_event_loads_expenses(self) -> None:
        database = FakeDatabase().queue(budget_row(), [expense_row()])
        repository = PostgresBudgetRepository(database)

        aggregate = repository.get_by_event(EVENT_ID)

        assert aggregate is not None
        assert aggregate.expenses[0].name == "Dinner buffet"

    def test_update_budget_returns_the_versioned_aggregate(self) -> None:
        database = FakeDatabase().queue(
            budget_row(version=1),
            budget_row(version=2),
            [expense_row()],
        )
        repository = PostgresBudgetRepository(database)

        aggregate = repository.update_budget(
            BUDGET_ID,
            1,
            total_limit=Decimal("800000.00"),
            reserve_type=ReserveType.FIXED_AMOUNT,
            reserve_value=Decimal("50000.00"),
            updated_at=NOW,
        )

        assert aggregate.budget.version == 2
        assert len(aggregate.expenses) == 1

    def test_update_budget_translates_lock_failures(self) -> None:
        missing = PostgresBudgetRepository(FakeDatabase().queue(None))
        with pytest.raises(ResourceNotFoundError):
            missing.update_budget(
                BUDGET_ID,
                1,
                total_limit=Decimal("1.00"),
                reserve_type=ReserveType.FIXED_AMOUNT,
                reserve_value=Decimal("1.00"),
                updated_at=NOW,
            )

        stale = PostgresBudgetRepository(FakeDatabase().queue(budget_row(version=9)))
        with pytest.raises(ResourceConflictError):
            stale.update_budget(
                BUDGET_ID,
                1,
                total_limit=Decimal("1.00"),
                reserve_type=ReserveType.FIXED_AMOUNT,
                reserve_value=Decimal("1.00"),
                updated_at=NOW,
            )

    def test_update_budget_translates_a_missing_returning_row(self) -> None:
        repository = PostgresBudgetRepository(FakeDatabase().queue(budget_row(version=1), None))

        with pytest.raises(ResourceNotFoundError):
            repository.update_budget(
                BUDGET_ID,
                1,
                total_limit=Decimal("1.00"),
                reserve_type=ReserveType.FIXED_AMOUNT,
                reserve_value=Decimal("1.00"),
                updated_at=NOW,
            )

    def test_add_expense_returns_the_versioned_aggregate(self) -> None:
        database = FakeDatabase().queue(
            budget_row(version=1),
            expense_row(),
            budget_row(version=2),
            [expense_row()],
        )
        repository = PostgresBudgetRepository(database)

        aggregate = repository.add_expense(
            BUDGET_ID,
            1,
            expense=make_expense(),
            updated_at=NOW,
        )

        assert aggregate.budget.version == 2
        assert aggregate.expenses[0].expense_id == EXPENSE_ID

    def test_add_expense_translates_insert_and_version_failures(self) -> None:
        empty_insert = PostgresBudgetRepository(FakeDatabase().queue(budget_row(version=1), None))
        with pytest.raises(RuntimeError, match="returned no row"):
            empty_insert.add_expense(
                BUDGET_ID,
                1,
                expense=make_expense(),
                updated_at=NOW,
            )

        missing_version = PostgresBudgetRepository(
            FakeDatabase().queue(budget_row(version=1), expense_row(), None)
        )
        with pytest.raises(ResourceNotFoundError):
            missing_version.add_expense(
                BUDGET_ID,
                1,
                expense=make_expense(),
                updated_at=NOW,
            )

    def test_update_expense_returns_the_versioned_aggregate(self) -> None:
        database = FakeDatabase().queue(
            budget_row(version=1),
            expense_row(),
            budget_row(version=2),
            [expense_row()],
        )
        repository = PostgresBudgetRepository(database)

        aggregate = repository.update_expense(
            BUDGET_ID,
            EXPENSE_ID,
            1,
            expense=make_expense(),
            updated_at=NOW,
        )

        assert aggregate.budget.version == 2

    def test_update_expense_translates_a_missing_expense(self) -> None:
        repository = PostgresBudgetRepository(FakeDatabase().queue(budget_row(version=1), None))

        with pytest.raises(ResourceNotFoundError):
            repository.update_expense(
                BUDGET_ID,
                EXPENSE_ID,
                1,
                expense=make_expense(),
                updated_at=NOW,
            )

    def test_delete_expense_returns_the_versioned_aggregate(self) -> None:
        database = FakeDatabase().queue(
            budget_row(version=1),
            {"id": EXPENSE_ID},
            budget_row(version=2),
            [],
        )
        repository = PostgresBudgetRepository(database)

        aggregate = repository.delete_expense(
            BUDGET_ID,
            EXPENSE_ID,
            1,
            updated_at=NOW,
        )

        assert aggregate.budget.version == 2
        assert aggregate.expenses == ()

    def test_delete_expense_translates_missing_rows(self) -> None:
        absent = PostgresBudgetRepository(FakeDatabase().queue(budget_row(version=1), None))
        with pytest.raises(ResourceNotFoundError):
            absent.delete_expense(BUDGET_ID, EXPENSE_ID, 1, updated_at=NOW)

        vanishing = PostgresBudgetRepository(
            FakeDatabase().queue(budget_row(version=1), {"id": EXPENSE_ID}, None)
        )
        with pytest.raises(ResourceNotFoundError):
            vanishing.delete_expense(BUDGET_ID, EXPENSE_ID, 1, updated_at=NOW)


class TestPostgresProposalRepository:
    def test_create_returns_the_inserted_proposal(self) -> None:
        database = FakeDatabase().queue(proposal_row())
        repository = PostgresProposalRepository(database)

        created = repository.create(make_proposal())

        assert created.status is ProposalStatus.PENDING
        assert created.payload == {"actions": []}
        assert database.executed_sql[0].startswith("INSERT INTO public.planning_proposals")

    def test_create_translates_a_duplicate_identifier(self) -> None:
        repository = PostgresProposalRepository(FakeDatabase().queue(UniqueViolation()))

        with pytest.raises(ResourceConflictError):
            repository.create(make_proposal())

    def test_create_rejects_an_insert_without_a_returning_row(self) -> None:
        repository = PostgresProposalRepository(FakeDatabase().queue(None))

        with pytest.raises(RuntimeError, match="returned no row"):
            repository.create(make_proposal())

    def test_get_returns_none_for_an_unknown_proposal(self) -> None:
        repository = PostgresProposalRepository(FakeDatabase().queue(None))

        assert repository.get(PROPOSAL_ID, EVENT_ID, OWNER_ID) is None

    def test_list_filters_by_status(self) -> None:
        database = FakeDatabase().queue({"total": 1}, [proposal_row()])
        repository = PostgresProposalRepository(database)

        proposals, total = repository.list(
            OWNER_ID,
            EVENT_ID,
            status=ProposalStatus.APPROVED,
            limit=10,
            offset=0,
        )

        assert total == 1
        assert proposals[0].proposal_id == PROPOSAL_ID
        assert "status = %s" in database.executed_sql[0]

    def test_list_treats_a_missing_count_as_zero(self) -> None:
        repository = PostgresProposalRepository(FakeDatabase().queue(None, []))

        proposals, total = repository.list(
            OWNER_ID,
            EVENT_ID,
            status=None,
            limit=10,
            offset=0,
        )

        assert (proposals, total) == ([], 0)

    def test_update_returns_none_when_the_version_is_stale(self) -> None:
        repository = PostgresProposalRepository(FakeDatabase().queue(None))

        assert repository.update(OWNER_ID, make_proposal(), expected_version=3) is None


class TestPostgresPlanningRepository:
    def test_create_timeline_inserts_tasks(self) -> None:
        database = FakeDatabase().queue(timeline_row(), None)
        repository = PostgresPlanningRepository(database)

        timeline = repository.create_timeline(make_timeline(), [make_task()])

        assert timeline.timeline_id == TIMELINE_ID
        assert len(database.executed_sql) == 2
        assert database.executed_sql[1].startswith("INSERT INTO public.event_tasks")

    def test_create_timeline_translates_a_duplicate_timeline(self) -> None:
        repository = PostgresPlanningRepository(FakeDatabase().queue(UniqueViolation()))

        with pytest.raises(ResourceConflictError):
            repository.create_timeline(make_timeline(), [])

    def test_create_timeline_rejects_an_insert_without_a_returning_row(self) -> None:
        repository = PostgresPlanningRepository(FakeDatabase().queue(None))

        with pytest.raises(RuntimeError, match="returned no row"):
            repository.create_timeline(make_timeline(), [])

    def test_get_timeline_returns_none_when_absent(self) -> None:
        repository = PostgresPlanningRepository(FakeDatabase().queue(None))

        assert repository.get_timeline(EVENT_ID, OWNER_ID) is None

    def test_update_timeline_returns_none_for_a_foreign_timeline(self) -> None:
        repository = PostgresPlanningRepository(FakeDatabase().queue(None))

        assert repository.update_timeline(uuid4(), make_timeline()) is None

    def test_add_generated_tasks_reports_only_new_rows(self) -> None:
        database = FakeDatabase().queue(timeline_row(), task_row())
        repository = PostgresPlanningRepository(database)

        timeline, added = repository.add_generated_tasks(
            OWNER_ID,
            make_timeline(),
            [make_task()],
            generated_at=NOW,
        )

        assert timeline.timeline_id == TIMELINE_ID
        assert [item.task_id for item in added] == [TASK_ID]

    def test_add_generated_tasks_skips_conflicting_rows(self) -> None:
        database = FakeDatabase().queue(timeline_row(), None)
        repository = PostgresPlanningRepository(database)

        _, added = repository.add_generated_tasks(
            OWNER_ID,
            make_timeline(),
            [make_task()],
            generated_at=NOW,
        )

        assert added == []

    def test_add_generated_tasks_translates_a_missing_timeline(self) -> None:
        repository = PostgresPlanningRepository(FakeDatabase().queue(None))

        with pytest.raises(ResourceNotFoundError):
            repository.add_generated_tasks(
                OWNER_ID,
                make_timeline(),
                [],
                generated_at=NOW,
            )

    def test_get_task_by_template_key_returns_none_when_absent(self) -> None:
        repository = PostgresPlanningRepository(FakeDatabase().queue(None))

        assert repository.get_task_by_template_key(OWNER_ID, EVENT_ID, "book_venue") is None

    def test_create_task_translates_conflicts_and_empty_inserts(self) -> None:
        conflicting = PostgresPlanningRepository(FakeDatabase().queue(UniqueViolation()))
        with pytest.raises(ResourceConflictError):
            conflicting.create_task(make_task())

        empty = PostgresPlanningRepository(FakeDatabase().queue(None))
        with pytest.raises(RuntimeError, match="returned no row"):
            empty.create_task(make_task())

    def test_create_task_returns_the_inserted_task(self) -> None:
        repository = PostgresPlanningRepository(FakeDatabase().queue(task_row()))

        created = repository.create_task(make_task())

        assert created.task_id == TASK_ID

    def test_get_task_returns_none_when_absent(self) -> None:
        repository = PostgresPlanningRepository(FakeDatabase().queue(None))

        assert repository.get_task(TASK_ID, EVENT_ID, OWNER_ID) is None

    def test_update_task_returns_none_for_a_foreign_task(self) -> None:
        repository = PostgresPlanningRepository(FakeDatabase().queue(None))

        assert repository.update_task(uuid4(), make_task()) is None

    def test_delete_task_reports_whether_a_row_was_removed(self) -> None:
        repository = PostgresPlanningRepository(FakeDatabase().queue({"id": TASK_ID}, None))

        assert repository.delete_task(TASK_ID, EVENT_ID, OWNER_ID) is True
        assert repository.delete_task(TASK_ID, EVENT_ID, OWNER_ID) is False

    def test_list_tasks_applies_filters_and_totals(self) -> None:
        database = FakeDatabase().queue({"total": 1}, [task_row()])
        repository = PostgresPlanningRepository(database)

        tasks, total = repository.list_tasks(
            OWNER_ID,
            EVENT_ID,
            status=TaskStatus.PENDING,
            priority=TaskPriority.HIGH,
            timeline_id=TIMELINE_ID,
            limit=10,
            offset=0,
        )

        assert total == 1
        assert tasks[0].title == "Book the venue"
        count_sql = database.executed_sql[0]
        assert "status = %s" in count_sql
        assert "priority = %s" in count_sql
        assert "timeline_id = %s" in count_sql

    def test_list_tasks_treats_a_missing_count_as_zero(self) -> None:
        repository = PostgresPlanningRepository(FakeDatabase().queue(None, []))

        tasks, total = repository.list_tasks(
            OWNER_ID,
            EVENT_ID,
            status=None,
            priority=None,
            timeline_id=None,
            limit=10,
            offset=0,
        )

        assert (tasks, total) == ([], 0)

    def test_list_timeline_tasks_returns_rows_in_order(self) -> None:
        database = FakeDatabase().queue([task_row()])
        repository = PostgresPlanningRepository(database)

        tasks = repository.list_timeline_tasks(OWNER_ID, EVENT_ID, TIMELINE_ID)

        assert [item.task_id for item in tasks] == [TASK_ID]
