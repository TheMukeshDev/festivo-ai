"""Event use cases, policies, and server-managed fields."""

from dataclasses import replace
from datetime import date, datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from app.core.clock import Clock, coerce_utc, utc_now
from app.core.exceptions import DomainValidationError, ResourceNotFoundError, ValidationIssue
from app.core.ids import parse_uuid
from app.models.event import Event
from app.repositories.event_repository import EventRepository
from app.schemas.event import EventCreate, EventUpdate

_NOT_FOUND_MESSAGE = "Event not found."


class EventService:
    """Coordinate event validation, identifiers, timestamps, and persistence."""

    def __init__(
        self,
        repository: EventRepository,
        timezone: ZoneInfo,
        clock: Clock | None = None,
    ) -> None:
        self._repository = repository
        self._timezone = timezone
        self._clock = clock or utc_now

    def create(self, owner_id: UUID, payload: EventCreate) -> Event:
        now = self._now()
        timezone = payload.timezone or self._timezone.key
        self._validate_event_date(payload.event_date, now, timezone)
        event = Event(
            event_id=uuid4(),
            owner_id=owner_id,
            name=payload.name,
            event_type=payload.event_type,
            event_date=payload.event_date,
            location=payload.location,
            guest_count=payload.guest_count,
            budget_amount=payload.budget_amount,
            currency=payload.currency,
            timezone=timezone,
            description=payload.description,
            preferences=tuple(payload.preferences),
            constraints=tuple(payload.constraints),
            created_at=now,
            updated_at=now,
        )
        return self._repository.save(event)

    def get(self, owner_id: UUID, raw_event_id: str) -> Event:
        event_id = parse_uuid(raw_event_id, _NOT_FOUND_MESSAGE)
        event = self._repository.get(event_id, owner_id)
        if event is None:
            raise ResourceNotFoundError(_NOT_FOUND_MESSAGE)
        return event

    def list_events(
        self,
        owner_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[Event], int]:
        return self._repository.list(owner_id, limit=limit, offset=offset)

    def update(self, owner_id: UUID, raw_event_id: str, payload: EventUpdate) -> Event:
        event_id = parse_uuid(raw_event_id, _NOT_FOUND_MESSAGE)
        event = self._repository.get(event_id, owner_id)
        if event is None:
            raise ResourceNotFoundError(_NOT_FOUND_MESSAGE)

        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            return event

        issues = [
            ValidationIssue(
                field=f"body.{field}",
                message="This field cannot be null.",
            )
            for field, value in changes.items()
            if value is None and field != "description"
        ]
        if issues:
            raise DomainValidationError(issues)

        now = self._now()
        if changes.get("event_date") is not None or changes.get("timezone") is not None:
            self._validate_event_date(
                changes.get("event_date", event.event_date),
                now,
                changes.get("timezone", event.timezone),
            )

        if changes.get("preferences") is not None:
            changes["preferences"] = tuple(changes["preferences"])
        if changes.get("constraints") is not None:
            changes["constraints"] = tuple(changes["constraints"])

        candidate = replace(event, **changes)
        if candidate == event:
            return event

        updated_at = max(now, event.updated_at + timedelta(microseconds=1))
        updated = self._repository.update(
            owner_id,
            replace(candidate, updated_at=updated_at),
        )
        if updated is None:
            raise ResourceNotFoundError(_NOT_FOUND_MESSAGE)
        return updated

    def delete(self, owner_id: UUID, raw_event_id: str) -> None:
        event_id = parse_uuid(raw_event_id, _NOT_FOUND_MESSAGE)
        if not self._repository.delete(event_id, owner_id):
            raise ResourceNotFoundError(_NOT_FOUND_MESSAGE)

    def _now(self) -> datetime:
        return coerce_utc(self._clock())

    @staticmethod
    def _validate_event_date(event_date: date, now: datetime, timezone: str) -> None:
        today = now.astimezone(ZoneInfo(timezone)).date()
        if event_date < today:
            raise DomainValidationError(
                [
                    ValidationIssue(
                        field="body.event_date",
                        message=(
                            f"Event date must be today or later in the event timezone ({timezone})."
                        ),
                    )
                ]
            )
