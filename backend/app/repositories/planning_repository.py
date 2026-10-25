"""Persistence boundary for event timelines and planning tasks."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from app.models.task import Task, TaskPriority, TaskStatus
from app.models.timeline import Timeline


class PlanningRepository(ABC):
    """Store timelines and tasks with owner-scoped access in every query."""

    @abstractmethod
    def create_timeline(self, timeline: Timeline, tasks: Sequence[Task]) -> Timeline:
        """Atomically create a timeline and its initial generated tasks."""

    @abstractmethod
    def get_timeline(self, event_id: UUID, owner_id: UUID) -> Timeline | None:
        """Return an owned event's timeline when it exists."""

    @abstractmethod
    def update_timeline(self, owner_id: UUID, timeline: Timeline) -> Timeline | None:
        """Replace an existing owned timeline."""

    @abstractmethod
    def add_generated_tasks(
        self,
        owner_id: UUID,
        timeline: Timeline,
        tasks: Sequence[Task],
        *,
        generated_at: datetime,
    ) -> tuple[Timeline, list[Task]]:
        """Atomically add missing generated tasks and record regeneration time."""

    @abstractmethod
    def get_task_by_template_key(
        self,
        owner_id: UUID,
        event_id: UUID,
        template_key: str,
    ) -> Task | None:
        """Return an event task with the given generated template key, if any."""

    @abstractmethod
    def create_task(self, task: Task) -> Task:
        """Persist a new owned task."""

    @abstractmethod
    def get_task(
        self,
        task_id: UUID,
        event_id: UUID,
        owner_id: UUID,
    ) -> Task | None:
        """Return one owned task belonging to the given event."""

    @abstractmethod
    def update_task(self, owner_id: UUID, task: Task) -> Task | None:
        """Replace an existing owned task."""

    @abstractmethod
    def delete_task(
        self,
        task_id: UUID,
        event_id: UUID,
        owner_id: UUID,
    ) -> bool:
        """Delete an owned task belonging to the given event."""

    @abstractmethod
    def list_tasks(
        self,
        owner_id: UUID,
        event_id: UUID,
        *,
        status: TaskStatus | None,
        priority: TaskPriority | None,
        timeline_id: UUID | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Task], int]:
        """Return a filtered, stable page of an owned event's tasks."""

    @abstractmethod
    def list_timeline_tasks(
        self,
        owner_id: UUID,
        event_id: UUID,
        timeline_id: UUID,
    ) -> list[Task]:
        """Return all tasks linked to an owned timeline."""
