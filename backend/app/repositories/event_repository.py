"""Event persistence contract and thread-safe in-memory implementation."""

import copy
from abc import ABC, abstractmethod
from threading import RLock
from uuid import UUID

from app.models.event import Event


class EventRepository(ABC):
    """Persistence contract used by the event service."""

    @abstractmethod
    def save(self, event: Event) -> Event:
        """Store an event and return an isolated copy."""

    @abstractmethod
    def get(self, event_id: UUID) -> Event | None:
        """Return an isolated event copy when it exists."""

    @abstractmethod
    def list(self, *, limit: int, offset: int) -> tuple[list[Event], int]:
        """Return a stable page of isolated event copies and the total count."""

    @abstractmethod
    def update(self, event: Event) -> Event | None:
        """Replace an existing event and return an isolated copy."""

    @abstractmethod
    def delete(self, event_id: UUID) -> bool:
        """Delete an event, returning whether it existed."""


class InMemoryEventRepository(EventRepository):
    """Process-local repository intended for development and automated tests."""

    def __init__(self) -> None:
        self._events: dict[UUID, Event] = {}
        self._lock = RLock()

    def save(self, event: Event) -> Event:
        with self._lock:
            self._events[event.event_id] = copy.deepcopy(event)
            return copy.deepcopy(event)

    def get(self, event_id: UUID) -> Event | None:
        with self._lock:
            event = self._events.get(event_id)
            return copy.deepcopy(event) if event is not None else None

    def list(self, *, limit: int, offset: int) -> tuple[list[Event], int]:
        with self._lock:
            total = len(self._events)
            page = list(self._events.values())[offset : offset + limit]
            return [copy.deepcopy(event) for event in page], total

    def update(self, event: Event) -> Event | None:
        with self._lock:
            if event.event_id not in self._events:
                return None
            self._events[event.event_id] = copy.deepcopy(event)
            return copy.deepcopy(event)

    def delete(self, event_id: UUID) -> bool:
        with self._lock:
            return self._events.pop(event_id, None) is not None
