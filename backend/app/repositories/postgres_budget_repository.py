"""PostgreSQL-backed budget repository with atomic versioned mutations."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from psycopg import Cursor
from psycopg.errors import ForeignKeyViolation, UniqueViolation

from app.core.exceptions import ResourceConflictError, ResourceNotFoundError
from app.db.postgres import PostgresDatabase
from app.models.budget import Budget, Expense, ExpenseStatus, ReserveType
from app.repositories.budget_repository import BudgetAggregate, BudgetRepository

_BUDGET_COLUMNS = (
    "id, event_id, total_limit, currency, reserve_type, reserve_value, version, "
    "created_at, updated_at"
)
_EXPENSE_COLUMNS = (
    "id, budget_id, category, name, amount, amount_status, notes, created_at, updated_at"
)

_CONFLICT_MESSAGE = "The budget was modified by another request."
_NOT_FOUND_MESSAGE = "Budget or expense not found."


def _row_to_budget(row: dict[str, Any]) -> Budget:
    return Budget(
        budget_id=row["id"],
        event_id=row["event_id"],
        total_limit=row["total_limit"],
        currency=row["currency"],
        reserve_type=ReserveType(row["reserve_type"]),
        reserve_value=row["reserve_value"],
        version=row["version"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_expense(row: dict[str, Any]) -> Expense:
    return Expense(
        expense_id=row["id"],
        budget_id=row["budget_id"],
        category=row["category"],
        name=row["name"],
        amount=row["amount"],
        amount_status=ExpenseStatus(row["amount_status"]),
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class PostgresBudgetRepository(BudgetRepository):
    """Store budgets and expenses in Supabase PostgreSQL with row-level locking."""

    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    def create(self, budget: Budget) -> BudgetAggregate:
        with self._database.connection() as connection, connection.cursor() as cursor:
            try:
                cursor.execute(
                    f"""
                    INSERT INTO public.event_budgets (
                        id, event_id, total_limit, currency, reserve_type, reserve_value,
                        version, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING {_BUDGET_COLUMNS}
                    """,
                    (
                        budget.budget_id,
                        budget.event_id,
                        budget.total_limit,
                        budget.currency,
                        budget.reserve_type.value,
                        budget.reserve_value,
                        budget.version,
                        budget.created_at,
                        budget.updated_at,
                    ),
                )
            except UniqueViolation as exc:
                raise ResourceConflictError("An event budget already exists.") from exc
            except ForeignKeyViolation as exc:
                raise ResourceNotFoundError(_NOT_FOUND_MESSAGE) from exc
            row = cursor.fetchone()

        if row is None:
            raise RuntimeError("The budget insert returned no row.")
        return BudgetAggregate(budget=_row_to_budget(row), expenses=())

    def get_by_event(self, event_id: UUID) -> BudgetAggregate | None:
        with self._database.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {_BUDGET_COLUMNS} FROM public.event_budgets WHERE event_id = %s",
                (event_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            expenses = self._fetch_expenses(cursor, row["id"])
        return BudgetAggregate(budget=_row_to_budget(row), expenses=expenses)

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
        with self._database.connection() as connection, connection.cursor() as cursor:
            self._lock_budget(cursor, budget_id, expected_version)
            cursor.execute(
                f"""
                UPDATE public.event_budgets
                SET total_limit = %s,
                    reserve_type = %s,
                    reserve_value = %s,
                    version = version + 1,
                    updated_at = %s
                WHERE id = %s
                RETURNING {_BUDGET_COLUMNS}
                """,
                (
                    total_limit,
                    reserve_type.value,
                    reserve_value,
                    updated_at,
                    budget_id,
                ),
            )
            row = cursor.fetchone()
            if row is None:
                raise ResourceNotFoundError(_NOT_FOUND_MESSAGE)
            expenses = self._fetch_expenses(cursor, budget_id)
        return BudgetAggregate(budget=_row_to_budget(row), expenses=expenses)

    def add_expense(
        self,
        budget_id: UUID,
        expected_version: int,
        *,
        expense: Expense,
        updated_at: datetime,
    ) -> BudgetAggregate:
        with self._database.connection() as connection, connection.cursor() as cursor:
            self._lock_budget(cursor, budget_id, expected_version)
            cursor.execute(
                f"""
                INSERT INTO public.budget_expenses (
                    id, budget_id, category, name, amount, amount_status, notes,
                    created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING {_EXPENSE_COLUMNS}
                """,
                (
                    expense.expense_id,
                    budget_id,
                    expense.category,
                    expense.name,
                    expense.amount,
                    expense.amount_status.value,
                    expense.notes,
                    expense.created_at,
                    expense.updated_at,
                ),
            )
            if cursor.fetchone() is None:
                raise RuntimeError("The expense insert returned no row.")
            row = self._increment_version(cursor, budget_id, updated_at)
            expenses = self._fetch_expenses(cursor, budget_id)
        return BudgetAggregate(budget=_row_to_budget(row), expenses=expenses)

    def update_expense(
        self,
        budget_id: UUID,
        expense_id: UUID,
        expected_version: int,
        *,
        expense: Expense,
        updated_at: datetime,
    ) -> BudgetAggregate:
        with self._database.connection() as connection, connection.cursor() as cursor:
            self._lock_budget(cursor, budget_id, expected_version)
            cursor.execute(
                f"""
                UPDATE public.budget_expenses
                SET category = %s,
                    name = %s,
                    amount = %s,
                    amount_status = %s,
                    notes = %s,
                    updated_at = %s
                WHERE id = %s AND budget_id = %s
                RETURNING {_EXPENSE_COLUMNS}
                """,
                (
                    expense.category,
                    expense.name,
                    expense.amount,
                    expense.amount_status.value,
                    expense.notes,
                    expense.updated_at,
                    expense_id,
                    budget_id,
                ),
            )
            if cursor.fetchone() is None:
                raise ResourceNotFoundError(_NOT_FOUND_MESSAGE)
            row = self._increment_version(cursor, budget_id, updated_at)
            expenses = self._fetch_expenses(cursor, budget_id)
        return BudgetAggregate(budget=_row_to_budget(row), expenses=expenses)

    def delete_expense(
        self,
        budget_id: UUID,
        expense_id: UUID,
        expected_version: int,
        *,
        updated_at: datetime,
    ) -> BudgetAggregate:
        with self._database.connection() as connection, connection.cursor() as cursor:
            self._lock_budget(cursor, budget_id, expected_version)
            cursor.execute(
                "DELETE FROM public.budget_expenses WHERE id = %s AND budget_id = %s RETURNING id",
                (expense_id, budget_id),
            )
            if cursor.fetchone() is None:
                raise ResourceNotFoundError(_NOT_FOUND_MESSAGE)
            row = self._increment_version(cursor, budget_id, updated_at)
            expenses = self._fetch_expenses(cursor, budget_id)
        return BudgetAggregate(budget=_row_to_budget(row), expenses=expenses)

    @staticmethod
    def _lock_budget(
        cursor: Cursor[dict[str, Any]],
        budget_id: UUID,
        expected_version: int,
    ) -> None:
        cursor.execute(
            f"SELECT {_BUDGET_COLUMNS} FROM public.event_budgets WHERE id = %s FOR UPDATE",
            (budget_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise ResourceNotFoundError(_NOT_FOUND_MESSAGE)
        if row["version"] != expected_version:
            raise ResourceConflictError(_CONFLICT_MESSAGE)

    @staticmethod
    def _increment_version(
        cursor: Cursor[dict[str, Any]],
        budget_id: UUID,
        updated_at: datetime,
    ) -> dict[str, Any]:
        cursor.execute(
            f"""
            UPDATE public.event_budgets
            SET version = version + 1, updated_at = %s
            WHERE id = %s
            RETURNING {_BUDGET_COLUMNS}
            """,
            (updated_at, budget_id),
        )
        row = cursor.fetchone()
        if row is None:
            raise ResourceNotFoundError(_NOT_FOUND_MESSAGE)
        return row

    @staticmethod
    def _fetch_expenses(
        cursor: Cursor[dict[str, Any]],
        budget_id: UUID,
    ) -> tuple[Expense, ...]:
        cursor.execute(
            f"""
            SELECT {_EXPENSE_COLUMNS}
            FROM public.budget_expenses
            WHERE budget_id = %s
            ORDER BY created_at ASC, id ASC
            """,
            (budget_id,),
        )
        return tuple(_row_to_expense(row) for row in cursor.fetchall())
