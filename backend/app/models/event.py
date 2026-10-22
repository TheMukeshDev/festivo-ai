"""Immutable event domain model."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class EventType(StrEnum):
    """Event categories supported by the planning domain."""

    WEDDING = "wedding"
    BIRTHDAY = "birthday"
    COLLEGE_EVENT = "college_event"
    COMMUNITY_EVENT = "community_event"


@dataclass(frozen=True, slots=True)
class Event:
    """A stored celebration event with server-managed identity and timestamps."""

    event_id: UUID
    name: str
    event_type: EventType
    event_date: date
    location: str
    guest_count: int
    budget_amount: Decimal
    currency: str
    description: str | None
    preferences: tuple[str, ...]
    constraints: tuple[str, ...]
    created_at: datetime
    updated_at: datetime
