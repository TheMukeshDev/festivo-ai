"""Authenticated vendor API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.dependencies import get_current_user
from app.core.auth import AuthenticatedUser
from app.models.vendor import VendorCategory, VendorStatus
from app.schemas.errors import ErrorResponse
from app.schemas.vendor import (
    VendorCompareRequest,
    VendorCompareResponse,
    VendorCreate,
    VendorListResponse,
    VendorResponse,
    VendorUpdate,
)
from app.services.vendor_service import VendorService

router = APIRouter(prefix="/events/{event_id}/vendors", tags=["vendors"])

_STANDARD_ERRORS = {
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}


def _service(request: Request) -> VendorService:
    return request.app.state.vendor_service


@router.post(
    "",
    response_model=VendorResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_STANDARD_ERRORS,
    summary="Add a vendor to an event",
)
def create_vendor(
    event_id: str,
    payload: VendorCreate,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
):
    return VendorResponse.from_vendor(_service(request).create(user.user_id, event_id, payload))


@router.get(
    "",
    response_model=VendorListResponse,
    responses=_STANDARD_ERRORS,
    summary="List vendors",
)
def list_vendors(
    event_id: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    category: Annotated[VendorCategory | None, Query()] = None,
    status: Annotated[VendorStatus | None, Query()] = None,
    min_price: Annotated[float | None, Query(ge=0)] = None,
    max_price: Annotated[float | None, Query(ge=0)] = None,
    name: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
):
    vendors, total = _service(request).list(
        user.user_id,
        event_id,
        category=category,
        status=status,
        min_price=min_price,
        max_price=max_price,
        name=name,
        limit=limit,
        offset=offset,
    )
    return VendorListResponse(
        items=[VendorResponse.from_vendor(v) for v in vendors],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{vendor_id}",
    response_model=VendorResponse,
    responses=_STANDARD_ERRORS,
    summary="Get a vendor",
)
def get_vendor(
    event_id: str,
    vendor_id: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
):
    return VendorResponse.from_vendor(_service(request).get(user.user_id, event_id, vendor_id))


@router.patch(
    "/{vendor_id}",
    response_model=VendorResponse,
    responses=_STANDARD_ERRORS,
    summary="Update a vendor",
)
def update_vendor(
    event_id: str,
    vendor_id: str,
    payload: VendorUpdate,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
):
    return VendorResponse.from_vendor(
        _service(request).update(user.user_id, event_id, vendor_id, payload)
    )


@router.delete(
    "/{vendor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_STANDARD_ERRORS,
    summary="Delete a vendor",
)
def delete_vendor(
    event_id: str,
    vendor_id: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
):
    from fastapi import Response

    _service(request).delete(user.user_id, event_id, vendor_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/compare",
    response_model=VendorCompareResponse,
    responses=_STANDARD_ERRORS,
    summary="Compare vendors",
)
def compare_vendors(
    event_id: str,
    payload: VendorCompareRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
):
    result = _service(request).compare(user.user_id, event_id, payload)
    return VendorCompareResponse(**result)
