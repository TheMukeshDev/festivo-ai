"""Event creation and management API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Query, Request, Response, status

from app.schemas.errors import ErrorResponse
from app.schemas.event import EventCreate, EventListResponse, EventResponse, EventUpdate
from app.services.event_service import EventService

router = APIRouter(prefix="/events", tags=["events"])

_VALIDATION_RESPONSES = {422: {"model": ErrorResponse}}
_NOT_FOUND_RESPONSES = {
    404: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
}


def _service(request: Request) -> EventService:
    service: EventService = request.app.state.event_service
    return service


@router.post(
    "",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_VALIDATION_RESPONSES,
    summary="Create an event",
)
def create_event(payload: EventCreate, request: Request) -> EventResponse:
    """Create a server-identified event in the configured storage backend."""
    return EventResponse.from_event(_service(request).create(payload))


@router.get(
    "",
    response_model=EventListResponse,
    responses=_VALIDATION_RESPONSES,
    summary="List events",
)
def list_events(
    request: Request,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Maximum number of events to return."),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0, le=1_000_000, description="Number of events to skip."),
    ] = 0,
) -> EventListResponse:
    """Return a deterministic page of events in creation order."""
    events, total = _service(request).list_events(limit=limit, offset=offset)
    return EventListResponse(
        items=[EventResponse.from_event(event) for event in events],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{event_id}",
    response_model=EventResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get an event",
)
def get_event(event_id: str, request: Request) -> EventResponse:
    """Return one event or a consistent not-found error."""
    return EventResponse.from_event(_service(request).get(event_id))


@router.patch(
    "/{event_id}",
    response_model=EventResponse,
    responses=_NOT_FOUND_RESPONSES,
    summary="Update an event",
)
def update_event(event_id: str, payload: EventUpdate, request: Request) -> EventResponse:
    """Apply supplied editable fields while preserving server-managed fields."""
    return EventResponse.from_event(_service(request).update(event_id, payload))


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={404: {"model": ErrorResponse}},
    summary="Delete an event",
)
def delete_event(event_id: str, request: Request) -> Response:
    """Delete one event if it exists."""
    _service(request).delete(event_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
