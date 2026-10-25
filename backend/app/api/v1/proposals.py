"""Authenticated planning proposal, approval, and rejection endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.dependencies import get_current_user
from app.api.v1.ai_planning import generate_proposal
from app.core.auth import AuthenticatedUser
from app.models.proposal import ProposalStatus
from app.schemas.errors import ErrorResponse
from app.schemas.proposal import (
    ProposalApprovalRequest,
    ProposalApprovalResponse,
    ProposalGenerationRequest,
    ProposalListResponse,
    ProposalRejectRequest,
    ProposalRejectResponse,
    ProposalResponse,
)
from app.services.planning_orchestration_service import PlanningOrchestrationService

router = APIRouter(prefix="/events/{event_id}/proposals", tags=["proposals"])

_STANDARD_ERRORS = {
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}


def _service(request: Request) -> PlanningOrchestrationService:
    return request.app.state.planning_orchestration_service


@router.post(
    "/generate",
    response_model=ProposalResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_STANDARD_ERRORS,
    summary="Generate an unapproved AI planning proposal",
)
def generate_ai_proposal(
    event_id: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    payload: ProposalGenerationRequest | None = None,
) -> ProposalResponse:
    return generate_proposal(request, user, event_id, payload)


@router.get(
    "",
    response_model=ProposalListResponse,
    responses=_STANDARD_ERRORS,
    summary="List event planning proposals",
)
def list_proposals(
    event_id: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    status_filter: Annotated[ProposalStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
) -> ProposalListResponse:
    proposals, total = _service(request).list_proposals(
        user.user_id,
        event_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return ProposalListResponse(
        items=[ProposalResponse.from_proposal(proposal) for proposal in proposals],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{proposal_id}",
    response_model=ProposalResponse,
    responses=_STANDARD_ERRORS,
    summary="Get one planning proposal",
)
def get_proposal(
    event_id: str,
    proposal_id: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> ProposalResponse:
    return ProposalResponse.from_proposal(
        _service(request).get_proposal(user.user_id, event_id, proposal_id)
    )


@router.post(
    "/{proposal_id}/approve",
    response_model=ProposalApprovalResponse,
    responses=_STANDARD_ERRORS,
    summary="Approve all or selected proposal items",
)
def approve_proposal(
    event_id: str,
    proposal_id: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    payload: ProposalApprovalRequest | None = None,
) -> ProposalApprovalResponse:
    return _service(request).approve(
        user.user_id,
        event_id,
        proposal_id,
        payload or ProposalApprovalRequest(),
    )


@router.post(
    "/{proposal_id}/reject",
    response_model=ProposalRejectResponse,
    responses=_STANDARD_ERRORS,
    summary="Reject a proposal or selected items",
)
def reject_proposal(
    event_id: str,
    proposal_id: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    payload: ProposalRejectRequest | None = None,
) -> ProposalRejectResponse:
    return _service(request).reject(
        user.user_id,
        event_id,
        proposal_id,
        payload or ProposalRejectRequest(),
    )
