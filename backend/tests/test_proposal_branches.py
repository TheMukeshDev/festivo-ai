"""Branch coverage for proposal lifecycle, approval application, and plan item mapping."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest

from app.core.exceptions import (
    DomainValidationError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.models.event import Event
from app.models.proposal import (
    Proposal,
    ProposalActionType,
    ProposalStatus,
    ProposalType,
)
from app.models.task import TaskStatus
from app.repositories.memory_proposal_repository import InMemoryProposalRepository
from app.repositories.memory_vendor_repository import InMemoryVendorRepository
from app.schemas.budget import BudgetCreate
from app.schemas.event import EventCreate, EventUpdate
from app.schemas.proposal import ProposalApprovalRequest, ProposalRejectRequest
from app.schemas.task import TaskCreate, TaskUpdate
from app.schemas.vendor import VendorCreate
from app.services.ai.schemas import AIPlanResponse
from app.services.budget_service import BudgetService
from app.services.event_service import EventService
from app.services.proposal_service import ProposalService
from app.services.task_service import TaskService
from app.services.vendor_service import VendorService
from tests.conftest import FIXED_NOW, TEST_USER_ID, MutableClock

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


@pytest.fixture
def proposal_service(
    proposal_repository: InMemoryProposalRepository,
    event_service: EventService,
    budget_service: BudgetService,
    task_service: TaskService,
    vendor_service: VendorService,
    clock: MutableClock,
) -> ProposalService:
    return ProposalService(
        proposal_repository=proposal_repository,
        event_service=event_service,
        budget_service=budget_service,
        task_service=task_service,
        vendor_service=vendor_service,
        clock=clock,
        ttl=timedelta(days=7),
    )


@pytest.fixture
def solo_proposal_service(
    proposal_repository: InMemoryProposalRepository,
    event_service: EventService,
    budget_service: BudgetService,
    task_service: TaskService,
    clock: MutableClock,
) -> ProposalService:
    """Proposal service without vendor workflow support."""
    return ProposalService(
        proposal_repository=proposal_repository,
        event_service=event_service,
        budget_service=budget_service,
        task_service=task_service,
        vendor_service=None,
        clock=clock,
        ttl=timedelta(days=7),
    )


@pytest.fixture
def proposal_repository() -> InMemoryProposalRepository:
    return InMemoryProposalRepository()


def _item(
    action_type: ProposalActionType,
    data: dict[str, Any],
    *,
    status: str = "pending",
    item_id: str | None = None,
) -> dict[str, Any]:
    return {
        "item_id": item_id or str(uuid4()),
        "action_type": action_type.value,
        "status": status,
        "label": str(data.get("title", "Suggestion"))[:200],
        "data": data,
        "applied_at": None,
        "result_message": None,
    }


def _seed(
    service: ProposalService,
    event: Event,
    items: list[dict[str, Any]],
    *,
    status: ProposalStatus = ProposalStatus.PENDING,
    expires_at: Any = None,
) -> Proposal:
    now = FIXED_NOW
    proposal = Proposal(
        proposal_id=uuid4(),
        event_id=event.event_id,
        owner_id=TEST_USER_ID,
        proposal_type=ProposalType.AI_PLANNING,
        title="Seeded proposal",
        summary="Seeded summary",
        payload={"items": items},
        status=status,
        version=1,
        source_snapshot=service._snapshot(TEST_USER_ID, event),
        created_at=now,
        updated_at=now,
        expires_at=expires_at or now + timedelta(days=7),
    )
    return service._repository.create(proposal)


def _approve(
    service: ProposalService,
    event: Event,
    proposal: Proposal,
    **kwargs: Any,
) -> Any:
    request = ProposalApprovalRequest(**kwargs)
    return service.approve(TEST_USER_ID, str(event.event_id), str(proposal.proposal_id), request)


def _reject(
    service: ProposalService,
    event: Event,
    proposal: Proposal,
    **kwargs: Any,
) -> Any:
    request = ProposalRejectRequest(**kwargs)
    return service.reject(TEST_USER_ID, str(event.event_id), str(proposal.proposal_id), request)


def _plan(**overrides: Any) -> AIPlanResponse:
    payload: dict[str, Any] = {
        "event_id": "11111111-1111-1111-1111-111111111111",
        "summary": "A focused plan of attack.",
        "generated_at": "2030-05-15T08:00:00+00:00",
        "model_used": "unit-model",
    }
    payload.update(overrides)
    return AIPlanResponse.model_validate(payload)


# --- creation --------------------------------------------------------------------


def test_plan_without_actionable_items_is_rejected(
    proposal_service: ProposalService,
    owner_event: Event,
) -> None:
    with pytest.raises(DomainValidationError) as raised:
        proposal_service.create_ai_proposal(TEST_USER_ID, str(owner_event.event_id), _plan())

    assert raised.value.issues[0].message == (
        "The AI response did not contain actionable suggestions."
    )


def test_missing_proposal_lookup_is_not_found(
    proposal_service: ProposalService,
    owner_event: Event,
) -> None:
    with pytest.raises(ResourceNotFoundError, match="Proposal not found"):
        proposal_service.get(TEST_USER_ID, str(owner_event.event_id), str(uuid4()))


# --- plan item mapping -----------------------------------------------------------


def test_plan_items_deduplicate_and_cover_every_suggestion_type(
    proposal_service: ProposalService,
    owner_event: Event,
) -> None:
    plan = _plan(
        task_suggestions=[
            {
                "title": "Book the venue",
                "explanation": "Confirm before dates fill up.",
                "priority": "high",
            },
            {
                "title": "  book the venue ",
                "explanation": "Duplicate title must be dropped.",
            },
        ],
        vendor_category_suggestions=[
            {"category": "Catering", "rationale": "Compare per-plate quotes."},
            {"category": "catering", "rationale": "Duplicate category."},
        ],
        budget_suggestions=[
            {
                "category": "Decor",
                "description": "Flowers",
                "currency": "USD",
                "rationale": "Wrong currency is skipped.",
            }
        ],
        timeline_suggestions=["Send invitations eight weeks early."],
        next_steps=["Shortlist venues this week."],
    )

    proposal = proposal_service.create_ai_proposal(TEST_USER_ID, str(owner_event.event_id), plan)

    labels = [item["label"] for item in proposal.payload["items"]]
    assert labels.count("Book the venue") == 1
    assert labels.count("Research Catering vendors") == 1
    assert "Timeline improvement" in labels
    assert "Next steps" in labels
    assert not any(label.startswith("Budget advice") for label in labels)


def test_plan_items_are_capped_at_the_maximum(
    proposal_service: ProposalService,
    owner_event: Event,
) -> None:
    plan = _plan(
        recommendations=[
            {
                "category": f"Tip {index}",
                "description": "Keep guests informed.",
                "rationale": "Communication reduces no-shows.",
            }
            for index in range(70)
        ],
    )

    proposal = proposal_service.create_ai_proposal(TEST_USER_ID, str(owner_event.event_id), plan)

    assert len(proposal.payload["items"]) == 60


# --- approval --------------------------------------------------------------------


def test_approving_an_already_resolved_subset_is_a_no_op(
    proposal_service: ProposalService,
    owner_event: Event,
) -> None:
    first = _item(ProposalActionType.ADVISORY, {"details": "Invite early"})
    second = _item(ProposalActionType.ADVISORY, {"details": "Book car rental"})
    proposal = _seed(proposal_service, owner_event, [first, second])

    initial = _approve(proposal_service, owner_event, proposal, item_ids=[first["item_id"]])
    assert initial.proposal.status == "partially_approved"

    repeated = proposal_service.get(
        TEST_USER_ID, str(owner_event.event_id), str(proposal.proposal_id)
    )
    response = _approve(proposal_service, owner_event, repeated, item_ids=[first["item_id"]])

    assert response.applied == []
    assert response.skipped[0].message == "This item was already applied."
    assert response.proposal.status == "partially_approved"


def test_rejected_proposal_cannot_be_approved(
    proposal_service: ProposalService,
    owner_event: Event,
) -> None:
    proposal = _seed(
        proposal_service,
        owner_event,
        [_item(ProposalActionType.ADVISORY, {"details": "Later"})],
        status=ProposalStatus.REJECTED,
    )

    with pytest.raises(ResourceConflictError, match="no longer be approved"):
        _approve(proposal_service, owner_event, proposal)


def test_approve_rejects_items_from_other_proposals(
    proposal_service: ProposalService,
    owner_event: Event,
) -> None:
    proposal = _seed(
        proposal_service,
        owner_event,
        [_item(ProposalActionType.ADVISORY, {"details": "Mine"})],
    )

    with pytest.raises(DomainValidationError) as raised:
        _approve(proposal_service, owner_event, proposal, item_ids=[uuid4()])

    assert raised.value.issues[0].message == (
        "One or more proposal items do not belong to this proposal."
    )


def test_terminal_rejected_items_land_in_the_rejected_bucket(
    proposal_service: ProposalService,
    owner_event: Event,
) -> None:
    rejected_item = _item(ProposalActionType.ADVISORY, {"details": "No"}, status="rejected")
    pending_item = _item(ProposalActionType.ADVISORY, {"details": "Yes"})
    proposal = _seed(proposal_service, owner_event, [rejected_item, pending_item])

    response = _approve(
        proposal_service, owner_event, proposal, item_ids=[rejected_item["item_id"]]
    )

    assert response.rejected[0].item_id == rejected_item["item_id"]
    assert response.applied == []
    assert response.proposal.status == "pending"


def test_terminal_skipped_items_are_reported_as_skipped(
    proposal_service: ProposalService,
    owner_event: Event,
) -> None:
    skipped_item = _item(ProposalActionType.ADVISORY, {"details": "Old"}, status="skipped")
    proposal = _seed(proposal_service, owner_event, [skipped_item])

    response = _approve(proposal_service, owner_event, proposal, item_ids=[skipped_item["item_id"]])

    assert response.skipped[0].message == "This item was skipped."


def test_budget_currency_mismatch_downgrades_to_skip(
    proposal_service: ProposalService,
    owner_event: Event,
) -> None:
    item = _item(
        ProposalActionType.BUDGET_ALLOCATION_SUGGESTION,
        {
            "category": "Catering",
            "description": "Per-plate",
            "rationale": "Market rate.",
            "amount": "100000.00",
            "currency": "USD",
        },
    )
    proposal = _seed(proposal_service, owner_event, [item])

    response = _approve(proposal_service, owner_event, proposal)

    assert response.skipped[0].message == "Budget suggestions must use the event currency."
    assert response.applied == []


def test_invalid_budget_amount_downgrades_to_skip(
    proposal_service: ProposalService,
    owner_event: Event,
) -> None:
    item = _item(
        ProposalActionType.BUDGET_ALLOCATION_SUGGESTION,
        {
            "category": "Catering",
            "description": "Per-plate",
            "rationale": "Market rate.",
            "amount": "not-a-number",
            "currency": "INR",
        },
    )
    proposal = _seed(proposal_service, owner_event, [item])

    response = _approve(proposal_service, owner_event, proposal)

    assert response.skipped[0].message == "Invalid suggested amount."


def test_budget_advisory_without_amount_still_applies(
    proposal_service: ProposalService,
    owner_event: Event,
) -> None:
    item = _item(
        ProposalActionType.BUDGET_ALLOCATION_SUGGESTION,
        {
            "category": "Catering",
            "description": "Per-plate",
            "rationale": "Allocate after quotes.",
            "amount": None,
            "currency": "INR",
        },
    )
    proposal = _seed(proposal_service, owner_event, [item])

    response = _approve(proposal_service, owner_event, proposal)

    assert response.applied[0].status == "applied"


def test_advisory_budget_can_be_approved_without_recording_it(
    proposal_service: ProposalService,
    owner_event: Event,
) -> None:
    item = _item(
        ProposalActionType.BUDGET_ALLOCATION_SUGGESTION,
        {
            "category": "Catering",
            "description": "Per-plate",
            "rationale": "Allocate after quotes.",
            "amount": "50000.00",
            "currency": "INR",
        },
    )
    proposal = _seed(proposal_service, owner_event, [item])

    response = _approve(proposal_service, owner_event, proposal, allow_advisory=False)

    assert response.skipped[0].message == "Advisory budget suggestions were not approved."


def test_invalid_task_payload_downgrades_to_skip(
    proposal_service: ProposalService,
    owner_event: Event,
) -> None:
    item = _item(ProposalActionType.ADD_TASK, {"description": "Missing a title"})
    proposal = _seed(proposal_service, owner_event, [item])

    response = _approve(proposal_service, owner_event, proposal)

    assert response.skipped[0].message == "The proposed task is no longer valid."


def test_due_date_after_event_date_downgrades_to_skip(
    proposal_service: ProposalService,
    owner_event: Event,
) -> None:
    item = _item(
        ProposalActionType.ADD_TASK,
        {
            "title": "Plan the after-party",
            "explanation": "Too late for the event.",
            "due_at": "2030-07-01T10:00:00+00:00",
        },
    )
    proposal = _seed(proposal_service, owner_event, [item])

    response = _approve(proposal_service, owner_event, proposal)

    assert response.skipped[0].message == ("Proposed task dates cannot be after the event date.")


def test_vendor_follow_up_skips_without_vendor_workflow(
    solo_proposal_service: ProposalService,
    owner_event: Event,
) -> None:
    item = _item(
        ProposalActionType.ADD_VENDOR_FOLLOW_UP_TASK,
        {"vendor_id": str(uuid4()), "title": "Call the decorator"},
    )
    proposal = _seed(solo_proposal_service, owner_event, [item])

    response = _approve(solo_proposal_service, owner_event, proposal)

    assert response.skipped[0].message == "Vendor workflow is unavailable."


def test_vendor_follow_up_skips_when_vendor_is_gone(
    proposal_service: ProposalService,
    owner_event: Event,
) -> None:
    item = _item(
        ProposalActionType.ADD_VENDOR_FOLLOW_UP_TASK,
        {"vendor_id": str(uuid4()), "title": "Call the decorator"},
    )
    proposal = _seed(proposal_service, owner_event, [item])

    response = _approve(proposal_service, owner_event, proposal)

    assert response.skipped[0].message == "The referenced resource no longer exists."


def test_vendor_follow_up_skips_rejected_vendors(
    proposal_service: ProposalService,
    owner_event: Event,
    vendor_service: VendorService,
) -> None:
    vendor = vendor_service.create(
        TEST_USER_ID,
        str(owner_event.event_id),
        VendorCreate(
            name="Sunset Decor",
            category="decoration",
            status="rejected",
        ),
    )
    item = _item(
        ProposalActionType.ADD_VENDOR_FOLLOW_UP_TASK,
        {"vendor_id": str(vendor.vendor_id), "title": "Chase the decorator"},
    )
    proposal = _seed(proposal_service, owner_event, [item])

    response = _approve(proposal_service, owner_event, proposal)

    assert response.skipped[0].message == "The vendor is no longer active."


def test_update_due_date_action_applies(
    proposal_service: ProposalService,
    owner_event: Event,
    task_service: TaskService,
) -> None:
    task = task_service.create(
        TEST_USER_ID,
        str(owner_event.event_id),
        TaskCreate(title="Book the caterer", priority="high"),
    )
    item = _item(
        ProposalActionType.UPDATE_TASK_DUE_DATE,
        {"task_id": str(task.task_id), "due_at": "2030-06-01T10:00:00+00:00"},
    )
    proposal = _seed(proposal_service, owner_event, [item])

    response = _approve(proposal_service, owner_event, proposal)

    assert response.applied[0].message == "Updated the task due date."
    refreshed = task_service.get(TEST_USER_ID, str(owner_event.event_id), str(task.task_id))
    assert refreshed.due_at is not None


def test_update_due_date_skips_invalid_payload(
    proposal_service: ProposalService,
    owner_event: Event,
) -> None:
    item = _item(ProposalActionType.UPDATE_TASK_DUE_DATE, {"due_at": "2030-06-01"})
    proposal = _seed(proposal_service, owner_event, [item])

    response = _approve(proposal_service, owner_event, proposal)

    assert response.skipped[0].message == "The proposed due-date change is invalid."


def test_update_due_date_skips_missing_task(
    proposal_service: ProposalService,
    owner_event: Event,
) -> None:
    item = _item(
        ProposalActionType.UPDATE_TASK_DUE_DATE,
        {"task_id": str(uuid4()), "due_at": "2030-06-01T10:00:00+00:00"},
    )
    proposal = _seed(proposal_service, owner_event, [item])

    response = _approve(proposal_service, owner_event, proposal)

    assert response.skipped[0].message == "The target task no longer exists."


def test_update_due_date_skips_completed_tasks(
    proposal_service: ProposalService,
    owner_event: Event,
    task_service: TaskService,
) -> None:
    task = task_service.create(
        TEST_USER_ID,
        str(owner_event.event_id),
        TaskCreate(title="Send invitations"),
    )
    task_service.update(
        TEST_USER_ID,
        str(owner_event.event_id),
        str(task.task_id),
        TaskUpdate(status=TaskStatus.COMPLETED),
    )
    item = _item(
        ProposalActionType.UPDATE_TASK_DUE_DATE,
        {"task_id": str(task.task_id), "due_at": "2030-06-01T10:00:00+00:00"},
    )
    proposal = _seed(proposal_service, owner_event, [item])

    response = _approve(proposal_service, owner_event, proposal)

    assert response.skipped[0].message == "Completed tasks are never modified by a proposal."


def test_update_due_date_skips_when_user_edited_the_task(
    proposal_service: ProposalService,
    owner_event: Event,
    task_service: TaskService,
) -> None:
    task = task_service.create(
        TEST_USER_ID,
        str(owner_event.event_id),
        TaskCreate(title="Confirm guest count"),
    )
    item = _item(
        ProposalActionType.UPDATE_TASK_DUE_DATE,
        {
            "task_id": str(task.task_id),
            "due_at": "2030-06-01T10:00:00+00:00",
            "expected_due_at": "2030-05-20T10:00:00+00:00",
        },
    )
    proposal = _seed(proposal_service, owner_event, [item])

    response = _approve(proposal_service, owner_event, proposal)

    assert response.skipped[0].message == (
        "The task due date was edited by the user; the suggestion was not applied."
    )


def test_version_conflict_surfaces_when_persistence_fails(
    proposal_service: ProposalService,
    owner_event: Event,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = _seed(
        proposal_service,
        owner_event,
        [_item(ProposalActionType.ADVISORY, {"details": "Do the thing"})],
    )
    monkeypatch.setattr(proposal_service._repository, "update", lambda *_args, **_kwargs: None)

    with pytest.raises(ResourceConflictError, match="modified by another request"):
        _approve(proposal_service, owner_event, proposal)


# --- staleness -------------------------------------------------------------------


def test_event_change_after_generation_blocks_approval(
    proposal_service: ProposalService,
    owner_event: Event,
    event_service: EventService,
) -> None:
    proposal = _seed(
        proposal_service,
        owner_event,
        [_item(ProposalActionType.ADVISORY, {"details": "Still fine"})],
    )
    event_service.update(
        TEST_USER_ID, str(owner_event.event_id), EventUpdate(name="Renamed wedding")
    )

    with pytest.raises(ResourceConflictError, match="event changed"):
        _approve(proposal_service, owner_event, proposal)


def test_budget_change_after_generation_blocks_approval(
    proposal_service: ProposalService,
    owner_event: Event,
    budget_service: BudgetService,
) -> None:
    proposal = _seed(
        proposal_service,
        owner_event,
        [_item(ProposalActionType.ADVISORY, {"details": "Still fine"})],
    )
    budget_service.create(
        TEST_USER_ID,
        str(owner_event.event_id),
        BudgetCreate(
            total_limit="500000.00",
            reserve={"type": "percentage", "value": "10.00"},
        ),
    )

    with pytest.raises(ResourceConflictError, match="event changed"):
        _approve(proposal_service, owner_event, proposal)


# --- rejection -------------------------------------------------------------------


def test_rejecting_an_approved_proposal_conflicts(
    proposal_service: ProposalService,
    owner_event: Event,
) -> None:
    proposal = _seed(
        proposal_service,
        owner_event,
        [_item(ProposalActionType.ADVISORY, {"details": "Done"})],
        status=ProposalStatus.APPROVED,
    )

    with pytest.raises(ResourceConflictError, match="approved proposal cannot be rejected"):
        _reject(proposal_service, owner_event, proposal)


def test_rejecting_a_rejected_proposal_is_idempotent(
    proposal_service: ProposalService,
    owner_event: Event,
) -> None:
    proposal = _seed(
        proposal_service,
        owner_event,
        [_item(ProposalActionType.ADVISORY, {"details": "No"})],
        status=ProposalStatus.REJECTED,
    )

    response = _reject(proposal_service, owner_event, proposal)

    assert response.rejected_items == []
    assert response.message == "This proposal was already rejected."


def test_rejecting_an_expired_proposal_conflicts(
    proposal_service: ProposalService,
    owner_event: Event,
) -> None:
    proposal = _seed(
        proposal_service,
        owner_event,
        [_item(ProposalActionType.ADVISORY, {"details": "Too late"})],
        expires_at=FIXED_NOW - timedelta(days=1),
    )

    with pytest.raises(ResourceConflictError, match="expired"):
        _reject(proposal_service, owner_event, proposal)


def test_reject_rejects_unknown_items(
    proposal_service: ProposalService,
    owner_event: Event,
) -> None:
    proposal = _seed(
        proposal_service,
        owner_event,
        [_item(ProposalActionType.ADVISORY, {"details": "Mine"})],
    )

    with pytest.raises(DomainValidationError) as raised:
        _reject(proposal_service, owner_event, proposal, item_ids=[uuid4()])

    assert raised.value.issues[0].message == (
        "One or more proposal items do not belong to this proposal."
    )


def test_reject_with_only_resolved_items_changes_nothing(
    proposal_service: ProposalService,
    owner_event: Event,
) -> None:
    applied_item = _item(ProposalActionType.ADVISORY, {"details": "Kept"}, status="applied")
    pending_item = _item(ProposalActionType.ADVISORY, {"details": "Open"})
    proposal = _seed(proposal_service, owner_event, [applied_item, pending_item])

    response = _reject(proposal_service, owner_event, proposal, item_ids=[applied_item["item_id"]])

    assert response.rejected_items == []
    assert response.message == "No pending items were rejected."


def test_reject_conflict_when_persistence_fails(
    proposal_service: ProposalService,
    owner_event: Event,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = _seed(
        proposal_service,
        owner_event,
        [_item(ProposalActionType.ADVISORY, {"details": "No"})],
    )
    monkeypatch.setattr(proposal_service._repository, "update", lambda *_args, **_kwargs: None)

    with pytest.raises(ResourceConflictError, match="modified by another request"):
        _reject(proposal_service, owner_event, proposal)


# --- applied recommendations ------------------------------------------------------


def test_pending_proposals_never_contribute_recommendations(
    proposal_service: ProposalService,
    owner_event: Event,
) -> None:
    _seed(
        proposal_service,
        owner_event,
        [_item(ProposalActionType.ADVISORY, {"details": "Awaiting approval"})],
        status=ProposalStatus.APPROVED,
    )

    assert proposal_service.applied_recommendations(TEST_USER_ID, str(owner_event.event_id)) == []


# --- datetime parsing and vendor totals ------------------------------------------


def test_parse_datetime_supports_datetimes_strings_and_rejects_others() -> None:
    moment = datetime(2030, 6, 1, 10, 0, tzinfo=UTC)
    assert ProposalService._parse_datetime(moment) == moment
    assert ProposalService._parse_datetime("2030-06-01T10:00:00Z") == moment
    with pytest.raises(ValueError, match="Invalid datetime"):
        ProposalService._parse_datetime(42)


def test_vendor_changes_after_generation_block_approval(
    proposal_service: ProposalService,
    owner_event: Event,
    vendor_service: VendorService,
) -> None:
    proposal = _seed(
        proposal_service,
        owner_event,
        [_item(ProposalActionType.ADVISORY, {"details": "Fine"})],
    )
    vendor_service.create(
        TEST_USER_ID,
        str(owner_event.event_id),
        VendorCreate(name="New Caterer", category="catering"),
    )

    with pytest.raises(ResourceConflictError, match="event changed"):
        _approve(proposal_service, owner_event, proposal)
