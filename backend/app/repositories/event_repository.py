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
    def get(self, event_id: UUID, owner_id: UUID) -> Event | None:
        """Return an owned event copy when it exists."""

    @abstractmethod
    def list(
        self,
        owner_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[Event], int]:
        """Return a stable page of the owner's events and their total count."""

    @abstractmethod
    def update(self, owner_id: UUID, event: Event) -> Event | None:
        """Replace an existing owned event and return an isolated copy."""

    @abstractmethod
    def delete(self, event_id: UUID, owner_id: UUID) -> bool:
        """Delete an owned event, returning whether it existed."""


class InMemoryEventRepository(EventRepository):
    """Process-local repository intended for development and automated tests."""

    def __init__(self) -> None:
        self._events: dict[UUID, Event] = {}
        self._lock = RLock()

    def save(self, event: Event) -> Event:
        with self._lock:
            self._events[event.event_id] = copy.deepcopy(event)
            return copy.deepcopy(event)

    def get(self, event_id: UUID, owner_id: UUID) -> Event | None:
        with self._lock:
            event = self._events.get(event_id)
            if event is None or event.owner_id != owner_id:
                return None
            return copy.deepcopy(event)

    def list(
        self,
        owner_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[Event], int]:
        with self._lock:
            owned = [event for event in self._events.values() if event.owner_id == owner_id]
            total = len(owned)
            page = owned[offset : offset + limit]
            return [copy.deepcopy(event) for event in page], total

    def update(self, owner_id: UUID, event: Event) -> Event | None:
        with self._lock:
            existing = self._events.get(event.event_id)
            if existing is None or existing.owner_id != owner_id:
                return None
            self._events[event.event_id] = copy.deepcopy(event)
            return copy.deepcopy(event)

    def delete(self, event_id: UUID, owner_id: UUID) -> bool:
        with self._lock:
            existing = self._events.get(event_id)
            if existing is None or existing.owner_id != owner_id:
                return False
            del self._events[event_id]
            return True
