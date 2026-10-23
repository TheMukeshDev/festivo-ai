"""Event timeline domain model."""

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Timeline:
    """The planning window for an event."""

    timeline_id: UUID
    event_id: UUID
    owner_id: UUID
    start_date: date
    end_date: date
    timezone: str
    generated_at: datetime
    created_at: datetime
    updated_at: datetime
