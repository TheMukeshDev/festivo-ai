"""Thread-safe in-memory budget repository for development and tests."""

import copy
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from threading import RLock
from uuid import UUID

from app.core.exceptions import ResourceConflictError, ResourceNotFoundError
from app.models.budget import Budget, Expense, ReserveType
from app.repositories.budget_repository import BudgetAggregate, BudgetRepository

_CONFLICT_MESSAGE = "The budget was modified by another request."
_NOT_FOUND_MESSAGE = "Budget or expense not found."


class InMemoryBudgetRepository(BudgetRepository):
    """Process-local repository implementing the same version semantics as PostgreSQL."""

    def __init__(self) -> None:
        self._budgets: dict[UUID, Budget] = {}
        self._budget_by_event: dict[UUID, UUID] = {}
        self._expenses: dict[UUID, dict[UUID, Expense]] = {}
        self._lock = RLock()

    def create(self, budget: Budget) -> BudgetAggregate:
        with self._lock:
            if budget.event_id in self._budget_by_event:
                raise ResourceConflictError("An event budget already exists.")
            self._budgets[budget.budget_id] = copy.deepcopy(budget)
            self._budget_by_event[budget.event_id] = budget.budget_id
            self._expenses[budget.budget_id] = {}
            return self._snapshot(budget)

    def get_by_event(self, event_id: UUID) -> BudgetAggregate | None:
        with self._lock:
            budget_id = self._budget_by_event.get(event_id)
            if budget_id is None:
                return None
            return self._snapshot(self._budgets[budget_id])

    def update_budget(
        self,
        budget_id: UUID,
        expected_version: int,
        *,
        total_limit: Decimal,
        reserve_type: ReserveType,
        reserve_value: Decimal,
        updated_at: datetime,
    ) -> BudgetAggregate:
        with self._lock:
            current = self._locked_budget(budget_id, expected_version)
            updated = replace(
                current,
                total_limit=total_limit,
                reserve_type=reserve_type,
                reserve_value=reserve_value,
                version=current.version + 1,
                updated_at=updated_at,
            )
            self._budgets[budget_id] = updated
            return self._snapshot(updated)

    def add_expense(
        self,
        budget_id: UUID,
        expected_version: int,
        *,
        expense: Expense,
        updated_at: datetime,
    ) -> BudgetAggregate:
        with self._lock:
            current = self._locked_budget(budget_id, expected_version)
            if expense.budget_id != budget_id:
                raise ResourceNotFoundError(_NOT_FOUND_MESSAGE)
            if expense.expense_id in self._expenses[budget_id]:
                raise ResourceConflictError(_CONFLICT_MESSAGE)
            self._expenses[budget_id][expense.expense_id] = copy.deepcopy(expense)
            updated = replace(
                current,
                version=current.version + 1,
                updated_at=updated_at,
            )
            self._budgets[budget_id] = updated
            return self._snapshot(updated)

    def update_expense(
        self,
        budget_id: UUID,
        expense_id: UUID,
        expected_version: int,
        *,
        expense: Expense,
        updated_at: datetime,
    ) -> BudgetAggregate:
        with self._lock:
            current = self._locked_budget(budget_id, expected_version)
            existing = self._expenses[budget_id].get(expense_id)
            if existing is None:
                raise ResourceNotFoundError(_NOT_FOUND_MESSAGE)
            updated_expense = replace(
                existing,
                category=expense.category,
                name=expense.name,
                amount=expense.amount,
                amount_status=expense.amount_status,
                notes=expense.notes,
                updated_at=expense.updated_at,
            )
            self._expenses[budget_id][expense_id] = updated_expense
            updated = replace(
                current,
                version=current.version + 1,
                updated_at=updated_at,
            )
            self._budgets[budget_id] = updated
            return self._snapshot(updated)

    def delete_expense(
        self,
        budget_id: UUID,
        expense_id: UUID,
        expected_version: int,
        *,
        updated_at: datetime,
    ) -> BudgetAggregate:
        with self._lock:
            current = self._locked_budget(budget_id, expected_version)
            if self._expenses[budget_id].pop(expense_id, None) is None:
                raise ResourceNotFoundError(_NOT_FOUND_MESSAGE)
            updated = replace(
                current,
                version=current.version + 1,
                updated_at=updated_at,
            )
            self._budgets[budget_id] = updated
            return self._snapshot(updated)

    def _locked_budget(self, budget_id: UUID, expected_version: int) -> Budget:
        budget = self._budgets.get(budget_id)
        if budget is None:
            raise ResourceNotFoundError(_NOT_FOUND_MESSAGE)
        if budget.version != expected_version:
            raise ResourceConflictError(_CONFLICT_MESSAGE)
        return budget

    def _snapshot(self, budget: Budget) -> BudgetAggregate:
        expenses = tuple(
            copy.deepcopy(expense)
            for expense in sorted(
                self._expenses[budget.budget_id].values(),
                key=lambda item: (item.created_at, str(item.expense_id)),
            )
        )
        return BudgetAggregate(budget=copy.deepcopy(budget), expenses=expenses)
