"""Validated event timeline response schemas."""

from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict

from app.models.timeline import Timeline


class TimelineResponse(BaseModel):
    """Server representation of an event's planning timeline."""

    model_config = ConfigDict(extra="forbid")

    timeline_id: str
    event_id: str
    start_date: date
    end_date: date
    timezone: str
    generated_at: datetime
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_timeline(cls, timeline: Timeline) -> Self:
        """Build a response from an immutable timeline model."""
        return cls(
            timeline_id=str(timeline.timeline_id),
            event_id=str(timeline.event_id),
            start_date=timeline.start_date,
            end_date=timeline.end_date,
            timezone=timeline.timezone,
            generated_at=timeline.generated_at,
            created_at=timeline.created_at,
            updated_at=timeline.updated_at,
        )
