"""Thin orchestration between AI generation, proposals, and existing services."""

from typing import Any
from uuid import UUID

from app.models.proposal import Proposal, ProposalStatus
from app.schemas.proposal import (
    ProposalApprovalRequest,
    ProposalApprovalResponse,
    ProposalGenerationRequest,
    ProposalRejectRequest,
    ProposalRejectResponse,
)
from app.services.ai.planning_service import AIPlanningService
from app.services.proposal_service import ProposalService


class PlanningOrchestrationService:
    """Coordinate proposal generation and approval without duplicating domain logic."""

    def __init__(
        self,
        proposal_service: ProposalService,
        ai_planning_service: AIPlanningService,
    ) -> None:
        self._proposal_service = proposal_service
        self._ai_planning_service = ai_planning_service

    def generate_ai_proposal(
        self,
        owner_id: UUID,
        event_id: str,
        request: ProposalGenerationRequest,
    ) -> Proposal:
        preferences: dict[str, Any] = dict(request.preferences)
        if request.focus_areas:
            preferences["focus_areas"] = request.focus_areas
        if request.additional_notes:
            preferences["additional_notes"] = request.additional_notes
        if request.conversation:
            preferences["conversation"] = [message.model_dump() for message in request.conversation]
        plan = self._ai_planning_service.generate_plan(
            owner_id,
            event_id,
            preferences or None,
        )
        return self._proposal_service.create_ai_proposal(owner_id, event_id, plan)

    def list_proposals(
        self,
        owner_id: UUID,
        event_id: str,
        *,
        status: ProposalStatus | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Proposal], int]:
        return self._proposal_service.list(
            owner_id,
            event_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    def get_proposal(self, owner_id: UUID, event_id: str, proposal_id: str) -> Proposal:
        return self._proposal_service.get(owner_id, event_id, proposal_id)

    def approve(
        self,
        owner_id: UUID,
        event_id: str,
        proposal_id: str,
        request: ProposalApprovalRequest,
    ) -> ProposalApprovalResponse:
        return self._proposal_service.approve(owner_id, event_id, proposal_id, request)

    def reject(
        self,
        owner_id: UUID,
        event_id: str,
        proposal_id: str,
        request: ProposalRejectRequest,
    ) -> ProposalRejectResponse:
        return self._proposal_service.reject(owner_id, event_id, proposal_id, request)

    def applied_recommendations(
        self,
        owner_id: UUID,
        event_id: str,
    ) -> list[dict[str, Any]]:
        return self._proposal_service.applied_recommendations(owner_id, event_id)
