"""Minimal psycopg connection boundary with safe failure translation."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row
from pydantic import SecretStr

from app.core.exceptions import StorageUnavailableError


class PostgresDatabase:
    """Open short-lived psycopg connections to Supabase PostgreSQL."""

    def __init__(self, dsn: SecretStr, connect_timeout: int) -> None:
        self._dsn = dsn
        self._connect_timeout = connect_timeout

    @contextmanager
    def connection(self) -> Iterator[Connection[dict[str, Any]]]:
        """Yield a transactional connection without exposing provider details."""
        try:
            with psycopg.connect(
                self._dsn.get_secret_value(),
                connect_timeout=self._connect_timeout,
                row_factory=dict_row,
            ) as connection:
                yield connection
        except (psycopg.OperationalError, psycopg.InterfaceError) as exc:
            raise StorageUnavailableError("The database is temporarily unavailable.") from exc

    def check_connection(self) -> None:
        """Verify that PostgreSQL accepts a short-lived connection."""
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT 1 AS health_check")
            if cursor.fetchone() != {"health_check": 1}:
                raise StorageUnavailableError("The database health check failed.")
