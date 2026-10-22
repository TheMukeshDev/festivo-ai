"""Event budget and expense API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Query, Request, status

from app.schemas.budget import (
    BudgetCreate,
    BudgetIssueResponse,
    BudgetResponse,
    BudgetUpdate,
    CategoryTotalResponse,
    ExpenseCreate,
    ExpenseResponse,
    ExpenseUpdate,
    ReserveResponse,
)
from app.schemas.errors import ErrorResponse
from app.services.budget_service import BudgetService, BudgetView

router = APIRouter(prefix="/events/{event_id}/budget", tags=["budgets"])

_STANDARD_ERRORS = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}


def _service(request: Request) -> BudgetService:
    service: BudgetService = request.app.state.budget_service
    return service


def _response(view: BudgetView) -> BudgetResponse:
    budget = view.budget
    calculation = view.calculation
    return BudgetResponse(
        budget_id=str(budget.budget_id),
        event_id=str(budget.event_id),
        total_limit=budget.total_limit,
        currency=budget.currency,
        reserve=ReserveResponse(
            type=budget.reserve_type,
            value=budget.reserve_value,
            amount=calculation.reserve_amount,
        ),
        planned_spending=calculation.planned_spending,
        available_for_planning=calculation.available_for_planning,
        remaining_total=calculation.remaining_total,
        remaining_after_reserve=calculation.remaining_after_reserve,
        budget_overrun=calculation.budget_overrun,
        reserve_consumed=calculation.reserve_consumed,
        cost_per_guest=calculation.cost_per_guest,
        status=calculation.status,
        version=budget.version,
        issues=[
            BudgetIssueResponse(
                code=issue.code,
                severity=issue.severity,
                message=issue.message,
            )
            for issue in calculation.issues
        ],
        category_totals=[
            CategoryTotalResponse(category=total.category, amount=total.amount)
            for total in calculation.category_totals
        ],
        expenses=[
            ExpenseResponse(
                expense_id=str(expense.expense_id),
                category=expense.category,
                name=expense.name,
                amount=expense.amount,
                amount_status=expense.amount_status,
                notes=expense.notes,
                created_at=expense.created_at,
                updated_at=expense.updated_at,
            )
            for expense in view.expenses
        ],
        created_at=budget.created_at,
        updated_at=budget.updated_at,
    )


@router.post(
    "",
    response_model=BudgetResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_STANDARD_ERRORS,
    summary="Create an event budget",
)
def create_budget(
    event_id: str,
    payload: BudgetCreate,
    request: Request,
) -> BudgetResponse:
    """Create the single budget for an event using its currency and default limit."""
    return _response(_service(request).create(event_id, payload))


@router.get(
    "",
    response_model=BudgetResponse,
    responses=_STANDARD_ERRORS,
    summary="Get a budget summary",
)
def get_budget(event_id: str, request: Request) -> BudgetResponse:
    """Return server-calculated totals, reserve usage, and planned expenses."""
    return _response(_service(request).get(event_id))


@router.patch(
    "",
    response_model=BudgetResponse,
    responses=_STANDARD_ERRORS,
    summary="Update budget settings",
)
def update_budget(
    event_id: str,
    payload: BudgetUpdate,
    request: Request,
) -> BudgetResponse:
    """Change the total limit or reserve and increment the budget version."""
    return _response(_service(request).update(event_id, payload))


@router.post(
    "/expenses",
    response_model=BudgetResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_STANDARD_ERRORS,
    summary="Add a planned expense",
)
def create_expense(
    event_id: str,
    payload: ExpenseCreate,
    request: Request,
) -> BudgetResponse:
    """Add an expense and return the recalculated budget summary."""
    return _response(_service(request).add_expense(event_id, payload))


@router.patch(
    "/expenses/{expense_id}",
    response_model=BudgetResponse,
    responses=_STANDARD_ERRORS,
    summary="Update a planned expense",
)
def update_expense(
    event_id: str,
    expense_id: str,
    payload: ExpenseUpdate,
    request: Request,
) -> BudgetResponse:
    """Update an expense and increment the budget version atomically."""
    return _response(_service(request).update_expense(event_id, expense_id, payload))


@router.delete(
    "/expenses/{expense_id}",
    response_model=BudgetResponse,
    responses=_STANDARD_ERRORS,
    summary="Delete a planned expense",
)
def delete_expense(
    event_id: str,
    expense_id: str,
    request: Request,
    expected_version: Annotated[
        int,
        Query(
            ge=1,
            description="Current budget version used for optimistic concurrency.",
        ),
    ],
) -> BudgetResponse:
    """Delete an expense and return the recalculated budget summary."""
    return _response(_service(request).delete_expense(event_id, expense_id, expected_version))
