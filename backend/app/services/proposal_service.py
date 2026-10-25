"""Validated proposal lifecycle and explicit owner approval application."""

from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from app.core.clock import Clock, coerce_utc, utc_now
from app.core.exceptions import (
    DomainValidationError,
    ResourceConflictError,
    ResourceNotFoundError,
    ValidationIssue,
)
from app.models.budget import MAX_MONEY
from app.models.event import Event
from app.models.proposal import (
    Proposal,
    ProposalActionType,
    ProposalItemStatus,
    ProposalStatus,
    ProposalType,
)
from app.models.task import TaskPriority, TaskStatus
from app.repositories.proposal_repository import ProposalRepository
from app.schemas.proposal import (
    AppliedItemResult,
    ProposalApprovalRequest,
    ProposalApprovalResponse,
    ProposalRejectRequest,
    ProposalRejectResponse,
    ProposalResponse,
)
from app.schemas.task import TaskCreate
from app.services.ai.schemas import AIPlanResponse
from app.services.budget_service import BudgetService
from app.services.event_service import EventService
from app.services.task_service import TaskService
from app.services.vendor_service import VendorService

_PROPOSAL_NOT_FOUND = "Proposal not found."
_DEFAULT_TTL = timedelta(days=7)
_MAX_ITEMS = 60

_PRIORITY_MAP = {
    "low": TaskPriority.LOW,
    "medium": TaskPriority.MEDIUM,
    "high": TaskPriority.HIGH,
    "critical": TaskPriority.URGENT,
}


class ProposalService:
    """Create advisory proposals and apply only explicitly approved actions."""

    def __init__(
        self,
        proposal_repository: ProposalRepository,
        event_service: EventService,
        budget_service: BudgetService,
        task_service: TaskService,
        vendor_service: VendorService | None = None,
        clock: Clock | None = None,
        ttl: timedelta = _DEFAULT_TTL,
    ) -> None:
        self._repository = proposal_repository
        self._event_service = event_service
        self._budget_service = budget_service
        self._task_service = task_service
        self._vendor_service = vendor_service
        self._clock = clock or utc_now
        self._ttl = ttl

    def create_ai_proposal(
        self,
        owner_id: UUID,
        event_id: str,
        plan: AIPlanResponse,
    ) -> Proposal:
        event = self._event_service.get(owner_id, event_id)
        now = self._now()
        items = self._items_from_plan(plan, event)
        if not items:
            raise DomainValidationError(
                [
                    ValidationIssue(
                        field="body.plan",
                        message="The AI response did not contain actionable suggestions.",
                    )
                ]
            )
        proposal = Proposal(
            proposal_id=uuid4(),
            event_id=event.event_id,
            owner_id=owner_id,
            proposal_type=ProposalType.AI_PLANNING,
            title=f"AI planning proposal for {event.name}"[:200],
            summary=plan.summary[:6000],
            payload={
                "items": items,
                "ai_plan": plan.model_dump(mode="json"),
            },
            status=ProposalStatus.PENDING,
            version=1,
            source_snapshot=self._snapshot(owner_id, event),
            created_at=now,
            updated_at=now,
            expires_at=now + self._ttl,
        )
        return self._repository.create(proposal)

    def list(
        self,
        owner_id: UUID,
        event_id: str,
        *,
        status: ProposalStatus | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Proposal], int]:
        event = self._event_service.get(owner_id, event_id)
        return self._repository.list(
            owner_id,
            event.event_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    def get(self, owner_id: UUID, event_id: str, raw_proposal_id: str) -> Proposal:
        event = self._event_service.get(owner_id, event_id)
        proposal_id = self._parse_identifier(raw_proposal_id, _PROPOSAL_NOT_FOUND)
        proposal = self._repository.get(proposal_id, event.event_id, owner_id)
        if proposal is None:
            raise ResourceNotFoundError(_PROPOSAL_NOT_FOUND)
        return proposal

    def approve(
        self,
        owner_id: UUID,
        event_id: str,
        raw_proposal_id: str,
        request: ProposalApprovalRequest,
    ) -> ProposalApprovalResponse:
        event = self._event_service.get(owner_id, event_id)
        proposal = self.get(owner_id, event_id, raw_proposal_id)
        now = self._now()

        if proposal.status in {ProposalStatus.REJECTED, ProposalStatus.EXPIRED}:
            raise ResourceConflictError("This proposal can no longer be approved.")
        if proposal.expires_at <= now and proposal.status in {
            ProposalStatus.PENDING,
            ProposalStatus.PARTIALLY_APPROVED,
        }:
            self._expire(proposal, now)
            raise ResourceConflictError("This proposal has expired.")

        items = [dict(item) for item in proposal.payload.get("items", [])]
        by_id = {item["item_id"]: item for item in items}
        requested_ids = (
            [str(item_id) for item_id in request.item_ids]
            if request.item_ids is not None
            else [item["item_id"] for item in items]
        )
        unknown = [item_id for item_id in requested_ids if item_id not in by_id]
        if unknown:
            raise DomainValidationError(
                [
                    ValidationIssue(
                        field="body.item_ids",
                        message="One or more proposal items do not belong to this proposal.",
                    )
                ]
            )

        if proposal.status == ProposalStatus.APPROVED:
            skipped = [
                AppliedItemResult(
                    item_id=item["item_id"],
                    action_type=ProposalActionType(item["action_type"]),
                    status="skipped",
                    message="This proposal was already fully approved.",
                )
                for item in items
                if item["item_id"] in requested_ids
            ]
            return ProposalApprovalResponse(
                proposal=ProposalResponse.from_proposal(proposal),
                applied=[],
                skipped=skipped,
                rejected=[],
            )

        if self._is_stale(owner_id, event, proposal):
            raise ResourceConflictError(
                "The event changed after this proposal was generated; regenerate it."
            )

        applied: list[AppliedItemResult] = []
        skipped: list[AppliedItemResult] = []
        rejected: list[AppliedItemResult] = []
        changed = False

        for item in items:
            if item["item_id"] not in requested_ids:
                continue
            action_type = ProposalActionType(item["action_type"])
            item_status = ProposalItemStatus(item["status"])

            if item_status == ProposalItemStatus.APPLIED:
                skipped.append(
                    AppliedItemResult(
                        item_id=item["item_id"],
                        action_type=action_type,
                        status="skipped",
                        message="This item was already applied.",
                        resource_id=item.get("resource_id"),
                    )
                )
                continue
            if item_status == ProposalItemStatus.REJECTED:
                rejected.append(
                    AppliedItemResult(
                        item_id=item["item_id"],
                        action_type=action_type,
                        status="rejected",
                        message=item.get("result_message") or "This item was rejected.",
                    )
                )
                continue
            if item_status == ProposalItemStatus.SKIPPED:
                skipped.append(
                    AppliedItemResult(
                        item_id=item["item_id"],
                        action_type=action_type,
                        status="skipped",
                        message=item.get("result_message") or "This item was skipped.",
                    )
                )
                continue

            try:
                outcome = self._apply_item(
                    owner_id,
                    event,
                    proposal,
                    item,
                    action_type,
                    allow_advisory=request.allow_advisory,
                )
            except DomainValidationError as exc:
                message = (
                    exc.issues[0].message
                    if exc.issues
                    else "The proposed action is no longer valid."
                )
                outcome = self._result(item["item_id"], action_type, "skipped", message)
            except ResourceNotFoundError:
                outcome = self._result(
                    item["item_id"],
                    action_type,
                    "skipped",
                    "The referenced resource no longer exists.",
                )
            changed = True
            item["status"] = outcome.status
            item["result_message"] = outcome.message
            if outcome.resource_id is not None:
                item["resource_id"] = outcome.resource_id
            if outcome.status == "applied":
                item["applied_at"] = now.isoformat()
                applied.append(outcome)
            elif outcome.status == "rejected":
                rejected.append(outcome)
            else:
                skipped.append(outcome)

        if not changed:
            return ProposalApprovalResponse(
                proposal=ProposalResponse.from_proposal(proposal),
                applied=applied,
                skipped=skipped,
                rejected=rejected,
            )

        remaining_pending = any(
            ProposalItemStatus(item["status"]) == ProposalItemStatus.PENDING for item in items
        )
        new_status = (
            ProposalStatus.PARTIALLY_APPROVED
            if remaining_pending
            else ProposalStatus.APPROVED
        )
        snapshot = self._snapshot(owner_id, event)
        updated = replace(
            proposal,
            payload={"items": items},
            status=new_status,
            version=proposal.version + 1,
            source_snapshot=snapshot,
            updated_at=max(now, proposal.updated_at + timedelta(microseconds=1)),
            approved_at=proposal.approved_at or now,
        )
        saved = self._repository.update(
            owner_id,
            updated,
            expected_version=proposal.version,
        )
        if saved is None:
            raise ResourceConflictError(
                "The proposal was modified by another request; refresh and retry."
            )
        return ProposalApprovalResponse(
            proposal=ProposalResponse.from_proposal(saved),
            applied=applied,
            skipped=skipped,
            rejected=rejected,
        )

    def reject(
        self,
        owner_id: UUID,
        event_id: str,
        raw_proposal_id: str,
        request: ProposalRejectRequest,
    ) -> ProposalRejectResponse:
        self._event_service.get(owner_id, event_id)
        proposal = self.get(owner_id, event_id, raw_proposal_id)
        now = self._now()

        if proposal.status in {ProposalStatus.APPROVED, ProposalStatus.REJECTED}:
            if proposal.status == ProposalStatus.REJECTED:
                return ProposalRejectResponse(
                    proposal=ProposalResponse.from_proposal(proposal),
                    rejected_items=[],
                    message="This proposal was already rejected.",
                )
            raise ResourceConflictError("An approved proposal cannot be rejected.")
        if proposal.status == ProposalStatus.EXPIRED or proposal.expires_at <= now:
            if proposal.status != ProposalStatus.EXPIRED:
                self._expire(proposal, now)
            raise ResourceConflictError("This proposal has expired.")

        items = [dict(item) for item in proposal.payload.get("items", [])]
        by_id = {item["item_id"]: item for item in items}
        requested_ids = (
            [str(item_id) for item_id in request.item_ids]
            if request.item_ids is not None
            else [
                item["item_id"]
                for item in items
                if ProposalItemStatus(item["status"]) == ProposalItemStatus.PENDING
            ]
        )
        if any(item_id not in by_id for item_id in requested_ids):
            raise DomainValidationError(
                [
                    ValidationIssue(
                        field="body.item_ids",
                        message="One or more proposal items do not belong to this proposal.",
                    )
                ]
            )

        rejected_items: list[str] = []
        reason = request.reason or "Rejected by the event owner."
        for item in items:
            if item["item_id"] not in requested_ids:
                continue
            if ProposalItemStatus(item["status"]) != ProposalItemStatus.PENDING:
                continue
            item["status"] = ProposalItemStatus.REJECTED.value
            item["result_message"] = reason
            rejected_items.append(item["item_id"])

        if not rejected_items:
            return ProposalRejectResponse(
                proposal=ProposalResponse.from_proposal(proposal),
                rejected_items=[],
                message="No pending items were rejected.",
            )

        remaining_pending = any(
            ProposalItemStatus(item["status"]) == ProposalItemStatus.PENDING for item in items
        )
        new_status = (
            ProposalStatus.PARTIALLY_APPROVED
            if remaining_pending
            else ProposalStatus.REJECTED
        )
        updated = replace(
            proposal,
            payload={"items": items},
            status=new_status,
            version=proposal.version + 1,
            updated_at=max(now, proposal.updated_at + timedelta(microseconds=1)),
            rejected_at=now if not remaining_pending else proposal.rejected_at,
        )
        saved = self._repository.update(
            owner_id,
            updated,
            expected_version=proposal.version,
        )
        if saved is None:
            raise ResourceConflictError(
                "The proposal was modified by another request; refresh and retry."
            )
        return ProposalRejectResponse(
            proposal=ProposalResponse.from_proposal(saved),
            rejected_items=rejected_items,
            message="Selected proposal items were rejected.",
        )

    def applied_recommendations(
        self,
        owner_id: UUID,
        event_id: str,
        *,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return only owner-approved, applied advisory text for reports."""
        event = self._event_service.get(owner_id, event_id)
        proposals, _ = self._repository.list(
            owner_id,
            event.event_id,
            status=None,
            limit=limit,
            offset=0,
        )
        recommendations: list[dict[str, Any]] = []
        for proposal in proposals:
            if proposal.status not in {
                ProposalStatus.APPROVED,
                ProposalStatus.PARTIALLY_APPROVED,
            }:
                continue
            for item in proposal.payload.get("items", []):
                if ProposalItemStatus(item.get("status")) != ProposalItemStatus.APPLIED:
                    continue
                action_type = ProposalActionType(item["action_type"])
                if action_type not in {
                    ProposalActionType.BUDGET_ALLOCATION_SUGGESTION,
                    ProposalActionType.ADVISORY,
                }:
                    continue
                data = item.get("data", {})
                recommendations.append(
                    {
                        "proposal_title": proposal.title,
                        "action_type": action_type.value,
                        "label": item.get("label", "Recommendation"),
                        "details": data.get("details")
                        or data.get("rationale")
                        or data.get("description")
                        or "",
                        "amount": data.get("amount"),
                        "currency": data.get("currency"),
                        "advisory": True,
                    }
                )
        return recommendations

    def _apply_item(
        self,
        owner_id: UUID,
        event: Event,
        proposal: Proposal,
        item: dict[str, Any],
        action_type: ProposalActionType,
        *,
        allow_advisory: bool,
    ) -> AppliedItemResult:
        item_id = item["item_id"]
        data = dict(item.get("data") or {})
        template_key = f"proposal:{proposal.proposal_id}:{item_id}"

        if action_type in {
            ProposalActionType.ADD_TASK,
            ProposalActionType.ADD_VENDOR_FOLLOW_UP_TASK,
        }:
            vendor = None
            if action_type == ProposalActionType.ADD_VENDOR_FOLLOW_UP_TASK:
                if self._vendor_service is None:
                    return self._result(
                        item_id,
                        action_type,
                        "skipped",
                        "Vendor workflow is unavailable.",
                    )
                vendor = self._vendor_service.get(
                    owner_id,
                    str(event.event_id),
                    str(data.get("vendor_id", "")),
                )
                if vendor.status.value in {"rejected", "cancelled"}:
                    return self._result(
                        item_id,
                        action_type,
                        "skipped",
                        "The vendor is no longer active.",
                    )
            try:
                payload = TaskCreate(
                    title=data["title"],
                    description=data.get("description"),
                    priority=_PRIORITY_MAP.get(str(data.get("priority", "medium")), TaskPriority.MEDIUM),
                    due_at=data.get("due_at"),
                )
            except (KeyError, ValidationError):
                return self._result(
                    item_id,
                    action_type,
                    "skipped",
                    "The proposed task is no longer valid.",
                )
            self._validate_task_due_date(event, payload.due_at)
            task = self._task_service.create_generated_task(
                owner_id,
                event,
                template_key=template_key,
                title=payload.title,
                description=payload.description,
                priority=payload.priority,
                due_at=payload.due_at,
            )
            message = (
                f"Created a follow-up task for {vendor.name}."
                if vendor is not None
                else "Created the proposed planning task."
            )
            return self._result(
                item_id,
                action_type,
                "applied",
                message,
                resource_id=str(task.task_id),
            )

        if action_type == ProposalActionType.UPDATE_TASK_DUE_DATE:
            try:
                task_id = str(data["task_id"])
                due_at = self._parse_datetime(data["due_at"])
            except (KeyError, ValueError):
                return self._result(
                    item_id,
                    action_type,
                    "skipped",
                    "The proposed due-date change is invalid.",
                )
            try:
                task = self._task_service.get(owner_id, str(event.event_id), task_id)
            except ResourceNotFoundError:
                return self._result(
                    item_id,
                    action_type,
                    "skipped",
                    "The target task no longer exists.",
                )
            if task.status == TaskStatus.COMPLETED:
                return self._result(
                    item_id,
                    action_type,
                    "skipped",
                    "Completed tasks are never modified by a proposal.",
                )
            expected_due_at = data.get("expected_due_at")
            if expected_due_at is not None:
                expected = self._parse_datetime(expected_due_at)
                if task.due_at != expected:
                    return self._result(
                        item_id,
                        action_type,
                        "skipped",
                        "The task due date was edited by the user; the suggestion was not applied.",
                    )
            self._validate_task_due_date(event, due_at)
            from app.schemas.task import TaskUpdate

            updated = self._task_service.update(
                owner_id,
                str(event.event_id),
                task_id,
                TaskUpdate(due_at=due_at),
            )
            return self._result(
                item_id,
                action_type,
                "applied",
                "Updated the task due date.",
                resource_id=str(updated.task_id),
            )

        if action_type == ProposalActionType.BUDGET_ALLOCATION_SUGGESTION:
            self._validate_budget_suggestion(event, data)
            if not allow_advisory:
                return self._result(
                    item_id,
                    action_type,
                    "skipped",
                    "Advisory budget suggestions were not approved.",
                )
            return self._result(
                item_id,
                action_type,
                "applied",
                "Recorded as advice only; no budget or expense records were changed.",
            )

        if action_type == ProposalActionType.ADVISORY:
            return self._result(
                item_id,
                action_type,
                "applied",
                "Recorded as an approved planning recommendation.",
            )

        return self._result(
            item_id,
            action_type,
            "skipped",
            "Unsupported proposal action.",
        )

    def _items_from_plan(self, plan: AIPlanResponse, event: Event) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        seen_titles: set[str] = set()

        def add_item(action_type: ProposalActionType, label: str, data: dict[str, Any]) -> None:
            if len(items) >= _MAX_ITEMS:
                return
            items.append(
                {
                    "item_id": str(uuid4()),
                    "action_type": action_type.value,
                    "status": ProposalItemStatus.PENDING.value,
                    "label": label[:200],
                    "data": data,
                    "applied_at": None,
                    "result_message": None,
                }
            )

        for suggestion in plan.task_suggestions:
            key = suggestion.title.strip().lower()
            if key in seen_titles:
                continue
            seen_titles.add(key)
            add_item(
                ProposalActionType.ADD_TASK,
                suggestion.title,
                {
                    "title": suggestion.title,
                    "description": suggestion.explanation,
                    "priority": _PRIORITY_MAP.get(suggestion.priority.value, TaskPriority.MEDIUM).value,
                    "due_at": None,
                    "suggested_timing": suggestion.suggested_timing,
                    "relative_deadline": suggestion.relative_deadline,
                },
            )

        for suggestion in plan.vendor_category_suggestions:
            title = f"Research {suggestion.category} vendors"
            key = title.lower()
            if key in seen_titles:
                continue
            seen_titles.add(key)
            add_item(
                ProposalActionType.ADD_TASK,
                title,
                {
                    "title": title[:200],
                    "description": suggestion.rationale,
                    "priority": _PRIORITY_MAP.get(suggestion.priority.value, TaskPriority.MEDIUM).value,
                    "due_at": None,
                },
            )

        for suggestion in plan.budget_suggestions:
            if suggestion.currency != event.currency:
                continue
            add_item(
                ProposalActionType.BUDGET_ALLOCATION_SUGGESTION,
                f"Budget advice: {suggestion.category}",
                {
                    "category": suggestion.category,
                    "description": suggestion.description,
                    "rationale": suggestion.rationale,
                    "amount": str(suggestion.suggested_amount)
                    if suggestion.suggested_amount is not None
                    else None,
                    "currency": suggestion.currency,
                    "source": suggestion.source.value,
                },
            )

        for recommendation in plan.recommendations:
            add_item(
                ProposalActionType.ADVISORY,
                recommendation.category,
                {
                    "category": recommendation.category,
                    "description": recommendation.description,
                    "rationale": recommendation.rationale,
                    "details": recommendation.description,
                    "priority": recommendation.priority.value,
                },
            )

        for suggestion in plan.timeline_suggestions:
            add_item(
                ProposalActionType.ADVISORY,
                "Timeline improvement",
                {"details": suggestion, "category": "Timeline"},
            )

        if final_summary := plan.next_steps:
            add_item(
                ProposalActionType.ADVISORY,
                "Next steps",
                {"details": " ".join(final_summary)[:2000], "category": "Next steps"},
            )

        return items

    def _validate_budget_suggestion(self, event: Event, data: dict[str, Any]) -> None:
        currency = str(data.get("currency", event.currency)).upper()
        if currency != event.currency:
            raise DomainValidationError(
                [
                    ValidationIssue(
                        field="body.currency",
                        message="Budget suggestions must use the event currency.",
                    )
                ]
            )
        amount = data.get("amount")
        if amount is None:
            return
        try:
            parsed = Decimal(str(amount))
        except (InvalidOperation, ValueError) as exc:
            raise DomainValidationError(
                [ValidationIssue(field="body.amount", message="Invalid suggested amount.")]
            ) from exc
        if not parsed.is_finite() or parsed < 0 or parsed > MAX_MONEY:
            raise DomainValidationError(
                [
                    ValidationIssue(
                        field="body.amount",
                        message="Suggested amount is outside the supported range.",
                    )
                ]
            )

    def _validate_task_due_date(self, event: Event, due_at: datetime | None) -> None:
        if due_at is None:
            return
        local_date = due_at.astimezone(ZoneInfo(event.timezone)).date()
        if local_date > event.event_date:
            raise DomainValidationError(
                [
                    ValidationIssue(
                        field="body.due_at",
                        message="Proposed task dates cannot be after the event date.",
                    )
                ]
            )

    def _snapshot(self, owner_id: UUID, event: Event) -> dict[str, Any]:
        try:
            budget = self._budget_service.get(owner_id, str(event.event_id))
        except ResourceNotFoundError:
            budget_version = None
        else:
            budget_version = budget.budget.version
        _, task_total = self._task_service.list_tasks(
            owner_id,
            str(event.event_id),
            status=None,
            priority=None,
            timeline_id=None,
            limit=1,
            offset=0,
        )
        vendor_total = 0
        if self._vendor_service is not None:
            _, vendor_total = self._vendor_service.list(
                owner_id,
                str(event.event_id),
                category=None,
                status=None,
                min_price=None,
                max_price=None,
                name=None,
                limit=1,
                offset=0,
            )
        return {
            "event_updated_at": event.updated_at.isoformat(),
            "budget_version": budget_version,
            "task_count": task_total,
            "vendor_count": vendor_total,
        }

    def _is_stale(self, owner_id: UUID, event: Event, proposal: Proposal) -> bool:
        current = self._snapshot(owner_id, event)
        snapshot = proposal.source_snapshot
        if snapshot.get("event_updated_at") != current["event_updated_at"]:
            return True
        if snapshot.get("budget_version") != current["budget_version"]:
            return True
        if int(snapshot.get("task_count", 0)) != current["task_count"]:
            return True
        return int(snapshot.get("vendor_count", 0)) != current["vendor_count"]

    def _expire(self, proposal: Proposal, now: datetime) -> None:
        expired = replace(
            proposal,
            status=ProposalStatus.EXPIRED,
            version=proposal.version + 1,
            updated_at=max(now, proposal.updated_at + timedelta(microseconds=1)),
        )
        self._repository.update(
            proposal.owner_id,
            expired,
            expected_version=proposal.version,
        )

    @staticmethod
    def _parse_datetime(value: object) -> datetime:
        if isinstance(value, datetime):
            return coerce_utc(value)
        if isinstance(value, str):
            return coerce_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
        raise ValueError("Invalid datetime.")

    @staticmethod
    def _result(
        item_id: str,
        action_type: ProposalActionType,
        status: str,
        message: str,
        *,
        resource_id: str | None = None,
    ) -> AppliedItemResult:
        return AppliedItemResult(
            item_id=item_id,
            action_type=action_type,
            status=status,
            message=message,
            resource_id=resource_id,
        )

    def _now(self) -> datetime:
        return coerce_utc(self._clock())

    @staticmethod
    def _parse_identifier(raw_identifier: str, not_found_message: str) -> UUID:
        if len(raw_identifier) != 36:
            raise ResourceNotFoundError(not_found_message)
        try:
            identifier = UUID(raw_identifier)
        except ValueError:
            raise ResourceNotFoundError(not_found_message) from None
        if str(identifier) != raw_identifier.lower():
            raise ResourceNotFoundError(not_found_message)
        return identifier
