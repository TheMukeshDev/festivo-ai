"""Validated planning task request and response schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
)

from app.core.clock import coerce_utc
from app.core.money import quantize_money
from app.models.budget import MAX_MONEY
from app.models.task import Task, TaskPriority, TaskStatus

TaskTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
    Field(description="User-facing task title."),
]
TaskDescription = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=2_000),
    Field(description="Optional task details."),
]
AssignedTo = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=120),
    Field(description="Optional person responsible for the task."),
]
TaskMoney = Annotated[
    Decimal,
    Field(
        ge=Decimal("0"),
        le=MAX_MONEY,
        max_digits=12,
        decimal_places=2,
        allow_inf_nan=False,
        description="Optional non-negative monetary amount.",
    ),
    AfterValidator(quantize_money),
]


def _normalize_datetime(value: object) -> object:
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise ValueError("Due date must be an ISO-8601 timestamp with a timezone.")
    return coerce_utc(value)


DueAt = Annotated[
    datetime,
    BeforeValidator(_normalize_datetime),
    Field(description="Optional timezone-aware due timestamp, normalized to UTC."),
]


class TaskCreate(BaseModel):
    """Client-supplied fields for creating a planning task."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "title": "Confirm catering headcount",
                "description": "Call the caterer with the final guest count.",
                "priority": "high",
                "due_at": "2030-06-10T09:00:00+05:30",
                "assigned_to": "Ananya",
            }
        },
    )

    title: TaskTitle
    description: TaskDescription | None = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    due_at: DueAt | None = None
    assigned_to: AssignedTo | None = None
    estimated_cost: TaskMoney | None = None
    actual_cost: TaskMoney | None = None


class TaskUpdate(BaseModel):
    """Client-editable task fields; omitted fields remain unchanged."""

    model_config = ConfigDict(extra="forbid")

    title: TaskTitle | None = None
    description: TaskDescription | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_at: DueAt | None = None
    assigned_to: AssignedTo | None = None
    estimated_cost: TaskMoney | None = None
    actual_cost: TaskMoney | None = None


class TaskResponse(BaseModel):
    """Complete server representation of a planning task."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    event_id: str
    timeline_id: str | None
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

    @classmethod
    def from_task(cls, task: Task) -> Self:
        """Build a response from an immutable task model."""
        return cls(
            task_id=str(task.task_id),
            event_id=str(task.event_id),
            timeline_id=str(task.timeline_id) if task.timeline_id is not None else None,
            template_key=task.template_key,
            title=task.title,
            description=task.description,
            status=task.status,
            priority=task.priority,
            due_at=task.due_at,
            assigned_to=task.assigned_to,
            estimated_cost=task.estimated_cost,
            actual_cost=task.actual_cost,
            currency=task.currency,
            sort_order=task.sort_order,
            completed_at=task.completed_at,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )


class TaskListResponse(BaseModel):
    """Bounded, deterministic task collection response."""

    model_config = ConfigDict(extra="forbid")

    items: list[TaskResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
