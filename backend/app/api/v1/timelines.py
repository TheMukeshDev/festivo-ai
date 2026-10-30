"""Authenticated timeline and task API endpoints."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.api.dependencies import get_current_user
from app.core.auth import AuthenticatedUser
from app.core.ids import parse_uuid
from app.models.task import TaskPriority, TaskStatus
from app.schemas.errors import ErrorResponse
from app.schemas.task import TaskCreate, TaskListResponse, TaskResponse, TaskUpdate
from app.schemas.timeline import TimelineResponse
from app.services.task_service import TaskService
from app.services.timeline_service import TimelineService

router = APIRouter(tags=["timelines", "tasks"])

_STANDARD_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}


def _timeline_service(request: Request) -> TimelineService:
    service: TimelineService = request.app.state.timeline_service
    return service


def _task_service(request: Request) -> TaskService:
    service: TaskService = request.app.state.task_service
    return service


@router.post(
    "/events/{event_id}/timeline",
    response_model=TimelineResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_STANDARD_ERRORS,
    summary="Generate an event timeline",
)
def generate_timeline(
    event_id: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> TimelineResponse:
    timeline, _ = _timeline_service(request).generate(user.user_id, event_id)
    return TimelineResponse.from_timeline(timeline)


@router.get(
    "/events/{event_id}/timeline",
    response_model=TimelineResponse,
    responses=_STANDARD_ERRORS,
    summary="Get an event timeline",
)
def get_timeline(
    event_id: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> TimelineResponse:
    return TimelineResponse.from_timeline(_timeline_service(request).get(user.user_id, event_id))


@router.post(
    "/events/{event_id}/timeline/regenerate",
    response_model=TimelineResponse,
    status_code=status.HTTP_200_OK,
    responses=_STANDARD_ERRORS,
    summary="Regenerate missing timeline tasks",
)
def regenerate_timeline(
    event_id: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> TimelineResponse:
    timeline, _ = _timeline_service(request).regenerate(user.user_id, event_id)
    return TimelineResponse.from_timeline(timeline)


@router.post(
    "/events/{event_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_STANDARD_ERRORS,
    summary="Create a planning task",
)
def create_task(
    event_id: str,
    payload: TaskCreate,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> TaskResponse:
    return TaskResponse.from_task(_task_service(request).create(user.user_id, event_id, payload))


@router.get(
    "/events/{event_id}/tasks",
    response_model=TaskListResponse,
    responses=_STANDARD_ERRORS,
    summary="List planning tasks",
)
def list_tasks(
    event_id: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    *,
    status: Annotated[TaskStatus | None, Query()] = None,
    priority: Annotated[TaskPriority | None, Query()] = None,
    timeline_id: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
) -> TaskListResponse:
    parsed_timeline_id = (
        parse_uuid(timeline_id, "Task not found.") if timeline_id is not None else None
    )
    tasks, total = _task_service(request).list_tasks(
        user.user_id,
        event_id,
        status=status,
        priority=priority,
        timeline_id=parsed_timeline_id,
        limit=limit,
        offset=offset,
    )
    return TaskListResponse(
        items=[TaskResponse.from_task(task) for task in tasks],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/events/{event_id}/tasks/{task_id}",
    response_model=TaskResponse,
    responses=_STANDARD_ERRORS,
    summary="Get a planning task",
)
def get_task(
    event_id: str,
    task_id: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> TaskResponse:
    return TaskResponse.from_task(_task_service(request).get(user.user_id, event_id, task_id))


@router.patch(
    "/events/{event_id}/tasks/{task_id}",
    response_model=TaskResponse,
    responses=_STANDARD_ERRORS,
    summary="Update a planning task",
)
def update_task(
    event_id: str,
    task_id: str,
    payload: TaskUpdate,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> TaskResponse:
    return TaskResponse.from_task(
        _task_service(request).update(user.user_id, event_id, task_id, payload)
    )


@router.delete(
    "/events/{event_id}/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=_STANDARD_ERRORS,
    summary="Delete a planning task",
)
def delete_task(
    event_id: str,
    task_id: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> Response:
    _task_service(request).delete(user.user_id, event_id, task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
