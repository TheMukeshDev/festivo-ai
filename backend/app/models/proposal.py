"""Planning proposal domain model.

Proposals are advisory records. They never mutate budgets, tasks, vendors, or
expenses until an explicit, validated owner approval is applied.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class ProposalType(StrEnum):
    """Supported proposal sources."""

    AI_PLANNING = "ai_planning"


class ProposalStatus(StrEnum):
    """Lifecycle of a planning proposal."""

    PENDING = "pending"
    PARTIALLY_APPROVED = "partially_approved"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ProposalItemStatus(StrEnum):
    """Lifecycle of one proposed action inside a proposal."""

    PENDING = "pending"
    APPLIED = "applied"
    SKIPPED = "skipped"
    REJECTED = "rejected"


class ProposalActionType(StrEnum):
    """Explicit, non-executable actions a proposal may contain."""

    ADD_TASK = "add_task"
    UPDATE_TASK_DUE_DATE = "update_task_due_date"
    ADD_VENDOR_FOLLOW_UP_TASK = "add_vendor_follow_up_task"
    BUDGET_ALLOCATION_SUGGESTION = "budget_allocation_suggestion"
    ADVISORY = "advisory"


@dataclass(frozen=True, slots=True)
class Proposal:
    """An owner-scoped set of suggested planning changes."""

    proposal_id: UUID
    event_id: UUID
    owner_id: UUID
    proposal_type: ProposalType
    title: str
    summary: str
    payload: dict[str, Any]
    status: ProposalStatus
    version: int
    source_snapshot: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
