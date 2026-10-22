"""Event use cases, policies, and server-managed fields."""

from dataclasses import replace
from datetime import date, datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from app.core.clock import Clock, coerce_utc, utc_now
from app.core.exceptions import DomainValidationError, ResourceNotFoundError, ValidationIssue
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

    def create(self, payload: EventCreate) -> Event:
        now = self._now()
        self._validate_event_date(payload.event_date, now)
        event = Event(
            event_id=uuid4(),
            name=payload.name,
            event_type=payload.event_type,
            event_date=payload.event_date,
            location=payload.location,
            guest_count=payload.guest_count,
            budget_amount=payload.budget_amount,
            currency=payload.currency,
            description=payload.description,
            preferences=tuple(payload.preferences),
            constraints=tuple(payload.constraints),
            created_at=now,
            updated_at=now,
        )
        return self._repository.save(event)

    def get(self, raw_event_id: str) -> Event:
        event_id = self._parse_event_id(raw_event_id)
        event = self._repository.get(event_id)
        if event is None:
            raise ResourceNotFoundError(_NOT_FOUND_MESSAGE)
        return event

    def list_events(self, *, limit: int, offset: int) -> tuple[list[Event], int]:
        return self._repository.list(limit=limit, offset=offset)

    def update(self, raw_event_id: str, payload: EventUpdate) -> Event:
        event_id = self._parse_event_id(raw_event_id)
        event = self._repository.get(event_id)
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
        if changes.get("event_date") is not None:
            self._validate_event_date(changes["event_date"], now)

        if changes.get("preferences") is not None:
            changes["preferences"] = tuple(changes["preferences"])
        if changes.get("constraints") is not None:
            changes["constraints"] = tuple(changes["constraints"])

        candidate = replace(event, **changes)
        if candidate == event:
            return event

        updated_at = max(now, event.updated_at + timedelta(microseconds=1))
        updated = self._repository.update(replace(candidate, updated_at=updated_at))
        if updated is None:
            raise ResourceNotFoundError(_NOT_FOUND_MESSAGE)
        return updated

    def delete(self, raw_event_id: str) -> None:
        event_id = self._parse_event_id(raw_event_id)
        if not self._repository.delete(event_id):
            raise ResourceNotFoundError(_NOT_FOUND_MESSAGE)

    def _now(self) -> datetime:
        return coerce_utc(self._clock())

    def _validate_event_date(self, event_date: date, now: datetime) -> None:
        today = now.astimezone(self._timezone).date()
        if event_date < today:
            raise DomainValidationError(
                [
                    ValidationIssue(
                        field="body.event_date",
                        message=(
                            "Event date must be today or later in the configured "
                            f"timezone ({self._timezone.key})."
                        ),
                    )
                ]
            )

    @staticmethod
    def _parse_event_id(raw_event_id: str) -> UUID:
        if len(raw_event_id) != 36:
            raise ResourceNotFoundError(_NOT_FOUND_MESSAGE)
        try:
            event_id = UUID(raw_event_id)
        except ValueError:
            raise ResourceNotFoundError(_NOT_FOUND_MESSAGE) from None
        if str(event_id) != raw_event_id.lower():
            raise ResourceNotFoundError(_NOT_FOUND_MESSAGE)
        return event_id
