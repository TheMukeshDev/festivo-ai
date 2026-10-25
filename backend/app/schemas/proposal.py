"""Validated planning proposal and approval API contracts."""

from datetime import datetime
from typing import Annotated, Any, Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.core.clock import coerce_utc
from app.models.proposal import (
    Proposal,
    ProposalActionType,
    ProposalItemStatus,
    ProposalStatus,
    ProposalType,
)

ProposalTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]
ProposalSummary = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=6000),
]
ShortText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]
LongText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=2000),
]


def _normalize_optional_datetime(value: object) -> object:
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise ValueError("Timestamp must be a timezone-aware ISO-8601 value.")
    return coerce_utc(value)


class ProposalItemResponse(BaseModel):
    """One validated, non-executable proposal item."""

    model_config = ConfigDict(extra="forbid")

    item_id: str
    action_type: ProposalActionType
    status: ProposalItemStatus
    label: str
    data: dict[str, Any]
    applied_at: datetime | None = None
    result_message: str | None = None
    resource_id: str | None = None


class ProposalResponse(BaseModel):
    """Owner-scoped proposal with explicit item states."""

    model_config = ConfigDict(extra="forbid")

    proposal_id: str
    event_id: str
    proposal_type: ProposalType
    title: str
    summary: str
    status: ProposalStatus
    version: int
    items: list[ProposalItemResponse]
    pending_item_count: int = Field(ge=0)
    applied_item_count: int = Field(ge=0)
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    approved_at: datetime | None = None
    rejected_at: datetime | None = None

    @classmethod
    def from_proposal(cls, proposal: Proposal) -> Self:
        items = [
            ProposalItemResponse.model_validate(item)
            for item in proposal.payload.get("items", [])
        ]
        pending = sum(1 for item in items if item.status == ProposalItemStatus.PENDING)
        applied = sum(1 for item in items if item.status == ProposalItemStatus.APPLIED)
        return cls(
            proposal_id=str(proposal.proposal_id),
            event_id=str(proposal.event_id),
            proposal_type=proposal.proposal_type,
            title=proposal.title,
            summary=proposal.summary,
            status=proposal.status,
            version=proposal.version,
            items=items,
            pending_item_count=pending,
            applied_item_count=applied,
            created_at=proposal.created_at,
            updated_at=proposal.updated_at,
            expires_at=proposal.expires_at,
            approved_at=proposal.approved_at,
            rejected_at=proposal.rejected_at,
        )


class ProposalListResponse(BaseModel):
    """Deterministic page of proposals for one event."""

    model_config = ConfigDict(extra="forbid")

    items: list[ProposalResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)


class ProposalApprovalRequest(BaseModel):
    """Approve all pending items or an explicit subset."""

    model_config = ConfigDict(extra="forbid")

    item_ids: list[UUID] | None = Field(
        default=None,
        max_length=100,
        description="Pending item identifiers. Omit to approve every eligible item.",
    )
    allow_advisory: bool = Field(
        default=True,
        description="Advisory budget suggestions are recorded as applied without changing money.",
    )

    @field_validator("item_ids")
    @classmethod
    def deduplicate_items(cls, value: list[UUID] | None) -> list[UUID] | None:
        if value is None:
            return None
        return list(dict.fromkeys(value))


class ProposalRejectRequest(BaseModel):
    """Reject a whole proposal or selected pending items."""

    model_config = ConfigDict(extra="forbid")

    item_ids: list[UUID] | None = Field(default=None, max_length=100)
    reason: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = (
        None
    )

    @field_validator("item_ids")
    @classmethod
    def deduplicate_rejection_items(cls, value: list[UUID] | None) -> list[UUID] | None:
        if value is None:
            return None
        return list(dict.fromkeys(value))


class AppliedItemResult(BaseModel):
    """Outcome for one requested proposal item."""

    model_config = ConfigDict(extra="forbid")

    item_id: str
    action_type: ProposalActionType
    status: Literal["applied", "skipped", "rejected"]
    message: str
    resource_id: str | None = None


class ProposalApprovalResponse(BaseModel):
    """Explicit summary of an approval application."""

    model_config = ConfigDict(extra="forbid")

    proposal: ProposalResponse
    applied: list[AppliedItemResult]
    skipped: list[AppliedItemResult]
    rejected: list[AppliedItemResult]


class ProposalRejectResponse(BaseModel):
    """Proposal state after a rejection request."""

    model_config = ConfigDict(extra="forbid")

    proposal: ProposalResponse
    rejected_items: list[str]
    message: str


class ProposalGenerationRequest(BaseModel):
    """Optional preferences supplied when requesting a Gemini proposal."""

    model_config = ConfigDict(extra="forbid")

    preferences: dict[str, Any] = Field(default_factory=dict)
    focus_areas: list[str] = Field(default_factory=list, max_length=20)
    additional_notes: str | None = Field(default=None, max_length=2000)

    @field_validator("focus_areas")
    @classmethod
    def clean_focus_areas(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()][:20]

    @model_validator(mode="after")
    def combine_notes(self) -> Self:
        if self.additional_notes:
            self.additional_notes = self.additional_notes.strip() or None
        return self
