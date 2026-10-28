"""Budget use cases, version checks, and server-authoritative summaries."""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from app.core.clock import Clock, coerce_utc, utc_now
from app.core.exceptions import (
    DomainValidationError,
    ResourceConflictError,
    ResourceNotFoundError,
    ValidationIssue,
)
from app.core.ids import parse_uuid
from app.models.budget import Budget, Expense, ReserveType
from app.models.event import Event
from app.repositories.budget_repository import BudgetAggregate, BudgetRepository
from app.repositories.event_repository import EventRepository
from app.schemas.budget import (
    BudgetCreate,
    BudgetUpdate,
    ExpenseCreate,
    ExpenseUpdate,
    FixedReserve,
    PercentageReserve,
)
from app.services.budget_calculator import BudgetCalculation, calculate_budget_summary

_EVENT_NOT_FOUND = "Event not found."
_BUDGET_NOT_FOUND = "Budget or expense not found."
_CONFLICT_MESSAGE = "The budget was modified by another request."


@dataclass(frozen=True, slots=True)
class BudgetView:
    """Budget data with all values derived on the server."""

    budget: Budget
    expenses: tuple[Expense, ...]
    calculation: BudgetCalculation
    guest_count: int


class BudgetService:
    """Coordinate budget lifecycle policies and optimistic concurrency."""

    def __init__(
        self,
        event_repository: EventRepository,
        budget_repository: BudgetRepository,
        clock: Clock | None = None,
    ) -> None:
        self._event_repository = event_repository
        self._budget_repository = budget_repository
        self._clock = clock or utc_now

    def create(self, owner_id: UUID, raw_event_id: str, payload: BudgetCreate) -> BudgetView:
        event = self._require_event(owner_id, raw_event_id)
        if self._budget_repository.get_by_event(event.event_id) is not None:
            raise ResourceConflictError("An event budget already exists.")

        total_limit = payload.total_limit or event.budget_amount
        reserve_type, reserve_value = self._reserve_values(payload.reserve)
        self._validate_reserve(total_limit, reserve_type, reserve_value)

        now = self._now()
        budget = Budget(
            budget_id=uuid4(),
            event_id=event.event_id,
            total_limit=total_limit,
            currency=event.currency,
            reserve_type=reserve_type,
            reserve_value=reserve_value,
            version=1,
            created_at=now,
            updated_at=now,
        )
        aggregate = self._budget_repository.create(budget)
        return self._view(aggregate, event.guest_count)

    def get(self, owner_id: UUID, raw_event_id: str) -> BudgetView:
        event = self._require_event(owner_id, raw_event_id)
        aggregate = self._budget_repository.get_by_event(event.event_id)
        if aggregate is None:
            raise ResourceNotFoundError(_BUDGET_NOT_FOUND)
        return self._view(aggregate, event.guest_count)

    def update(self, owner_id: UUID, raw_event_id: str, payload: BudgetUpdate) -> BudgetView:
        event = self._require_event(owner_id, raw_event_id)
        aggregate = self._require_budget(event.event_id)
        current = aggregate.budget
        self._ensure_version(current, payload.expected_version)

        changes = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
        issues = [
            ValidationIssue(field=f"body.{field}", message="This field cannot be null.")
            for field, value in changes.items()
            if value is None
        ]
        if issues:
            raise DomainValidationError(issues)

        total_limit = changes.get("total_limit", current.total_limit)
        if "reserve" in changes:
            reserve_type, reserve_value = self._reserve_values(payload.reserve)
        else:
            reserve_type, reserve_value = current.reserve_type, current.reserve_value
        self._validate_reserve(total_limit, reserve_type, reserve_value)

        if (
            total_limit == current.total_limit
            and reserve_type == current.reserve_type
            and reserve_value == current.reserve_value
        ):
            return self._view(aggregate, event.guest_count)

        updated_at = max(self._now(), current.updated_at + timedelta(microseconds=1))
        updated = self._budget_repository.update_budget(
            current.budget_id,
            payload.expected_version,
            total_limit=total_limit,
            reserve_type=reserve_type,
            reserve_value=reserve_value,
            updated_at=updated_at,
        )
        return self._view(updated, event.guest_count)

    def add_expense(self, owner_id: UUID, raw_event_id: str, payload: ExpenseCreate) -> BudgetView:
        event = self._require_event(owner_id, raw_event_id)
        aggregate = self._require_budget(event.event_id)
        now = self._now()
        expense = Expense(
            expense_id=uuid4(),
            budget_id=aggregate.budget.budget_id,
            category=payload.category,
            name=payload.name,
            amount=payload.amount,
            amount_status=payload.amount_status,
            notes=payload.notes,
            created_at=now,
            updated_at=now,
        )
        updated = self._budget_repository.add_expense(
            aggregate.budget.budget_id,
            payload.expected_version,
            expense=expense,
            updated_at=max(now, aggregate.budget.updated_at + timedelta(microseconds=1)),
        )
        return self._view(updated, event.guest_count)

    def update_expense(
        self,
        owner_id: UUID,
        raw_event_id: str,
        raw_expense_id: str,
        payload: ExpenseUpdate,
    ) -> BudgetView:
        event = self._require_event(owner_id, raw_event_id)
        expense_id = parse_uuid(raw_expense_id, _BUDGET_NOT_FOUND)
        aggregate = self._require_budget(event.event_id)
        current = aggregate.budget
        self._ensure_version(current, payload.expected_version)

        existing = next(
            (expense for expense in aggregate.expenses if expense.expense_id == expense_id),
            None,
        )
        if existing is None:
            raise ResourceNotFoundError(_BUDGET_NOT_FOUND)

        changes = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
        issues = [
            ValidationIssue(field=f"body.{field}", message="This field cannot be null.")
            for field, value in changes.items()
            if value is None and field != "notes"
        ]
        if issues:
            raise DomainValidationError(issues)

        candidate = replace(existing, **changes)
        if candidate == existing:
            return self._view(aggregate, event.guest_count)

        now = self._now()
        updated_expense = replace(
            candidate,
            updated_at=max(now, existing.updated_at + timedelta(microseconds=1)),
        )
        updated = self._budget_repository.update_expense(
            current.budget_id,
            expense_id,
            payload.expected_version,
            expense=updated_expense,
            updated_at=max(now, current.updated_at + timedelta(microseconds=1)),
        )
        return self._view(updated, event.guest_count)

    def delete_expense(
        self,
        owner_id: UUID,
        raw_event_id: str,
        raw_expense_id: str,
        expected_version: int,
    ) -> BudgetView:
        event = self._require_event(owner_id, raw_event_id)
        expense_id = parse_uuid(raw_expense_id, _BUDGET_NOT_FOUND)
        aggregate = self._require_budget(event.event_id)
        now = self._now()
        updated = self._budget_repository.delete_expense(
            aggregate.budget.budget_id,
            expense_id,
            expected_version,
            updated_at=max(now, aggregate.budget.updated_at + timedelta(microseconds=1)),
        )
        return self._view(updated, event.guest_count)

    def _require_event(self, owner_id: UUID, raw_event_id: str) -> Event:
        event_id = parse_uuid(raw_event_id, _EVENT_NOT_FOUND)
        event = self._event_repository.get(event_id, owner_id)
        if event is None:
            raise ResourceNotFoundError(_EVENT_NOT_FOUND)
        return event

    def _require_budget(self, event_id: UUID) -> BudgetAggregate:
        aggregate = self._budget_repository.get_by_event(event_id)
        if aggregate is None:
            raise ResourceNotFoundError(_BUDGET_NOT_FOUND)
        return aggregate

    @staticmethod
    def _ensure_version(budget: Budget, expected_version: int) -> None:
        if budget.version != expected_version:
            raise ResourceConflictError(_CONFLICT_MESSAGE)

    def _view(self, aggregate: BudgetAggregate, guest_count: int) -> BudgetView:
        calculation = calculate_budget_summary(
            total_limit=aggregate.budget.total_limit,
            reserve_type=aggregate.budget.reserve_type,
            reserve_value=aggregate.budget.reserve_value,
            currency=aggregate.budget.currency,
            expenses=aggregate.expenses,
            guest_count=guest_count,
        )
        return BudgetView(
            budget=aggregate.budget,
            expenses=aggregate.expenses,
            calculation=calculation,
            guest_count=guest_count,
        )

    @staticmethod
    def _reserve_values(reserve: object) -> tuple[ReserveType, Decimal]:
        if reserve is None:
            return ReserveType.PERCENTAGE, Decimal("0.00")
        if isinstance(reserve, PercentageReserve):
            return ReserveType.PERCENTAGE, reserve.value
        if isinstance(reserve, FixedReserve):
            return ReserveType.FIXED_AMOUNT, reserve.value
        raise RuntimeError("Unsupported reserve configuration.")

    @staticmethod
    def _validate_reserve(
        total_limit: Decimal,
        reserve_type: ReserveType,
        reserve_value: Decimal,
    ) -> None:
        if reserve_type == ReserveType.FIXED_AMOUNT and reserve_value > total_limit:
            raise DomainValidationError(
                [
                    ValidationIssue(
                        field="body.reserve.value",
                        message="Reserve amount cannot exceed the total limit.",
                    )
                ]
            )

    def _now(self) -> datetime:
        return coerce_utc(self._clock())
