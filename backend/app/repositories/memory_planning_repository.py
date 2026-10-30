"""Thread-safe in-memory timeline and task repository."""

import copy
from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime
from threading import RLock
from uuid import UUID

from app.core.exceptions import ResourceConflictError, ResourceNotFoundError
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.timeline import Timeline
from app.repositories.planning_repository import PlanningRepository

_TIMELINE_CONFLICT = "An event timeline already exists."
_TASK_CONFLICT = "A task with this template key already exists."
_TASK_NOT_FOUND = "Task not found."


class InMemoryPlanningRepository(PlanningRepository):
    """Process-local repository with the same ownership invariants as PostgreSQL."""

    def __init__(self) -> None:
        self._timelines: dict[UUID, Timeline] = {}
        self._timeline_by_event: dict[UUID, UUID] = {}
        self._tasks: dict[UUID, Task] = {}
        self._lock = RLock()

    def create_timeline(self, timeline: Timeline, tasks: Sequence[Task]) -> Timeline:
        with self._lock:
            if timeline.event_id in self._timeline_by_event:
                raise ResourceConflictError(_TIMELINE_CONFLICT)
            self._timelines[timeline.timeline_id] = copy.deepcopy(timeline)
            self._timeline_by_event[timeline.event_id] = timeline.timeline_id
            for task in tasks:
                self._tasks[task.task_id] = copy.deepcopy(task)
            return copy.deepcopy(timeline)

    def get_timeline(self, event_id: UUID, owner_id: UUID) -> Timeline | None:
        with self._lock:
            timeline_id = self._timeline_by_event.get(event_id)
            timeline = self._timelines.get(timeline_id) if timeline_id else None
            if timeline is None or timeline.owner_id != owner_id:
                return None
            return copy.deepcopy(timeline)

    def update_timeline(self, owner_id: UUID, timeline: Timeline) -> Timeline | None:
        with self._lock:
            existing = self._timelines.get(timeline.timeline_id)
            if (
                existing is None
                or existing.owner_id != owner_id
                or existing.event_id != timeline.event_id
            ):
                return None
            self._timelines[timeline.timeline_id] = copy.deepcopy(timeline)
            return copy.deepcopy(timeline)

    def add_generated_tasks(
        self,
        owner_id: UUID,
        timeline: Timeline,
        tasks: Sequence[Task],
        *,
        generated_at: datetime,
    ) -> tuple[Timeline, list[Task]]:
        with self._lock:
            existing = self._timelines.get(timeline.timeline_id)
            if existing is None or existing.owner_id != owner_id:
                raise ResourceNotFoundError("Timeline not found.")

            existing_keys = {
                task.template_key
                for task in self._tasks.values()
                if task.event_id == timeline.event_id and task.template_key is not None
            }
            added: list[Task] = []
            for task in tasks:
                if task.template_key is not None and task.template_key in existing_keys:
                    continue
                self._tasks[task.task_id] = copy.deepcopy(task)
                if task.template_key is not None:
                    existing_keys.add(task.template_key)
                added.append(copy.deepcopy(task))

            updated = replace(
                existing,
                generated_at=generated_at,
                updated_at=timeline.updated_at,
            )
            self._timelines[timeline.timeline_id] = updated
            return copy.deepcopy(updated), added

    def create_task(self, task: Task) -> Task:
        with self._lock:
            self._assert_timeline_link(task)
            if task.template_key is not None:
                existing = next(
                    (
                        candidate
                        for candidate in self._tasks.values()
                        if candidate.event_id == task.event_id
                        and candidate.template_key == task.template_key
                    ),
                    None,
                )
                if existing is not None:
                    raise ResourceConflictError(_TASK_CONFLICT)
            self._tasks[task.task_id] = copy.deepcopy(task)
            return copy.deepcopy(task)

    def get_task_by_template_key(
        self,
        owner_id: UUID,
        event_id: UUID,
        template_key: str,
    ) -> Task | None:
        with self._lock:
            for task in self._tasks.values():
                if (
                    task.owner_id == owner_id
                    and task.event_id == event_id
                    and task.template_key == template_key
                ):
                    return copy.deepcopy(task)
            return None

    def get_task(
        self,
        task_id: UUID,
        event_id: UUID,
        owner_id: UUID,
    ) -> Task | None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None or task.owner_id != owner_id or task.event_id != event_id:
                return None
            return copy.deepcopy(task)

    def update_task(self, owner_id: UUID, task: Task) -> Task | None:
        with self._lock:
            existing = self._tasks.get(task.task_id)
            if existing is None or existing.owner_id != owner_id:
                return None
            self._assert_timeline_link(task)
            self._tasks[task.task_id] = copy.deepcopy(task)
            return copy.deepcopy(task)

    def delete_task(
        self,
        task_id: UUID,
        event_id: UUID,
        owner_id: UUID,
    ) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None or task.owner_id != owner_id or task.event_id != event_id:
                return False
            del self._tasks[task_id]
            return True

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
        with self._lock:
            matches = [
                task
                for task in self._tasks.values()
                if task.owner_id == owner_id
                and task.event_id == event_id
                and (status is None or task.status == status)
                and (priority is None or task.priority == priority)
                and (timeline_id is None or task.timeline_id == timeline_id)
            ]
            matches.sort(key=lambda task: (task.sort_order, task.created_at, task.task_id))
            return [copy.deepcopy(task) for task in matches[offset : offset + limit]], len(matches)

    def list_timeline_tasks(
        self,
        owner_id: UUID,
        event_id: UUID,
        timeline_id: UUID,
    ) -> list[Task]:
        with self._lock:
            matches = [
                task
                for task in self._tasks.values()
                if task.owner_id == owner_id
                and task.event_id == event_id
                and task.timeline_id == timeline_id
            ]
            matches.sort(key=lambda task: (task.sort_order, task.created_at, task.task_id))
            return [copy.deepcopy(task) for task in matches]

    def _assert_timeline_link(self, task: Task) -> None:
        if task.timeline_id is None:
            return
        timeline = self._timelines.get(task.timeline_id)
        if (
            timeline is None
            or timeline.owner_id != task.owner_id
            or timeline.event_id != task.event_id
        ):
            raise ResourceNotFoundError(_TASK_NOT_FOUND)
