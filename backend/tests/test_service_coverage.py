"""Service branches that are not reachable through the happy-path API tests."""

from dataclasses import replace
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from app.core.exceptions import (
    DomainValidationError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.models.task import TaskStatus
from app.models.vendor import VendorStatus
from app.repositories.memory_proposal_repository import InMemoryProposalRepository
from app.repositories.memory_vendor_repository import InMemoryVendorRepository
from app.schemas.budget import ExpenseCreate
from app.schemas.event import EventCreate, EventUpdate
from app.schemas.proposal import ConversationMessage, ProposalGenerationRequest
from app.schemas.task import TaskCreate, TaskUpdate
from app.schemas.vendor import VendorCompareRequest, VendorCreate, VendorUpdate
from app.services.budget_service import BudgetService
from app.services.planning_orchestration_service import PlanningOrchestrationService
from app.services.proposal_service import MAX_MONEY, ProposalService
from app.services.timeline_service import TimelineService
from app.services.vendor_service import VendorService
from tests.conftest import TEST_USER_ID
from tests.test_postgres_repositories import make_vendor


@pytest.fixture
def owner_event(event_service, event_payload):
    return event_service.create(TEST_USER_ID, EventCreate(**event_payload()))


@pytest.fixture
def vendor_service(event_repository, event_service, task_service, clock):
    return VendorService(
        event_repository,
        InMemoryVendorRepository(),
        event_service,
        task_service,
        clock,
    )


@pytest.fixture
def proposal_service(
    event_service,
    budget_service,
    task_service,
    vendor_service,
    clock,
):
    return ProposalService(
        proposal_repository=InMemoryProposalRepository(),
        event_service=event_service,
        budget_service=budget_service,
        task_service=task_service,
        vendor_service=vendor_service,
        clock=clock,
    )


def test_budget_operations_require_an_existing_budget(budget_service, owner_event) -> None:
    with pytest.raises(ResourceNotFoundError):
        budget_service.add_expense(
            TEST_USER_ID,
            str(owner_event.event_id),
            ExpenseCreate(
                expected_version=1,
                category="Catering and Refreshments",
                name="Dinner service",
                amount="100.00",
            ),
        )


def test_unknown_reserve_configuration_is_rejected() -> None:
    with pytest.raises(RuntimeError):
        BudgetService._reserve_values(object())


def test_event_update_raises_when_the_repository_loses_the_row(
    event_service, owner_event, monkeypatch
) -> None:
    monkeypatch.setattr(event_service._repository, "update", lambda *_args, **_kwargs: None)

    with pytest.raises(ResourceNotFoundError):
        event_service.update(
            TEST_USER_ID,
            str(owner_event.event_id),
            EventUpdate(name="Renamed wedding"),
        )


class _RecordingAI:
    def __init__(self) -> None:
        self.preferences: dict[str, Any] | None = None

    def generate_plan(self, owner_id, event_id, preferences):
        self.preferences = preferences
        return SimpleNamespace(owner_id=owner_id, event_id=event_id)


class _RecordingProposal:
    def __init__(self) -> None:
        self.created: tuple[Any, ...] | None = None

    def create_ai_proposal(self, *args: Any):
        self.created = args
        return "proposal"

    def applied_recommendations(self, owner_id, event_id):
        return [{"label": f"{owner_id}:{event_id}"}]


def test_orchestration_forwards_all_generation_context() -> None:
    ai = _RecordingAI()
    proposals = _RecordingProposal()
    orchestration = PlanningOrchestrationService(proposals, ai)

    result = orchestration.generate_ai_proposal(
        TEST_USER_ID,
        "event-id",
        ProposalGenerationRequest(
            focus_areas=["venue"],
            additional_notes="Keep it small.",
            conversation=[ConversationMessage(role="user", content="We prefer mornings.")],
        ),
    )

    assert result == "proposal"
    assert ai.preferences == {
        "focus_areas": ["venue"],
        "additional_notes": "Keep it small.",
        "conversation": [{"role": "user", "content": "We prefer mornings."}],
    }
    assert orchestration.applied_recommendations(TEST_USER_ID, "event-id") == [
        {"label": f"{TEST_USER_ID}:event-id"}
    ]


def test_unsupported_proposal_action_is_skipped(proposal_service, owner_event, monkeypatch):
    monkeypatch.setattr(
        proposal_service,
        "_result",
        lambda item_id, action_type, status, message: (item_id, action_type, status, message),
    )

    result = proposal_service._apply_item(
        TEST_USER_ID,
        owner_event,
        SimpleNamespace(proposal_id=uuid4()),
        {"item_id": "item", "data": {}},
        "unsupported",
        allow_advisory=False,
    )

    assert result[2] == "skipped"


def test_budget_suggestions_reject_out_of_range_amounts(proposal_service, owner_event) -> None:
    with pytest.raises(DomainValidationError):
        proposal_service._validate_budget_suggestion(owner_event, {"amount": str(MAX_MONEY + 1)})


def test_task_lifecycle_guards(task_service, owner_event, monkeypatch) -> None:
    with pytest.raises(ResourceNotFoundError):
        task_service.create(TEST_USER_ID, str(uuid4()), TaskCreate(title="Task"))

    task = task_service.create(
        TEST_USER_ID, str(owner_event.event_id), TaskCreate(title="First task")
    )
    task_service.create(TEST_USER_ID, str(owner_event.event_id), TaskCreate(title="Second task"))

    with pytest.raises(ResourceNotFoundError):
        task_service.update(
            TEST_USER_ID, str(owner_event.event_id), str(uuid4()), TaskUpdate(title="Missing")
        )
    with pytest.raises(DomainValidationError):
        task_service.update(
            TEST_USER_ID, str(owner_event.event_id), str(task.task_id), TaskUpdate(title=None)
        )
    assert (
        task_service.update(
            TEST_USER_ID, str(owner_event.event_id), str(task.task_id), TaskUpdate()
        )
        == task
    )
    assert (
        task_service.update(
            TEST_USER_ID,
            str(owner_event.event_id),
            str(task.task_id),
            TaskUpdate(title=task.title),
        )
        == task
    )

    monkeypatch.setattr(
        task_service._planning_repository, "update_task", lambda *_args, **_kwargs: None
    )
    with pytest.raises(ResourceNotFoundError):
        task_service.update(
            TEST_USER_ID,
            str(owner_event.event_id),
            str(task.task_id),
            TaskUpdate(title="Renamed task"),
        )

    with pytest.raises(ResourceNotFoundError):
        task_service.delete(TEST_USER_ID, str(owner_event.event_id), str(uuid4()))

    completed = task_service.create(
        TEST_USER_ID,
        str(owner_event.event_id),
        TaskCreate(title="Completed task", status=TaskStatus.COMPLETED),
    )
    assert completed.completed_at is not None


def test_vendor_task_generation_handles_existing_and_racing_tasks(
    vendor_service, task_service, owner_event, monkeypatch
) -> None:
    shortlisted = vendor_service.create(
        TEST_USER_ID,
        str(owner_event.event_id),
        VendorCreate(name="Sunset Decor", category="decoration", status="shortlisted"),
    )
    assert task_service.ensure_vendor_tasks(TEST_USER_ID, owner_event, shortlisted) == []

    booked = vendor_service.create(
        TEST_USER_ID,
        str(owner_event.event_id),
        VendorCreate(name="Lotus Banquets", category="venue", status="booked"),
    )
    assert len(task_service.ensure_vendor_tasks(TEST_USER_ID, owner_event, booked)) == 0

    calls = {"count": 0}

    def fake_get(*_args, **_kwargs):
        calls["count"] += 1
        return None if calls["count"] == 1 else make_vendor()

    monkeypatch.setattr(task_service._planning_repository, "get_task_by_template_key", fake_get)
    monkeypatch.setattr(
        task_service._planning_repository,
        "create_task",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ResourceConflictError("conflict")),
    )
    candidate = replace(shortlisted, status=VendorStatus.SHORTLISTED)
    assert task_service.ensure_vendor_tasks(TEST_USER_ID, owner_event, candidate) == []


def test_vendor_task_generation_reraises_when_the_racer_disappears(
    vendor_service, task_service, owner_event, monkeypatch
) -> None:
    vendor = vendor_service.create(
        TEST_USER_ID,
        str(owner_event.event_id),
        VendorCreate(name="Sunset Decor", category="decoration", status="shortlisted"),
    )
    monkeypatch.setattr(
        task_service._planning_repository,
        "get_task_by_template_key",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        task_service._planning_repository,
        "create_task",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ResourceConflictError("conflict")),
    )

    with pytest.raises(ResourceConflictError):
        task_service.ensure_vendor_tasks(TEST_USER_ID, owner_event, vendor)


def test_generated_tasks_are_idempotent_and_tolerate_races(
    task_service, owner_event, monkeypatch
) -> None:
    first = task_service.create_generated_task(
        TEST_USER_ID,
        owner_event,
        template_key="proposal:one",
        title="Generated task",
        description=None,
        priority="medium",
    )
    second = task_service.create_generated_task(
        TEST_USER_ID,
        owner_event,
        template_key="proposal:one",
        title="Generated task",
        description=None,
        priority="medium",
    )
    assert second.task_id == first.task_id

    calls = {"count": 0}
    existing = make_vendor()  # only used as a sentinel with a task_id-like attribute

    def fake_get(*_args, **_kwargs):
        calls["count"] += 1
        return None if calls["count"] == 1 else SimpleNamespace(task_id=existing.vendor_id)

    monkeypatch.setattr(task_service._planning_repository, "get_task_by_template_key", fake_get)
    monkeypatch.setattr(
        task_service._planning_repository,
        "create_task",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ResourceConflictError("conflict")),
    )
    raced = task_service.create_generated_task(
        TEST_USER_ID,
        owner_event,
        template_key="proposal:two",
        title="Raced task",
        description=None,
        priority="medium",
    )
    assert raced.task_id == existing.vendor_id


def test_generated_task_race_reraises_when_no_row_exists(
    task_service, owner_event, monkeypatch
) -> None:
    monkeypatch.setattr(
        task_service._planning_repository,
        "get_task_by_template_key",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        task_service._planning_repository,
        "create_task",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ResourceConflictError("conflict")),
    )

    with pytest.raises(ResourceConflictError):
        task_service.create_generated_task(
            TEST_USER_ID,
            owner_event,
            template_key="proposal:three",
            title="Raced task",
            description=None,
            priority="medium",
        )


def test_timeline_missing_event_and_regeneration_guards(
    timeline_service: TimelineService, owner_event
) -> None:
    with pytest.raises(ResourceNotFoundError):
        timeline_service.get(TEST_USER_ID, str(uuid4()))

    with pytest.raises(ResourceNotFoundError):
        timeline_service.regenerate(TEST_USER_ID, str(owner_event.event_id))


def test_vendor_create_and_update_validation(vendor_service, owner_event) -> None:
    with pytest.raises(DomainValidationError):
        vendor_service.create(
            TEST_USER_ID,
            str(owner_event.event_id),
            VendorCreate(
                name="Invalid Range",
                category="venue",
                price_min="900.00",
                price_max="100.00",
            ),
        )

    with pytest.raises(ResourceNotFoundError):
        vendor_service.update(
            TEST_USER_ID, str(owner_event.event_id), str(uuid4()), VendorUpdate(name="Missing")
        )

    vendor = vendor_service.create(
        TEST_USER_ID,
        str(owner_event.event_id),
        VendorCreate(
            name="Dream Venue",
            category="venue",
            price_min="100.00",
            price_max="500.00",
        ),
    )
    assert (
        vendor_service.update(
            TEST_USER_ID, str(owner_event.event_id), str(vendor.vendor_id), VendorUpdate()
        )
        == vendor
    )

    updated = vendor_service.update(
        TEST_USER_ID,
        str(owner_event.event_id),
        str(vendor.vendor_id),
        VendorUpdate(website_url="https://example.com"),
    )
    assert updated.website_url is not None
    assert updated.website_url.startswith("https://example.com")

    with pytest.raises(DomainValidationError):
        vendor_service.update(
            TEST_USER_ID,
            str(owner_event.event_id),
            str(vendor.vendor_id),
            VendorUpdate(price_min="600.00"),
        )

    with pytest.raises(DomainValidationError):
        VendorService._reject_protected_fields({"vendor_id": "immutable"})

    with pytest.raises(DomainValidationError):
        vendor_service.update(
            TEST_USER_ID,
            str(owner_event.event_id),
            str(vendor.vendor_id),
            VendorUpdate(status="selected"),
        )


def test_vendor_booked_transition_requires_costs(vendor_service, owner_event) -> None:
    vendor = vendor_service.create(
        TEST_USER_ID,
        str(owner_event.event_id),
        VendorCreate(name="Selected Venue", category="venue", status="selected"),
    )

    with pytest.raises(DomainValidationError):
        vendor_service.update(
            TEST_USER_ID,
            str(owner_event.event_id),
            str(vendor.vendor_id),
            VendorUpdate(status="booked"),
        )


def test_vendor_delete_guards(vendor_service, owner_event, monkeypatch) -> None:
    with pytest.raises(ResourceNotFoundError):
        vendor_service.delete(TEST_USER_ID, str(owner_event.event_id), str(uuid4()))

    booked = vendor_service.create(
        TEST_USER_ID,
        str(owner_event.event_id),
        VendorCreate(name="Booked Venue", category="venue", status="booked"),
    )
    with pytest.raises(DomainValidationError):
        vendor_service.delete(TEST_USER_ID, str(owner_event.event_id), str(booked.vendor_id))

    removable = vendor_service.create(
        TEST_USER_ID,
        str(owner_event.event_id),
        VendorCreate(name="Removable Venue", category="venue"),
    )
    monkeypatch.setattr(
        vendor_service._vendor_repository, "delete", lambda *_args, **_kwargs: False
    )
    with pytest.raises(ResourceNotFoundError):
        vendor_service.delete(TEST_USER_ID, str(owner_event.event_id), str(removable.vendor_id))


def test_vendor_compare_marks_missing_vendors(vendor_service, owner_event) -> None:
    with pytest.raises(ResourceNotFoundError):
        vendor_service.compare(
            TEST_USER_ID,
            str(owner_event.event_id),
            VendorCompareRequest(vendor_ids=[str(uuid4()), str(uuid4())]),
        )


def test_vendor_compare_reports_preferences_and_fairness_reasons(
    vendor_service, owner_event
) -> None:
    service = vendor_service
    event_id = str(owner_event.event_id)

    within_budget = service.create(
        TEST_USER_ID,
        event_id,
        VendorCreate(
            name="Lotus Banquets",
            category="venue",
            status="contacted",
            service_area="Bengaluru",
            quoted_cost="1000.00",
            rating="4.50",
        ),
    )
    over_budget = service.create(
        TEST_USER_ID,
        event_id,
        VendorCreate(
            name="Grand Palace",
            category="venue",
            quoted_cost="900000.00",
        ),
    )
    foreign_currency = service.create(
        TEST_USER_ID,
        event_id,
        VendorCreate(
            name="Global Events",
            category="venue",
            currency="USD",
            quoted_cost="1000.00",
        ),
    )
    no_price = service.create(
        TEST_USER_ID,
        event_id,
        VendorCreate(name="Unknown Price", category="venue"),
    )

    result = service.compare(
        TEST_USER_ID,
        event_id,
        VendorCompareRequest(
            vendor_ids=[
                str(within_budget.vendor_id),
                str(over_budget.vendor_id),
                str(foreign_currency.vendor_id),
                str(no_price.vendor_id),
            ],
            prefer_service_area="bengaluru",
            prefer_quick_response=True,
        ),
    )

    items = {item["name"]: item for item in result["items"]}
    assert items["Lotus Banquets"]["budget_fit"] == "within_event_budget"
    assert "service_area_match" in items["Lotus Banquets"]["preference_match"]
    assert "active_response_state" in items["Lotus Banquets"]["preference_match"]
    assert "high_recorded_rating" in items["Lotus Banquets"]["preference_match"]
    assert items["Grand Palace"]["budget_fit"] == "over_event_budget"
    assert (
        "currency differs"
        in " ".join(items["Global Events"]["reasons_cannot_compare_fairly"]).lower()
    )
    assert "price/quote" in items["Unknown Price"]["missing"]
    assert items["Unknown Price"]["budget_fit"] == "unknown_due_to_missing_price_or_currency"


def test_vendor_compare_reports_missing_service_area(vendor_service, owner_event) -> None:
    first = vendor_service.create(
        TEST_USER_ID,
        str(owner_event.event_id),
        VendorCreate(name="First Venue", category="venue", quoted_cost="1000.00"),
    )
    second = vendor_service.create(
        TEST_USER_ID,
        str(owner_event.event_id),
        VendorCreate(name="Second Venue", category="venue", quoted_cost="2000.00"),
    )

    result = vendor_service.compare(
        TEST_USER_ID,
        str(owner_event.event_id),
        VendorCompareRequest(
            vendor_ids=[str(first.vendor_id), str(second.vendor_id)],
            prefer_service_area="Bengaluru",
        ),
    )

    assert all("service_area" in item["missing"] for item in result["items"])


def test_vendor_compare_requires_an_owned_event(vendor_service) -> None:
    with pytest.raises(ResourceNotFoundError):
        vendor_service.compare(
            TEST_USER_ID,
            str(uuid4()),
            VendorCompareRequest(vendor_ids=[str(uuid4()), str(uuid4())]),
        )


def test_vendor_task_generation_reraises_unexpected_failures(
    vendor_service, task_service, owner_event, monkeypatch
) -> None:
    vendor = vendor_service.create(
        TEST_USER_ID,
        str(owner_event.event_id),
        VendorCreate(name="Sunset Decor", category="decoration"),
    )
    monkeypatch.setattr(
        task_service._planning_repository,
        "create_task",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("boom")),
    )

    with pytest.raises(ValueError):
        task_service.ensure_vendor_tasks(
            TEST_USER_ID, owner_event, replace(vendor, status=VendorStatus.SHORTLISTED)
        )


def test_vendor_update_raises_when_the_repository_loses_the_row(
    vendor_service, owner_event, monkeypatch
) -> None:
    vendor = vendor_service.create(
        TEST_USER_ID,
        str(owner_event.event_id),
        VendorCreate(name="Lost Venue", category="venue"),
    )
    monkeypatch.setattr(vendor_service._vendor_repository, "update", lambda *_args, **_kwargs: None)

    with pytest.raises(ResourceNotFoundError):
        vendor_service.update(
            TEST_USER_ID,
            str(owner_event.event_id),
            str(vendor.vendor_id),
            VendorUpdate(notes="Still here"),
        )


def test_budget_fit_is_unknown_without_a_budget() -> None:
    assert VendorService._budget_fit(None, True, None) is None
