"""AI proposal generation endpoints and safe provider error mapping."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import get_current_user
from app.core.auth import AuthenticatedUser
from app.core.config import Settings
from app.schemas.errors import ErrorResponse
from app.schemas.proposal import ProposalGenerationRequest, ProposalResponse
from app.services.ai.base import (
    AIAuthenticationError,
    AIConfigurationError,
    AINetworkError,
    AIOutputValidationError,
    AIProviderError,
    AIRateLimitError,
    AIServiceError,
    AITimeoutError,
)
from app.services.planning_orchestration_service import PlanningOrchestrationService

router = APIRouter(prefix="/events/{event_id}/ai-plan", tags=["ai-planning"])

_STANDARD_ERRORS = {
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
    504: {"model": ErrorResponse},
}


def _service(request: Request) -> PlanningOrchestrationService:
    return request.app.state.planning_orchestration_service


def handle_ai_error(exc: Exception) -> None:
    """Translate provider failures without exposing exception details."""
    if isinstance(exc, AIConfigurationError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI planning is not configured.",
        ) from None
    if isinstance(exc, AIAuthenticationError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI provider authentication failed.",
        ) from None
    if isinstance(exc, AIRateLimitError):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI provider rate limit exceeded.",
        ) from None
    if isinstance(exc, AITimeoutError):
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI request timed out.",
        ) from None
    if isinstance(exc, (AINetworkError, AIServiceError)):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service temporarily unavailable.",
        ) from None
    if isinstance(exc, AIOutputValidationError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="AI response could not be validated.",
        ) from None
    if isinstance(exc, AIProviderError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI planning failed.",
        ) from None
    raise exc


def generate_proposal(
    request: Request,
    user: AuthenticatedUser,
    event_id: str,
    payload: ProposalGenerationRequest | None,
) -> ProposalResponse:
    try:
        proposal = _service(request).generate_ai_proposal(
            user.user_id,
            event_id,
            payload or ProposalGenerationRequest(),
        )
    except Exception as exc:
        handle_ai_error(exc)
        raise
    return ProposalResponse.from_proposal(proposal)


@router.post(
    "",
    response_model=ProposalResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_STANDARD_ERRORS,
    summary="Generate a personalized planning proposal",
)
def generate_ai_plan(
    event_id: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    payload: ProposalGenerationRequest | None = None,
) -> ProposalResponse:
    return generate_proposal(request, user, event_id, payload)


@router.post(
    "/refine",
    response_model=ProposalResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_STANDARD_ERRORS,
    summary="Refine a planning proposal",
)
def refine_ai_plan(
    event_id: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    payload: ProposalGenerationRequest | None = None,
) -> ProposalResponse:
    return generate_proposal(request, user, event_id, payload)


@router.get(
    "/status",
    status_code=status.HTTP_200_OK,
    responses={401: {"model": ErrorResponse}},
    summary="Get safe AI provider/configuration status",
)
def ai_plan_status(
    event_id: str,
    request: Request,
    _user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict[str, Any]:
    settings: Settings = request.app.state.settings
    return {
        "event_id": event_id,
        "provider": settings.llm_provider,
        "enabled": bool(settings.llm_enabled),
        "configuration_state": settings.llm_configuration_state,
        "model_configured": settings.llm_model is not None
        and not (settings.llm_model or "").startswith("replace_with"),
        "credential_configured": settings.credential_configured,
        "timeout_seconds": settings.llm_timeout_seconds,
        "max_retries": settings.llm_max_retries,
    }
