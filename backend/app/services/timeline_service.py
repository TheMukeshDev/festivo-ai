"""Planning timeline use cases."""

from dataclasses import replace
from datetime import timedelta
from uuid import UUID, uuid4

from app.core.clock import Clock, coerce_utc, utc_now
from app.core.exceptions import DomainValidationError, ResourceNotFoundError, ValidationIssue
from app.models.event import Event
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.timeline import Timeline
from app.repositories.event_repository import EventRepository
from app.repositories.planning_repository import PlanningRepository
from app.services.event_service import EventService

_EVENT_NOT_FOUND = "Event not found."
_TIMELINE_NOT_FOUND = "Timeline not found."
_TIMELINE_EXISTS = "An event timeline already exists."

_TEMPLATE_TASKS = [
    (
        "venue",
        "Book the venue",
        "Reserve the venue and confirm the contract details.",
        TaskPriority.HIGH,
        0,
    ),
    (
        "catering",
        "Finalize catering",
        "Confirm menu, guest count split, and dietary requirements.",
        TaskPriority.HIGH,
        1,
    ),
    (
        "decor",
        "Plan decoration and theme",
        "Finalize decor items and assign setup responsibilities.",
        TaskPriority.MEDIUM,
        2,
    ),
    (
        "photography",
        "Book photography and videography",
        "Compare quotes and confirm coverage hours.",
        TaskPriority.HIGH,
        3,
    ),
    (
        "entertainment",
        "Arrange entertainment",
        "Book music or activities suited to the event.",
        TaskPriority.MEDIUM,
        4,
    ),
    (
        "invitations",
        "Send invitations",
        "Prepare and distribute invitations with RSVP tracking.",
        TaskPriority.MEDIUM,
        5,
    ),
    (
        "logistics",
        "Arrange transport and logistics",
        "Plan travel, parking, and equipment delivery/pickup.",
        TaskPriority.MEDIUM,
        6,
    ),
    (
        "final-check",
        "Run a final readiness check",
        "Verify vendors, timeline, budget, and guest list a few days before.",
        TaskPriority.HIGH,
        7,
    ),
]


class TimelineService:
    """Coordinate deterministic timeline generation and ownership checks."""

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

    def generate(self, owner_id: UUID, raw_event_id: str) -> tuple[Timeline, list[Task]]:
        event = self._require_event(owner_id, raw_event_id)
        existing = self._planning_repository.get_timeline(event.event_id, owner_id)
        if existing is not None:
            raise DomainValidationError(
                [
                    ValidationIssue(
                        field="body.event_id",
                        message=_TIMELINE_EXISTS,
                    )
                ]
            )
        now = self._now()
        timeline = Timeline(
            timeline_id=uuid4(),
            event_id=event.event_id,
            owner_id=owner_id,
            start_date=event.event_date - timedelta(days=90),
            end_date=event.event_date,
            timezone=event.timezone,
            generated_at=now,
            created_at=now,
            updated_at=now,
        )
        tasks = self._build_tasks(event, timeline, now)
        return self._planning_repository.create_timeline(timeline, tasks)

    def get(self, owner_id: UUID, raw_event_id: str) -> Timeline:
        event = self._require_event(owner_id, raw_event_id)
        timeline = self._planning_repository.get_timeline(event.event_id, owner_id)
        if timeline is None:
            raise ResourceNotFoundError(_TIMELINE_NOT_FOUND)
        return timeline

    def regenerate(self, owner_id: UUID, raw_event_id: str) -> tuple[Timeline, list[Task]]:
        event = self._require_event(owner_id, raw_event_id)
        timeline = self._planning_repository.get_timeline(event.event_id, owner_id)
        if timeline is None:
            raise ResourceNotFoundError(_TIMELINE_NOT_FOUND)
        now = self._now()
        updated_timeline = replace(
            timeline,
            start_date=event.event_date - timedelta(days=90),
            end_date=event.event_date,
            timezone=event.timezone,
            updated_at=now,
        )
        tasks = self._build_tasks(event, updated_timeline, now)
        return self._planning_repository.add_generated_tasks(
            owner_id,
            updated_timeline,
            tasks,
            generated_at=now,
        )

    def _build_tasks(self, event: Event, timeline: Timeline, now: object) -> list[Task]:
        tasks: list[Task] = []
        for template_key, title, description, priority, offset in _TEMPLATE_TASKS:
            task = Task(
                task_id=uuid4(),
                event_id=event.event_id,
                owner_id=event.owner_id,
                timeline_id=timeline.timeline_id,
                template_key=f"timeline:{template_key}",
                title=title,
                description=description,
                status=TaskStatus.PENDING,
                priority=priority,
                due_at=None,
                assigned_to=None,
                estimated_cost=None,
                actual_cost=None,
                currency=event.currency,
                sort_order=offset * 10,
                completed_at=None,
                created_at=now,
                updated_at=now,
            )
            tasks.append(task)
        return tasks

    def _require_event(self, owner_id: UUID, raw_event_id: str) -> Event:
        event_id = self._parse_identifier(raw_event_id, _EVENT_NOT_FOUND)
        event = self._event_repository.get(event_id, owner_id)
        if event is None:
            raise ResourceNotFoundError(_EVENT_NOT_FOUND)
        return event

    def _now(self):
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
