"""Edge-case coverage for in-memory repositories and repository races."""

from dataclasses import replace
from uuid import uuid4

import pytest

from app.core.exceptions import ResourceConflictError, ResourceNotFoundError
from app.models.budget import ReserveType
from app.models.vendor import VendorCategory, VendorStatus
from app.repositories.event_repository import InMemoryEventRepository
from app.repositories.memory_budget_repository import InMemoryBudgetRepository
from app.repositories.memory_planning_repository import InMemoryPlanningRepository
from app.repositories.memory_proposal_repository import InMemoryProposalRepository
from app.repositories.memory_vendor_repository import InMemoryVendorRepository
from tests.test_postgres_repositories import (
    EVENT_ID,
    NOW,
    OWNER_ID,
    TIMELINE_ID,
    make_budget,
    make_event,
    make_expense,
    make_proposal,
    make_task,
    make_timeline,
    make_vendor,
)


def test_event_repository_update_returns_none_for_an_unknown_event() -> None:
    repository = InMemoryEventRepository()

    assert repository.update(OWNER_ID, make_event()) is None


def test_budget_repository_rejects_duplicates_and_missing_records() -> None:
    repository = InMemoryBudgetRepository()
    budget = make_budget()
    repository.create(budget)

    with pytest.raises(ResourceConflictError):
        repository.create(budget)

    with pytest.raises(ResourceNotFoundError):
        repository.add_expense(
            budget.budget_id,
            1,
            expense=replace(make_expense(), budget_id=uuid4()),
            updated_at=NOW,
        )

    expense = make_expense()
    repository.add_expense(budget.budget_id, 1, expense=expense, updated_at=NOW)
    with pytest.raises(ResourceConflictError):
        repository.add_expense(budget.budget_id, 2, expense=expense, updated_at=NOW)

    with pytest.raises(ResourceNotFoundError):
        repository.update_expense(
            budget.budget_id,
            uuid4(),
            2,
            expense=make_expense(),
            updated_at=NOW,
        )

    with pytest.raises(ResourceNotFoundError):
        repository.update_budget(
            uuid4(),
            1,
            total_limit=budget.total_limit,
            reserve_type=ReserveType.PERCENTAGE,
            reserve_value=budget.reserve_value,
            updated_at=NOW,
        )


def test_planning_repository_covers_all_lifecycle_guards() -> None:
    repository = InMemoryPlanningRepository()
    timeline = make_timeline()
    repository.create_timeline(timeline, [])

    with pytest.raises(ResourceConflictError):
        repository.create_timeline(make_timeline(), [])

    assert (
        repository.update_timeline(OWNER_ID, replace(make_timeline(), timeline_id=uuid4())) is None
    )
    assert repository.update_timeline(uuid4(), timeline) is None
    assert repository.update_timeline(OWNER_ID, replace(timeline, event_id=uuid4())) is None
    updated = repository.update_timeline(OWNER_ID, replace(timeline, timezone="UTC"))
    assert updated is not None

    with pytest.raises(ResourceNotFoundError):
        InMemoryPlanningRepository().add_generated_tasks(
            OWNER_ID, make_timeline(), [], generated_at=NOW
        )

    generated = [
        replace(make_task(), task_id=uuid4(), template_key=None),
        replace(make_task(), task_id=uuid4(), template_key="new"),
        replace(make_task(), task_id=uuid4(), template_key="new"),
    ]
    _, added = repository.add_generated_tasks(OWNER_ID, timeline, generated, generated_at=NOW)
    assert len(added) == 2

    found = repository.get_task_by_template_key(OWNER_ID, EVENT_ID, "new")
    assert found is not None
    assert repository.get_task_by_template_key(OWNER_ID, EVENT_ID, "missing") is None


def test_planning_repository_task_guards_and_lists() -> None:
    repository = InMemoryPlanningRepository()
    repository.create_timeline(make_timeline(), [])

    first = replace(make_task(), task_id=uuid4())
    repository.create_task(first)
    with pytest.raises(ResourceConflictError):
        repository.create_task(replace(make_task(), task_id=uuid4()))

    assert repository.update_task(OWNER_ID, replace(make_task(), task_id=uuid4())) is None
    assert repository.delete_task(uuid4(), EVENT_ID, OWNER_ID) is False
    assert [
        task.task_id for task in repository.list_timeline_tasks(OWNER_ID, EVENT_ID, TIMELINE_ID)
    ] == [first.task_id]

    with pytest.raises(ResourceNotFoundError):
        repository.create_task(
            replace(
                make_task(),
                task_id=uuid4(),
                template_key=None,
                timeline_id=uuid4(),
            )
        )


def test_proposal_repository_update_returns_none_for_a_stale_version() -> None:
    repository = InMemoryProposalRepository()
    repository.create(make_proposal())

    assert repository.update(OWNER_ID, make_proposal(), expected_version=2) is None


def test_vendor_repository_filters_and_guard_branches() -> None:
    repository = InMemoryVendorRepository()
    vendors = [
        make_vendor(owner_id=uuid4(), vendor_id=uuid4()),
        make_vendor(category=VendorCategory.CATERING, vendor_id=uuid4()),
        make_vendor(status=VendorStatus.CONTACTED, vendor_id=uuid4()),
        make_vendor(name="Other Hall", vendor_id=uuid4()),
        make_vendor(
            vendor_id=uuid4(),
            name="Lotus Venue No Price",
            quoted_cost=None,
            estimated_cost=None,
            price_min=None,
            price_max=None,
        ),
        make_vendor(
            vendor_id=uuid4(),
            name="Lotus Venue Cheap",
            quoted_cost=500,
            estimated_cost=None,
            price_min=None,
            price_max=None,
        ),
        make_vendor(
            vendor_id=uuid4(),
            name="Lotus Venue Expensive",
            quoted_cost=6000,
            estimated_cost=None,
            price_min=None,
            price_max=None,
        ),
        make_vendor(
            vendor_id=uuid4(),
            name="Lotus Venue Prime",
            status=VendorStatus.SHORTLISTED,
            quoted_cost=3000,
            estimated_cost=None,
            price_min=None,
            price_max=None,
        ),
    ]
    for vendor in vendors:
        repository.create(vendor)

    matched, total = repository.list(
        OWNER_ID,
        EVENT_ID,
        category=VendorCategory.VENUE,
        status=VendorStatus.SHORTLISTED,
        min_price=1000,
        max_price=5000,
        name_query="lotus venue",
        limit=10,
        offset=0,
    )

    assert total == 1
    assert matched[0].name == "Lotus Venue Prime"

    assert repository.update(OWNER_ID, make_vendor(vendor_id=uuid4())) is None
    assert repository.delete(uuid4(), EVENT_ID, OWNER_ID) is False
    foreign = make_vendor(vendor_id=uuid4())
    repository.create(foreign)
    assert repository.delete(foreign.vendor_id, EVENT_ID, uuid4()) is False
    assert repository.delete(foreign.vendor_id, EVENT_ID, OWNER_ID) is True


def test_vendor_repository_filter_rejections_cover_each_predicate() -> None:
    repository = InMemoryVendorRepository()
    repository.create(
        make_vendor(name="Other Hall", status=VendorStatus.SHORTLISTED, vendor_id=uuid4())
    )
    repository.create(
        make_vendor(
            name="Lotus Free",
            status=VendorStatus.SHORTLISTED,
            vendor_id=uuid4(),
            quoted_cost=None,
            estimated_cost=None,
            price_min=None,
            price_max=None,
        )
    )
    repository.create(
        make_vendor(
            name="Lotus Cheap",
            status=VendorStatus.SHORTLISTED,
            vendor_id=uuid4(),
            quoted_cost=500,
            estimated_cost=None,
            price_min=None,
            price_max=None,
        )
    )
    repository.create(
        make_vendor(
            name="Lotus Prime",
            status=VendorStatus.SHORTLISTED,
            vendor_id=uuid4(),
            quoted_cost=6000,
            estimated_cost=None,
            price_min=None,
            price_max=None,
        )
    )

    def query(*, name_query: str, min_price: float | None = None, max_price: float | None = None):
        return repository.list(
            OWNER_ID,
            EVENT_ID,
            category=VendorCategory.VENUE,
            status=VendorStatus.SHORTLISTED,
            min_price=min_price,
            max_price=max_price,
            name_query=name_query,
            limit=10,
            offset=0,
        )

    assert query(name_query="lotus")[1] == 3
    assert query(name_query="lotus free", min_price=1000) == ([], 0)
    assert query(name_query="lotus free", max_price=5000) == ([], 0)
    assert query(name_query="lotus cheap", min_price=1000) == ([], 0)
    assert query(name_query="lotus prime", max_price=1000) == ([], 0)
