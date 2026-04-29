from types import SimpleNamespace

import pytest
from psycopg import pq

from langgraph.checkpoint.postgres import _internal


@pytest.fixture(autouse=True)
def clear_test_db() -> None:
    return None


def _fake_connection(*, autocommit: bool, status: pq.TransactionStatus):
    return SimpleNamespace(
        autocommit=autocommit,
        info=SimpleNamespace(transaction_status=status),
    )


def test_transactional_migration_sql_keeps_concurrent_indexes_when_idle() -> None:
    migration = "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx ON table(col);"

    assert (
        _internal.transactional_migration_sql(migration, in_transaction=False)
        == migration
    )


def test_transactional_migration_sql_strips_concurrent_indexes_in_transaction() -> None:
    migration = "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx ON table(col);"

    assert (
        _internal.transactional_migration_sql(
            migration,
            in_transaction=True,
        )
        == "CREATE INDEX IF NOT EXISTS idx ON table(col);"
    )


def test_in_transaction_detects_explicit_transaction_context() -> None:
    conn = _fake_connection(
        autocommit=True,
        status=pq.TransactionStatus.INTRANS,
    )

    assert _internal.in_transaction(conn) is True


def test_in_transaction_detects_implicit_transaction_connection() -> None:
    conn = _fake_connection(
        autocommit=False,
        status=pq.TransactionStatus.IDLE,
    )

    assert _internal.in_transaction(conn) is True


def test_migration_sql_for_connection_keeps_concurrent_indexes_for_autocommit_idle() -> (
    None
):
    conn = _fake_connection(
        autocommit=True,
        status=pq.TransactionStatus.IDLE,
    )
    migration = "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx ON table(col);"

    assert _internal.migration_sql_for_connection(conn, migration) == migration


def test_migration_sql_for_connection_strips_concurrent_indexes_for_transactions() -> (
    None
):
    conn = _fake_connection(
        autocommit=True,
        status=pq.TransactionStatus.INTRANS,
    )
    migration = "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx ON table(col);"

    assert (
        _internal.migration_sql_for_connection(conn, migration)
        == "CREATE INDEX IF NOT EXISTS idx ON table(col);"
    )
