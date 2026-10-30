"""Branch coverage for task and vendor workflow services plus small service orphans."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest

from app.core.exceptions import (
    DomainValidationError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.models.event import Event
from app.models.task import TaskPriority
from app.repositories.memory_proposal_repository import InMemoryProposalRepository
from app.repositories.memory_vendor_repository import InMemoryVendorRepository
from app.schemas.event import EventCreate, EventUpdate
from app.schemas.task import TaskCreate, TaskUpdate
from app.schemas.vendor import VendorCompareRequest, VendorCreate, VendorUpdate
from app.services.budget_service import BudgetService
from app.services.event_service import EventService
from app.services.planning_orchestration_service import PlanningOrchestrationService
from app.services.proposal_service import ProposalService
from app.services.task_service import TaskService
from app.services.timeline_service import TimelineService
from app.services.vendor_service import VendorService
from tests.conftest import TEST_USER_ID, MutableClock

EventFactory = Callable[..., dict[str, Any]]


@pytest.fixture
def owner_event(
    event_service: EventService,
    event_payload: EventFactory,
) -> Event:
    return event_service.create(TEST_USER_ID, EventCreate(**event_payload()))


@pytest.fixture
def vendor_service(
    event_repository: Any,
    event_service: EventService,
    task_service: TaskService,
    clock: MutableClock,
) -> VendorService:
    return VendorService(
        event_repository,
        InMemoryVendorRepository(),
        event_service,
        task_service,
        clock,
    )


# --- task service ---------------------------------------------------------------


def test_task_update_reports_missing_task(
    task_service: TaskService,
    owner_event: Event,
) -> None:
    with pytest.raises(ResourceNotFoundError):
        task_service.update(
            TEST_USER_ID,
            str(owner_event.event_id),
            str(uuid4()),
            TaskUpdate(priority="high"),
        )


def test_task_update_rejects_null_required_fields(
    task_service: TaskService,
    owner_event: Event,
) -> None:
    task = task_service.create(
        TEST_USER_ID, str(owner_event.event_id), TaskCreate(title="Call the venue")
    )

    with pytest.raises(DomainValidationError):
        task_service.update(
            TEST_USER_ID,
            str(owner_event.event_id),
            str(task.task_id),
            TaskUpdate(title=None),
        )


def test_task_update_without_changes_is_a_no_op(
    task_service: TaskService,
    owner_event: Event,
) -> None:
    task = task_service.create(
        TEST_USER_ID, str(owner_event.event_id), TaskCreate(title="Call the venue")
    )

    unchanged = task_service.update(
        TEST_USER_ID,
        str(owner_event.event_id),
        str(task.task_id),
        TaskUpdate(),
    )

    assert unchanged.task_id == task.task_id


def test_task_update_with_identical_values_is_a_no_op(
    task_service: TaskService,
    owner_event: Event,
) -> None:
    task = task_service.create(
        TEST_USER_ID, str(owner_event.event_id), TaskCreate(title="Call the venue")
    )

    unchanged = task_service.update(
        TEST_USER_ID,
        str(owner_event.event_id),
        str(task.task_id),
        TaskUpdate(priority=task.priority),
    )

    assert unchanged.updated_at == task.updated_at


def test_task_update_surfaces_repository_conflicts(
    task_service: TaskService,
    owner_event: Event,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = task_service.create(
        TEST_USER_ID, str(owner_event.event_id), TaskCreate(title="Call the venue")
    )
    monkeypatch.setattr(
        task_service._planning_repository, "update_task", lambda *_args, **_kwargs: None
    )

    with pytest.raises(ResourceNotFoundError):
        task_service.update(
            TEST_USER_ID,
            str(owner_event.event_id),
            str(task.task_id),
            TaskUpdate(priority="high"),
        )


def test_deleting_the_same_task_twice_reports_not_found(
    task_service: TaskService,
    owner_event: Event,
) -> None:
    task = task_service.create(
        TEST_USER_ID, str(owner_event.event_id), TaskCreate(title="Temporary")
    )
    event_id = str(owner_event.event_id)

    task_service.delete(TEST_USER_ID, event_id, str(task.task_id))

    with pytest.raises(ResourceNotFoundError):
        task_service.delete(TEST_USER_ID, event_id, str(task.task_id))


def test_task_lookup_requires_a_known_event(
    task_service: TaskService,
) -> None:
    with pytest.raises(ResourceNotFoundError):
        task_service.get(TEST_USER_ID, str(uuid4()), str(uuid4()))


def test_vendor_follow_up_tasks_are_created_for_active_stages(
    task_service: TaskService,
    vendor_service: VendorService,
    owner_event: Event,
) -> None:
    event_id = str(owner_event.event_id)
    vendor = vendor_service.create(
        TEST_USER_ID,
        event_id,
        VendorCreate(name="Blue Hall", category="venue", status="contacted"),
    )

    first, _total = task_service.list_tasks(
        TEST_USER_ID,
        event_id,
        status=None,
        priority=None,
        timeline_id=None,
        limit=100,
        offset=0,
    )
    assert first, "active vendors should generate follow-up tasks"

    task_service.ensure_vendor_tasks(TEST_USER_ID, owner_event, vendor)
    second, _total_after = task_service.list_tasks(
        TEST_USER_ID,
        event_id,
        status=None,
        priority=None,
        timeline_id=None,
        limit=100,
        offset=0,
    )
    assert len(second) == len(first)


def test_ensure_vendor_tasks_reraises_unexpected_errors(
    task_service: TaskService,
    vendor_service: VendorService,
    owner_event: Event,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vendor = vendor_service.create(
        TEST_USER_ID,
        str(owner_event.event_id),
        VendorCreate(name="Quiet Hall", category="venue", status="shortlisted"),
    )

    monkeypatch.setattr(
        task_service._planning_repository,
        "get_task_by_template_key",
        lambda *_args, **_kwargs: None,
    )

    def _explode(_task: object) -> Any:
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(task_service._planning_repository, "create_task", _explode)

    with pytest.raises(RuntimeError, match="disk on fire"):
        task_service.ensure_vendor_tasks(TEST_USER_ID, owner_event, vendor)


def test_ensure_vendor_tasks_surfaces_conflicts_without_an_existing_task(
    task_service: TaskService,
    vendor_service: VendorService,
    owner_event: Event,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vendor = vendor_service.create(
        TEST_USER_ID,
        str(owner_event.event_id),
        VendorCreate(name="Lonely Hall", category="venue", status="shortlisted"),
    )
    monkeypatch.setattr(
        task_service._planning_repository,
        "get_task_by_template_key",
        lambda *_args, **_kwargs: None,
    )

    def _conflict(_task: object) -> Any:
        raise ResourceConflictError("Template key already used.")

    monkeypatch.setattr(task_service._planning_repository, "create_task", _conflict)

    with pytest.raises(ResourceConflictError):
        task_service.ensure_vendor_tasks(TEST_USER_ID, owner_event, vendor)


def test_ensure_vendor_tasks_recovers_when_the_conflicting_task_exists(
    task_service: TaskService,
    vendor_service: VendorService,
    owner_event: Event,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.exceptions import ResourceConflictError

    event_id = str(owner_event.event_id)
    vendor = vendor_service.create(
        TEST_USER_ID,
        event_id,
        VendorCreate(name="Busy Hall", category="venue", status="shortlisted"),
    )
    existing = task_service.create(TEST_USER_ID, event_id, TaskCreate(title="An unrelated task"))
    lookups = {"count": 0}

    def _lookup(*_args: Any, **_kwargs: Any) -> Any:
        lookups["count"] += 1
        # First probe finds nothing; every later probe finds the existing task.
        return None if lookups["count"] == 1 else existing

    monkeypatch.setattr(
        task_service._planning_repository,
        "get_task_by_template_key",
        _lookup,
    )

    def _conflict(_task: object) -> Any:
        raise ResourceConflictError("Template key already used.")

    monkeypatch.setattr(task_service._planning_repository, "create_task", _conflict)

    created = task_service.ensure_vendor_tasks(TEST_USER_ID, owner_event, vendor)

    assert created == []


def test_generated_task_is_idempotent_per_template_key(
    task_service: TaskService,
    owner_event: Event,
) -> None:
    first = task_service.create_generated_task(
        TEST_USER_ID,
        owner_event,
        template_key="proposal:demo:step",
        title="Draft the seating chart",
        description=None,
        priority=TaskPriority.MEDIUM,
    )
    second = task_service.create_generated_task(
        TEST_USER_ID,
        owner_event,
        template_key="proposal:demo:step",
        title="Draft the seating chart",
        description=None,
        priority=TaskPriority.MEDIUM,
    )

    assert first.task_id == second.task_id


def test_generated_task_conflict_returns_the_existing_task(
    task_service: TaskService,
    owner_event: Event,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing = task_service.create(
        TEST_USER_ID, str(owner_event.event_id), TaskCreate(title="Already here")
    )
    lookups = iter([None, existing])

    monkeypatch.setattr(
        task_service._planning_repository,
        "get_task_by_template_key",
        lambda *_args, **_kwargs: next(lookups),
    )

    def _conflict(_task: object) -> Any:
        raise ResourceConflictError("Template key already used.")

    monkeypatch.setattr(task_service._planning_repository, "create_task", _conflict)

    created = task_service.create_generated_task(
        TEST_USER_ID,
        owner_event,
        template_key="proposal:demo:conflict",
        title="Race winner",
        description=None,
        priority=TaskPriority.MEDIUM,
    )

    assert created.task_id == existing.task_id


def test_generated_task_conflict_without_existing_task_raises(
    task_service: TaskService,
    owner_event: Event,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        task_service._planning_repository,
        "get_task_by_template_key",
        lambda *_args, **_kwargs: None,
    )

    def _conflict(_task: object) -> Any:
        raise ResourceConflictError("Template key already used.")

    monkeypatch.setattr(task_service._planning_repository, "create_task", _conflict)

    with pytest.raises(ResourceConflictError):
        task_service.create_generated_task(
            TEST_USER_ID,
            owner_event,
            template_key="proposal:demo:ghost",
            title="Never lands",
            description=None,
            priority=TaskPriority.MEDIUM,
        )


# --- vendor service --------------------------------------------------------------


def test_vendor_create_rejects_inverted_price_range(
    vendor_service: VendorService,
    owner_event: Event,
) -> None:
    with pytest.raises(DomainValidationError):
        vendor_service.create(
            TEST_USER_ID,
            str(owner_event.event_id),
            VendorCreate(
                name="Wrong Way Hall",
                category="venue",
                price_min="90000.00",
                price_max="10000.00",
            ),
        )


def test_vendor_update_reports_missing_vendor(
    vendor_service: VendorService,
    owner_event: Event,
) -> None:
    with pytest.raises(ResourceNotFoundError):
        vendor_service.update(
            TEST_USER_ID,
            str(owner_event.event_id),
            str(uuid4()),
            VendorUpdate(name="Ghost Hall"),
        )


def test_vendor_delete_reports_missing_vendor(
    vendor_service: VendorService,
    owner_event: Event,
) -> None:
    with pytest.raises(ResourceNotFoundError):
        vendor_service.delete(TEST_USER_ID, str(owner_event.event_id), str(uuid4()))


def test_vendor_update_without_changes_is_a_no_op(
    vendor_service: VendorService,
    owner_event: Event,
) -> None:
    event_id = str(owner_event.event_id)
    vendor = vendor_service.create(
        TEST_USER_ID, event_id, VendorCreate(name="Steady Hall", category="venue")
    )

    unchanged = vendor_service.update(TEST_USER_ID, event_id, str(vendor.vendor_id), VendorUpdate())

    assert unchanged.updated_at == vendor.updated_at


def test_vendor_update_normalizes_website_urls(
    vendor_service: VendorService,
    owner_event: Event,
) -> None:
    event_id = str(owner_event.event_id)
    vendor = vendor_service.create(
        TEST_USER_ID, event_id, VendorCreate(name="Web Hall", category="venue")
    )

    updated = vendor_service.update(
        TEST_USER_ID,
        event_id,
        str(vendor.vendor_id),
        VendorUpdate(website_url="https://example.test/hall"),
    )

    assert updated.website_url == "https://example.test/hall"


def test_protected_vendor_fields_are_rejected() -> None:
    with pytest.raises(DomainValidationError):
        VendorService._reject_protected_fields({"vendor_id": "anything"})


def test_vendor_update_rejects_inverted_price_ranges(
    vendor_service: VendorService,
    owner_event: Event,
) -> None:
    event_id = str(owner_event.event_id)
    vendor = vendor_service.create(
        TEST_USER_ID,
        event_id,
        VendorCreate(name="Range Hall", category="venue", price_min="100.00", price_max="200.00"),
    )

    with pytest.raises(DomainValidationError):
        vendor_service.update(
            TEST_USER_ID,
            event_id,
            str(vendor.vendor_id),
            VendorUpdate(price_min="500.00"),
        )


def test_vendor_update_rejects_invalid_transitions(
    vendor_service: VendorService,
    owner_event: Event,
) -> None:
    event_id = str(owner_event.event_id)
    vendor = vendor_service.create(
        TEST_USER_ID, event_id, VendorCreate(name="Jump Hall", category="venue")
    )

    with pytest.raises(DomainValidationError):
        vendor_service.update(
            TEST_USER_ID, event_id, str(vendor.vendor_id), VendorUpdate(status="selected")
        )


def test_booking_requires_a_quote_or_final_cost(
    vendor_service: VendorService,
    owner_event: Event,
) -> None:
    event_id = str(owner_event.event_id)
    vendor = vendor_service.create(
        TEST_USER_ID,
        event_id,
        VendorCreate(name="Ready Hall", category="venue", status="selected"),
    )

    with pytest.raises(DomainValidationError):
        vendor_service.update(
            TEST_USER_ID, event_id, str(vendor.vendor_id), VendorUpdate(status="booked")
        )


def test_booked_vendors_cannot_be_deleted(
    vendor_service: VendorService,
    owner_event: Event,
) -> None:
    event_id = str(owner_event.event_id)
    vendor = vendor_service.create(
        TEST_USER_ID,
        event_id,
        VendorCreate(
            name="Locked Hall",
            category="venue",
            status="booked",
            quoted_cost="450000.00",
        ),
    )

    with pytest.raises(DomainValidationError):
        vendor_service.delete(TEST_USER_ID, event_id, str(vendor.vendor_id))


def test_vendor_delete_surfaces_repository_failures(
    vendor_service: VendorService,
    owner_event: Event,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event_id = str(owner_event.event_id)
    vendor = vendor_service.create(
        TEST_USER_ID, event_id, VendorCreate(name="Vanishing Hall", category="venue")
    )
    monkeypatch.setattr(
        vendor_service._vendor_repository, "delete", lambda *_args, **_kwargs: False
    )

    with pytest.raises(ResourceNotFoundError):
        vendor_service.delete(TEST_USER_ID, event_id, str(vendor.vendor_id))


def test_vendor_creation_requires_a_known_event(vendor_service: VendorService) -> None:
    with pytest.raises(ResourceNotFoundError):
        vendor_service.create(
            TEST_USER_ID,
            str(uuid4()),
            VendorCreate(name="Nowhere Hall", category="venue"),
        )


def test_comparison_requires_every_vendor(
    vendor_service: VendorService,
    owner_event: Event,
) -> None:
    event_id = str(owner_event.event_id)
    known = vendor_service.create(
        TEST_USER_ID, event_id, VendorCreate(name="Known Hall", category="venue")
    )

    with pytest.raises(ResourceNotFoundError):
        vendor_service.compare(
            TEST_USER_ID,
            event_id,
            VendorCompareRequest(vendor_ids=[str(known.vendor_id), str(uuid4())]),
        )


def test_comparison_flags_unfair_prices_and_missing_data(
    vendor_service: VendorService,
    owner_event: Event,
) -> None:
    event_id = str(owner_event.event_id)
    over_budget = vendor_service.create(
        TEST_USER_ID,
        event_id,
        VendorCreate(
            name="Grand Palace",
            category="venue",
            quoted_cost="900000.00",
            currency="INR",
            service_area="Bengaluru",
            status="contacted",
            rating="4.7",
        ),
    )
    bare = vendor_service.create(
        TEST_USER_ID, event_id, VendorCreate(name="Bare Hall", category="venue")
    )
    foreign = vendor_service.create(
        TEST_USER_ID,
        event_id,
        VendorCreate(
            name="Dollar Hall",
            category="venue",
            quoted_cost="5000.00",
            currency="USD",
        ),
    )

    result = vendor_service.compare(
        TEST_USER_ID,
        event_id,
        VendorCompareRequest(
            vendor_ids=[
                str(over_budget.vendor_id),
                str(bare.vendor_id),
                str(foreign.vendor_id),
            ],
            prefer_service_area="Bengaluru",
            prefer_quick_response=True,
        ),
    )

    by_id = {item["vendor_id"]: item for item in result["items"]}
    assert by_id[str(over_budget.vendor_id)]["budget_fit"] == "over_event_budget"
    assert by_id[str(over_budget.vendor_id)]["preference_match"] == [
        "service_area_match",
        "active_response_state",
        "high_recorded_rating",
    ]
    assert "price/quote" in by_id[str(bare.vendor_id)]["missing"]
    assert "service_area" in by_id[str(bare.vendor_id)]["missing"]
    assert by_id[str(bare.vendor_id)]["budget_fit"] == ("unknown_due_to_missing_price_or_currency")
    assert any(
        "Currency differs" in reason
        for reason in by_id[str(foreign.vendor_id)]["reasons_cannot_compare_fairly"]
    )


def test_budget_fit_classification_edges() -> None:
    assert VendorService._budget_fit(Decimal("100"), True, Decimal("50")) == ("within_event_budget")
    assert VendorService._budget_fit(None, False, None) is None


# --- small service orphans --------------------------------------------------------


def test_timeline_lookup_requires_a_generated_timeline(
    timeline_service: TimelineService,
    owner_event: Event,
) -> None:
    with pytest.raises(ResourceNotFoundError):
        timeline_service.get(TEST_USER_ID, str(owner_event.event_id))


def test_timeline_lookup_requires_a_known_event(timeline_service: TimelineService) -> None:
    with pytest.raises(ResourceNotFoundError):
        timeline_service.get(TEST_USER_ID, str(uuid4()))


def test_event_update_surfaces_repository_conflicts(
    event_service: EventService,
    owner_event: Event,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(event_service._repository, "update", lambda *_args, **_kwargs: None)

    with pytest.raises(ResourceNotFoundError):
        event_service.update(TEST_USER_ID, str(owner_event.event_id), EventUpdate(name="Renamed"))


def test_budget_lookup_reports_missing_budget(
    budget_service: BudgetService,
) -> None:
    with pytest.raises(ResourceNotFoundError):
        budget_service._require_budget(uuid4())


def test_reserve_parsing_rejects_unsupported_shapes() -> None:
    with pytest.raises(RuntimeError, match="Unsupported reserve configuration"):
        BudgetService._reserve_values(object())


def test_orchestration_delegates_applied_recommendations(
    owner_event: Event,
    event_service: EventService,
    budget_service: BudgetService,
    task_service: TaskService,
) -> None:
    proposal_service = ProposalService(
        proposal_repository=InMemoryProposalRepository(),
        event_service=event_service,
        budget_service=budget_service,
        task_service=task_service,
    )
    orchestration = PlanningOrchestrationService(
        proposal_service=proposal_service,
        ai_planning_service=None,  # type: ignore[arg-type]
    )

    assert orchestration.applied_recommendations(TEST_USER_ID, str(owner_event.event_id)) == []
