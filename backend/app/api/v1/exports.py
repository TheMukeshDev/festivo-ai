"""Authenticated PDF and CSV event report exports."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app.api.dependencies import get_current_user
from app.core.auth import AuthenticatedUser
from app.schemas.errors import ErrorResponse
from app.services.report_service import ReportService

router = APIRouter(prefix="/events/{event_id}/export", tags=["exports"])

_EXPORT_ERRORS = {
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}


def _service(request: Request) -> ReportService:
    return request.app.state.report_service


def _download_headers(filename: str) -> dict[str, str]:
    return {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": "no-store, private",
        "Pragma": "no-cache",
        "X-Content-Type-Options": "nosniff",
    }


@router.get(
    "/pdf",
    response_class=Response,
    responses={
        **_EXPORT_ERRORS,
        200: {
            "content": {"application/pdf": {}},
            "description": "Downloadable PDF event report.",
        },
    },
    summary="Export an event plan as PDF",
)
def export_pdf(
    event_id: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> Response:
    content, filename = _service(request).build_pdf(user.user_id, event_id)
    return Response(
        content=content,
        media_type="application/pdf",
        headers=_download_headers(filename),
    )


@router.get(
    "/csv",
    response_class=Response,
    responses={
        **_EXPORT_ERRORS,
        200: {
            "content": {"text/csv": {}},
            "description": "UTF-8 CSV event plan with documented section columns.",
        },
    },
    summary="Export an event plan as CSV",
)
def export_csv(
    event_id: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> Response:
    content, filename = _service(request).build_csv(user.user_id, event_id)
    return Response(
        content=content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers=_download_headers(filename),
    )
