"""Pooled psycopg connection boundary with safe failure translation."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from threading import Lock
from typing import Any

import psycopg
from psycopg import Connection
from psycopg.pq import TransactionStatus
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from pydantic import SecretStr

from app.core.exceptions import StorageUnavailableError


class _RequestConnection:
    """Lazily-acquired connection slot for the current request."""

    __slots__ = ("conn",)

    def __init__(self) -> None:
        self.conn: Connection[dict[str, Any]] | None = None


# One pooled connection is shared by every repository call inside a single
# request. Round trips to Supabase cost hundreds of milliseconds here, so the
# request scope pays for one BEGIN/COMMIT instead of one per repository call.
# The connection is only dialled if a repository actually needs it, so
# database-free endpoints (health, config status) stay free of DB latency.
_request_scope: ContextVar[_RequestConnection | None] = ContextVar(
    "festivo_request_scope", default=None
)


class PostgresDatabase:
    """Borrow pooled psycopg connections to Supabase PostgreSQL.

    Establishing a connection to Supabase costs seconds on this network, so a
    process-level pool is reused across requests instead of dialing TLS for
    every repository call, and ``request_scope()`` keeps one connection for the
    lifetime of a request.
    """

    def __init__(self, dsn: SecretStr, connect_timeout: int) -> None:
        self._dsn = dsn
        self._connect_timeout = connect_timeout
        self._pool: ConnectionPool[dict[str, Any]] | None = None
        self._pool_lock = Lock()

    def _get_pool(self) -> ConnectionPool[dict[str, Any]]:
        pool = self._pool
        if pool is not None:
            return pool
        with self._pool_lock:
            if self._pool is None:
                self._pool = ConnectionPool(
                    conninfo=self._dsn.get_secret_value(),
                    min_size=1,
                    max_size=5,
                    # Reuse connections; recycle them before Supabase closes them.
                    max_lifetime=60 * 30,
                    max_idle=60 * 5,
                    reconnect_timeout=5,
                    # Fail fast instead of stacking seconds-long dials.
                    kwargs={
                        "connect_timeout": self._connect_timeout,
                        "row_factory": dict_row,
                        "prepare_threshold": None,
                    },
                    open=True,
                )
            return self._pool

    def _borrow_for_scope(self, scope: _RequestConnection) -> Connection[dict[str, Any]]:
        if scope.conn is None:
            try:
                scope.conn = self._get_pool().getconn()
            except psycopg.Error as exc:
                raise StorageUnavailableError(
                    "The database is temporarily unavailable."
                ) from exc
        return scope.conn

    @contextmanager
    def connection(self) -> Iterator[Connection[dict[str, Any]]]:
        """Yield a connection without exposing provider details.

        Inside ``request_scope()`` every caller shares the request's single
        connection (commit happens once, when the request finishes). Outside a
        request scope (scripts, one-off checks) a pooled connection is borrowed
        for the block and committed on success, matching the previous
        per-call transaction behaviour.
        """
        scope = _request_scope.get()
        if scope is not None:
            yield self._borrow_for_scope(scope)
            return
        try:
            with self._get_pool().connection() as connection:
                yield connection
        except (psycopg.OperationalError, psycopg.InterfaceError) as exc:
            raise StorageUnavailableError("The database is temporarily unavailable.") from exc

    @contextmanager
    def request_scope(self) -> Iterator[None]:
        """Bind at most one pooled connection to the current request's context."""
        if _request_scope.get() is not None:
            # Nested scopes reuse the outer connection.
            yield
            return

        scope = _RequestConnection()
        token = _request_scope.set(scope)
        finished = False
        try:
            yield
            conn = scope.conn
            if conn is not None:
                status = conn.info.transaction_status
                if status is TransactionStatus.INTRANS:
                    # Commit once per request so writes actually persist.
                    conn.commit()
                elif status is TransactionStatus.INERROR:
                    # A failed statement aborts the transaction server-side.
                    conn.rollback()
            finished = True
        finally:
            _request_scope.reset(token)
            conn = scope.conn
            if conn is None:
                # Nothing was dialled: database-free request.
                pass
            elif finished:
                self._get_pool().putconn(conn)
            else:
                # Never return a broken connection to the pool, and never let
                # cleanup hide the original error.
                try:
                    conn.rollback()
                except psycopg.Error:
                    self._get_pool().putconn(conn, close=True)
                else:
                    self._get_pool().putconn(conn)

    def check_connection(self) -> None:
        """Verify that PostgreSQL accepts a pooled connection."""
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT 1 AS health_check")
            if cursor.fetchone() != {"health_check": 1}:
                raise StorageUnavailableError("The database health check failed.")
