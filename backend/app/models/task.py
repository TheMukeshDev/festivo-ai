"""Event planning task domain model."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class TaskStatus(StrEnum):
    """Lifecycle state of a planning task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(StrEnum):
    """Urgency of a planning task."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass(frozen=True, slots=True)
class Task:
    """A user-editable planning activity for an event."""

    task_id: UUID
    event_id: UUID
    owner_id: UUID
    timeline_id: UUID | None
    template_key: str | None
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_at: datetime | None
    assigned_to: str | None
    estimated_cost: Decimal | None
    actual_cost: Decimal | None
    currency: str
    sort_order: int
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
