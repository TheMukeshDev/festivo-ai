"""Budget persistence contract shared by memory and PostgreSQL implementations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.models.budget import Budget, Expense, ReserveType


@dataclass(frozen=True, slots=True)
class BudgetAggregate:
    """A budget and its expense items loaded as one consistent unit."""

    budget: Budget
    expenses: tuple[Expense, ...]


class BudgetRepository(ABC):
    """Persistence contract preserving optimistic budget version checks."""

    @abstractmethod
    def create(self, budget: Budget) -> BudgetAggregate:
        """Create the single budget for an event."""

    @abstractmethod
    def get_by_event(self, event_id: UUID) -> BudgetAggregate | None:
        """Load an event's budget and expenses."""

    @abstractmethod
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
        """Apply budget settings atomically and increment the version."""

    @abstractmethod
    def add_expense(
        self,
        budget_id: UUID,
        expected_version: int,
        *,
        expense: Expense,
        updated_at: datetime,
    ) -> BudgetAggregate:
        """Add an expense and increment the budget version atomically."""

    @abstractmethod
    def update_expense(
        self,
        budget_id: UUID,
        expense_id: UUID,
        expected_version: int,
        *,
        expense: Expense,
        updated_at: datetime,
    ) -> BudgetAggregate:
        """Update an expense and increment the budget version atomically."""

    @abstractmethod
    def delete_expense(
        self,
        budget_id: UUID,
        expense_id: UUID,
        expected_version: int,
        *,
        updated_at: datetime,
    ) -> BudgetAggregate:
        """Delete an expense and increment the budget version atomically."""
