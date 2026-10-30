"""Deterministic stand-ins for the psycopg connection boundary.

Repository tests script the rows each SQL statement returns instead of dialing
Supabase, so every branch (conflicts, missing rows, filters) runs in
milliseconds without a live database.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

Row = dict[str, Any]
# A queued result is one row, several rows, ``None``, or an exception to raise.
QueuedResult = Row | list[Row] | None | BaseException


class FakeDatabase:
    """Scripted replacement for ``PostgresDatabase.connection()``."""

    def __init__(self) -> None:
        self.statements: list[tuple[str, Any]] = []
        self._results: list[QueuedResult] = []
        self._current: Row | list[Row] | None = None

    def queue(self, *results: QueuedResult) -> FakeDatabase:
        """Queue results in the exact order the repository executes SQL."""
        self._results.extend(results)
        return self

    @property
    def executed_sql(self) -> list[str]:
        return [statement for statement, _ in self.statements]

    def assert_exhausted(self) -> None:
        if self._results:
            msg = f"Unused queued results remain: {self._results!r}"
            raise AssertionError(msg)

    @contextmanager
    def connection(self) -> Iterator[FakeConnection]:
        yield FakeConnection(self)


class FakeConnection:
    """Connection that only offers the cursor context manager repositories use."""

    def __init__(self, database: FakeDatabase) -> None:
        self._database = database

    def cursor(self) -> FakeCursor:
        return FakeCursor(self._database)


class FakeCursor:
    """Cursor replaying queued results and recording every statement."""

    def __init__(self, database: FakeDatabase) -> None:
        self._database = database

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False

    def execute(self, sql: str, params: Any = None) -> None:
        normalized = " ".join(sql.split())
        self._database.statements.append((normalized, params))
        if not self._database._results:
            msg = f"Unexpected SQL executed: {normalized[:200]}"
            raise AssertionError(msg)
        result = self._database._results.pop(0)
        if isinstance(result, BaseException):
            raise result
        self._database._current = result

    def fetchone(self) -> Row | None:
        current = self._database._current
        if isinstance(current, list):
            return current[0] if current else None
        return current

    def fetchall(self) -> list[Row]:
        current = self._database._current
        if isinstance(current, list):
            return list(current)
        if current is None:
            return []
        return [current]
