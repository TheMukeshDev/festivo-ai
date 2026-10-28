"""Planning task use cases, including idempotent vendor follow-up tasks."""

from dataclasses import replace
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from app.core.clock import Clock, coerce_utc, utc_now
from app.core.exceptions import (
    DomainValidationError,
    ResourceConflictError,
    ResourceNotFoundError,
    ValidationIssue,
)
from app.core.ids import parse_uuid
from app.models.event import Event
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.vendor import Vendor, VendorStatus
from app.repositories.event_repository import EventRepository
from app.repositories.planning_repository import PlanningRepository
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.event_service import EventService

_EVENT_NOT_FOUND = "Event not found."
_TASK_NOT_FOUND = "Task not found."

_VENDOR_STAGE_ORDER = (
    VendorStatus.SHORTLISTED,
    VendorStatus.CONTACTED,
    VendorStatus.QUOTED,
    VendorStatus.SELECTED,
    VendorStatus.BOOKED,
)

_VENDOR_TASK_TEMPLATES: dict[VendorStatus, tuple[tuple[str, str, str, TaskPriority], ...]] = {
    VendorStatus.SHORTLISTED: (
        (
            "contact",
            "Contact {vendor}",
            "Contact {vendor} about your event requirements. Festivo has not contacted them.",
            TaskPriority.MEDIUM,
        ),
    ),
    VendorStatus.CONTACTED: (
        (
            "quote",
            "Request a detailed quote from {vendor}",
            "Ask {vendor} for a written quote covering the agreed service scope.",
            TaskPriority.HIGH,
        ),
    ),
    VendorStatus.QUOTED: (
        (
            "scope",
            "Confirm service scope with {vendor}",
            "Review the quote and confirm exactly what {vendor} will provide.",
            TaskPriority.HIGH,
        ),
    ),
    VendorStatus.SELECTED: (
        (
            "availability",
            "Verify availability directly with {vendor}",
            "Confirm dates and availability with {vendor} directly.",
            TaskPriority.HIGH,
        ),
        (
            "cancellation",
            "Review cancellation terms for {vendor}",
            "Read the cancellation and rescheduling terms before booking.",
            TaskPriority.MEDIUM,
        ),
    ),
    VendorStatus.BOOKED: (
        (
            "booking",
            "Confirm booking details with {vendor}",
            "Record the booking reference, contact, and agreed scope. "
            "Festivo has not verified this booking externally.",
            TaskPriority.HIGH,
        ),
        (
            "payment",
            "Track remaining payment deadlines for {vendor}",
            "Record any payment schedule supplied by {vendor} and track upcoming deadlines.",
            TaskPriority.MEDIUM,
        ),
    ),
}


class TaskService:
    """Coordinate task validation, ownership, and deterministic checklist generation."""

    def __init__(
        self,
        event_repository: EventRepository,
        planning_repository: PlanningRepository,
        event_service: EventService,
        clock: Clock | None = None,
    ) -> None:
        self._event_repository = event_repository
        self._planning_repository = planning_repository
        self._event_service = event_service
        self._clock = clock or utc_now

    def create(self, owner_id: UUID, raw_event_id: str, payload: TaskCreate) -> Task:
        event = self._require_event(owner_id, raw_event_id)
        now = self._now()
        status = payload.status
        completed_at = now if status == TaskStatus.COMPLETED else None
        task = Task(
            task_id=uuid4(),
            event_id=event.event_id,
            owner_id=owner_id,
            timeline_id=None,
            template_key=None,
            title=payload.title,
            description=payload.description,
            status=status,
            priority=payload.priority,
            due_at=payload.due_at,
            assigned_to=payload.assigned_to,
            estimated_cost=payload.estimated_cost,
            actual_cost=payload.actual_cost,
            currency=event.currency,
            sort_order=self._next_sort_order(owner_id, event.event_id),
            completed_at=completed_at,
            created_at=now,
            updated_at=now,
        )
        return self._planning_repository.create_task(task)

    def get(self, owner_id: UUID, raw_event_id: str, raw_task_id: str) -> Task:
        event = self._require_event(owner_id, raw_event_id)
        task_id = parse_uuid(raw_task_id, _TASK_NOT_FOUND)
        task = self._planning_repository.get_task(task_id, event.event_id, owner_id)
        if task is None:
            raise ResourceNotFoundError(_TASK_NOT_FOUND)
        return task

    def list_tasks(
        self,
        owner_id: UUID,
        raw_event_id: str,
        *,
        status: TaskStatus | None,
        priority: TaskPriority | None,
        timeline_id: UUID | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Task], int]:
        event = self._require_event(owner_id, raw_event_id)
        return self._planning_repository.list_tasks(
            owner_id,
            event.event_id,
            status=status,
            priority=priority,
            timeline_id=timeline_id,
            limit=limit,
            offset=offset,
        )

    def update(
        self,
        owner_id: UUID,
        raw_event_id: str,
        raw_task_id: str,
        payload: TaskUpdate,
    ) -> Task:
        event = self._require_event(owner_id, raw_event_id)
        task_id = parse_uuid(raw_task_id, _TASK_NOT_FOUND)
        task = self._planning_repository.get_task(task_id, event.event_id, owner_id)
        if task is None:
            raise ResourceNotFoundError(_TASK_NOT_FOUND)

        changes = payload.model_dump(exclude_unset=True)
        required_fields = {"title", "status", "priority"}
        issues = [
            ValidationIssue(field=f"body.{field}", message="This field cannot be null.")
            for field, value in changes.items()
            if value is None and field in required_fields
        ]
        if issues:
            raise DomainValidationError(issues)
        if not changes:
            return task

        now = self._now()
        if "status" in changes and changes["status"] != task.status:
            changes["completed_at"] = now if changes["status"] == TaskStatus.COMPLETED else None

        candidate = replace(task, **changes)
        if candidate == task:
            return task

        updated = self._planning_repository.update_task(
            owner_id,
            replace(candidate, updated_at=max(now, task.updated_at + timedelta(microseconds=1))),
        )
        if updated is None:
            raise ResourceNotFoundError(_TASK_NOT_FOUND)
        return updated

    def delete(self, owner_id: UUID, raw_event_id: str, raw_task_id: str) -> None:
        event = self._require_event(owner_id, raw_event_id)
        task_id = parse_uuid(raw_task_id, _TASK_NOT_FOUND)
        if not self._planning_repository.delete_task(task_id, event.event_id, owner_id):
            raise ResourceNotFoundError(_TASK_NOT_FOUND)

    def ensure_vendor_tasks(
        self,
        owner_id: UUID,
        event: Event,
        vendor: Vendor,
    ) -> list[Task]:
        """Create missing vendor follow-up tasks without touching existing tasks."""
        if vendor.status in {
            VendorStatus.DISCOVERED,
            VendorStatus.REJECTED,
            VendorStatus.CANCELLED,
        }:
            return []

        now = self._now()
        created: list[Task] = []
        sort_order = self._next_sort_order(owner_id, event.event_id)
        current_index = _VENDOR_STAGE_ORDER.index(vendor.status)
        for stage in _VENDOR_STAGE_ORDER[: current_index + 1]:
            for slug, title_template, description_template, priority in _VENDOR_TASK_TEMPLATES[
                stage
            ]:
                template_key = f"vendor:{vendor.vendor_id}:{slug}"
                existing = self._planning_repository.get_task_by_template_key(
                    owner_id,
                    event.event_id,
                    template_key,
                )
                if existing is not None:
                    continue
                task = Task(
                    task_id=uuid4(),
                    event_id=event.event_id,
                    owner_id=owner_id,
                    timeline_id=None,
                    template_key=template_key,
                    title=title_template.format(vendor=vendor.name),
                    description=description_template.format(vendor=vendor.name),
                    status=TaskStatus.PENDING,
                    priority=priority,
                    due_at=None,
                    assigned_to=None,
                    estimated_cost=None,
                    actual_cost=None,
                    currency=event.currency,
                    sort_order=sort_order,
                    completed_at=None,
                    created_at=now,
                    updated_at=now,
                )
                try:
                    created.append(self._planning_repository.create_task(task))
                except Exception as exc:
                    if exc.__class__.__name__ != "ResourceConflictError":
                        raise
                    existing = self._planning_repository.get_task_by_template_key(
                        owner_id,
                        event.event_id,
                        template_key,
                    )
                    if existing is None:
                        raise
                    continue
                sort_order += 10
        return created

    def _next_sort_order(self, owner_id: UUID, event_id: UUID) -> int:
        tasks, _ = self._planning_repository.list_tasks(
            owner_id,
            event_id,
            status=None,
            priority=None,
            timeline_id=None,
            limit=10_000,
            offset=0,
        )
        if not tasks:
            return 0
        return max(task.sort_order for task in tasks) + 10

    def _require_event(self, owner_id: UUID, raw_event_id: str) -> Event:
        event_id = parse_uuid(raw_event_id, _EVENT_NOT_FOUND)
        event = self._event_repository.get(event_id, owner_id)
        if event is None:
            raise ResourceNotFoundError(_EVENT_NOT_FOUND)
        return event

    def _now(self) -> datetime:
        return coerce_utc(self._clock())

    def create_generated_task(
        self,
        owner_id: UUID,
        event: Event,
        *,
        template_key: str,
        title: str,
        description: str | None,
        priority: TaskPriority,
        due_at: datetime | None = None,
    ) -> Task:
        """Create one idempotent proposal task without touching existing user tasks."""
        existing = self._planning_repository.get_task_by_template_key(
            owner_id,
            event.event_id,
            template_key,
        )
        if existing is not None:
            return existing

        now = self._now()
        task = Task(
            task_id=uuid4(),
            event_id=event.event_id,
            owner_id=owner_id,
            timeline_id=None,
            template_key=template_key,
            title=title,
            description=description,
            status=TaskStatus.PENDING,
            priority=priority,
            due_at=due_at,
            assigned_to=None,
            estimated_cost=None,
            actual_cost=None,
            currency=event.currency,
            sort_order=self._next_sort_order(owner_id, event.event_id),
            completed_at=None,
            created_at=now,
            updated_at=now,
        )
        try:
            return self._planning_repository.create_task(task)
        except ResourceConflictError:
            existing = self._planning_repository.get_task_by_template_key(
                owner_id,
                event.event_id,
                template_key,
            )
            if existing is None:
                raise
            return existing
