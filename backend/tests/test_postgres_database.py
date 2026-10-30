"""Connection pooling, request scoping, and failure translation paths."""

from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import psycopg
import pytest
from psycopg.pq import TransactionStatus
from pydantic import SecretStr

import app.db.postgres as postgres_module
from app.core.exceptions import StorageUnavailableError
from app.db.postgres import PostgresDatabase
from tests.fakes import FakeDatabase

DSN = "postgresql://festivo:secret@localhost:5432/festivo_test"


class FakePsycopgConnection:
    """Connection double exposing the transaction-status contract."""

    def __init__(self, status: TransactionStatus) -> None:
        self.info = SimpleNamespace(transaction_status=status)
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class ExplodingConnection(FakePsycopgConnection):
    """Connection whose rollback already lost the server connection."""

    def rollback(self) -> None:
        msg = "connection closed"
        raise psycopg.OperationalError(msg)


class FakePool:
    """Stand-in for ``psycopg_pool.ConnectionPool``."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.init_args = args
        self.init_kwargs = kwargs
        self.returned: list[FakePsycopgConnection] = []
        self.next_connection: FakePsycopgConnection = FakePsycopgConnection(TransactionStatus.IDLE)
        self.getconn_error: psycopg.Error | None = None
        self.connection_error: psycopg.Error | None = None
        self.scripted: FakeDatabase | None = None

    def getconn(self) -> FakePsycopgConnection:
        if self.getconn_error is not None:
            raise self.getconn_error
        return self.next_connection

    def putconn(self, connection: FakePsycopgConnection) -> None:
        self.returned.append(connection)

    @contextmanager
    def connection(self) -> Iterator[Any]:
        if self.connection_error is not None:
            raise self.connection_error
        if self.scripted is not None:
            with self.scripted.connection() as connection:
                yield connection
            return
        yield self.next_connection


@pytest.fixture
def pools(monkeypatch: pytest.MonkeyPatch) -> list[FakePool]:
    """Replace the real pool factory with a recording fake."""
    created: list[FakePool] = []

    def factory(*args: Any, **kwargs: Any) -> FakePool:
        pool = FakePool(*args, **kwargs)
        created.append(pool)
        return pool

    monkeypatch.setattr(postgres_module, "ConnectionPool", factory)
    return created


def make_database() -> PostgresDatabase:
    return PostgresDatabase(SecretStr(DSN), 3)


class TestPoolLifecycle:
    def test_the_pool_is_created_once_and_configured_to_fail_fast(
        self,
        pools: list[FakePool],
    ) -> None:
        database = make_database()

        first = database._get_pool()
        second = database._get_pool()

        assert first is second
        assert len(pools) == 1
        assert pools[0].init_kwargs["open"] is True
        assert pools[0].init_kwargs["kwargs"]["connect_timeout"] == 3

    def test_pool_construction_is_not_attempted_before_first_use(
        self,
        pools: list[FakePool],
    ) -> None:
        database = make_database()

        assert pools == []
        assert database._pool is None

    def test_connection_outside_a_scope_yields_a_pooled_connection(
        self,
        pools: list[FakePool],
    ) -> None:
        database = make_database()

        with database.connection() as connection:
            assert connection is pools[0].next_connection

        assert len(pools) == 1

    def test_operational_failures_are_translated_at_the_pool_boundary(
        self,
        pools: list[FakePool],
    ) -> None:
        database = make_database()
        pool = database._get_pool()
        pool.connection_error = psycopg.OperationalError("dial failed")

        with pytest.raises(StorageUnavailableError), database.connection():
            pass

    def test_interface_failures_are_translated_at_the_pool_boundary(
        self,
        pools: list[FakePool],
    ) -> None:
        database = make_database()
        pool = database._get_pool()
        pool.connection_error = psycopg.InterfaceError("dropped")

        with pytest.raises(StorageUnavailableError), database.connection():
            pass


class TestRequestScope:
    def test_a_scope_borrows_one_connection_for_every_inner_call(
        self,
        pools: list[FakePool],
    ) -> None:
        database = make_database()
        pool = database._get_pool()

        with (
            database.request_scope(),
            database.connection() as first,
            database.connection() as second,
        ):
            assert first is second

        assert pool.returned == [first]

    def test_a_borrow_failure_is_translated_without_leaking(
        self,
        pools: list[FakePool],
    ) -> None:
        database = make_database()
        pool = database._get_pool()
        pool.getconn_error = psycopg.OperationalError("pool exhausted")

        with (
            database.request_scope(),
            pytest.raises(StorageUnavailableError),
            database.connection(),
        ):
            pass

        assert pool.returned == []

    def test_an_idle_scope_returns_the_connection_without_committing(
        self,
        pools: list[FakePool],
    ) -> None:
        database = make_database()
        pool = database._get_pool()

        with database.request_scope(), database.connection():
            pass

        assert pool.next_connection.commits == 0
        assert pool.next_connection.rollbacks == 0
        assert pool.returned == [pool.next_connection]

    def test_an_open_transaction_is_committed_once_per_request(
        self,
        pools: list[FakePool],
    ) -> None:
        database = make_database()
        pool = database._get_pool()
        pool.next_connection = FakePsycopgConnection(TransactionStatus.INTRANS)

        with database.request_scope(), database.connection():
            pass

        assert pool.next_connection.commits == 1
        assert pool.returned == [pool.next_connection]

    def test_a_failed_transaction_is_rolled_back_once_per_request(
        self,
        pools: list[FakePool],
    ) -> None:
        database = make_database()
        pool = database._get_pool()
        pool.next_connection = FakePsycopgConnection(TransactionStatus.INERROR)

        with database.request_scope(), database.connection():
            pass

        assert pool.next_connection.rollbacks == 1
        assert pool.returned == [pool.next_connection]

    def test_a_nested_scope_reuses_the_outer_connection(
        self,
        pools: list[FakePool],
    ) -> None:
        database = make_database()
        pool = database._get_pool()

        with database.request_scope():
            with database.connection() as outer:
                pass
            with database.request_scope(), database.connection() as inner:
                assert inner is outer

        assert pool.returned == [outer]

    def test_a_failing_scope_still_returns_its_connection(
        self,
        pools: list[FakePool],
    ) -> None:
        database = make_database()
        pool = database._get_pool()
        pool.next_connection = FakePsycopgConnection(TransactionStatus.INTRANS)

        with (
            pytest.raises(RuntimeError, match="handler exploded"),
            database.request_scope(),
            database.connection(),
        ):
            msg = "handler exploded"
            raise RuntimeError(msg)

        assert pool.next_connection.rollbacks == 1
        assert pool.returned == [pool.next_connection]

    def test_a_cleanup_rollback_failure_never_hides_the_original_error(
        self,
        pools: list[FakePool],
    ) -> None:
        database = make_database()
        pool = database._get_pool()
        pool.next_connection = ExplodingConnection(TransactionStatus.INERROR)

        with (
            pytest.raises(RuntimeError, match="handler exploded"),
            database.request_scope(),
            database.connection(),
        ):
            msg = "handler exploded"
            raise RuntimeError(msg)

        assert pool.returned == [pool.next_connection]

    def test_a_database_free_request_never_touches_the_pool(
        self,
        pools: list[FakePool],
    ) -> None:
        database = make_database()

        with database.request_scope():
            pass

        assert database._pool is None


class TestHealthCheck:
    def test_a_successful_probe_accepts_the_expected_row(
        self,
        pools: list[FakePool],
    ) -> None:
        database = make_database()
        pool = database._get_pool()
        pool.scripted = FakeDatabase().queue({"health_check": 1})

        database.check_connection()

        assert pool.scripted.executed_sql == ["SELECT 1 AS health_check"]

    def test_an_unexpected_probe_row_is_a_storage_failure(
        self,
        pools: list[FakePool],
    ) -> None:
        database = make_database()
        pool = database._get_pool()
        pool.scripted = FakeDatabase().queue({"health_check": 2})

        with pytest.raises(StorageUnavailableError, match="health check failed"):
            database.check_connection()
