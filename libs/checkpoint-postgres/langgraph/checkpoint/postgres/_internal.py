"""Shared utility functions for the Postgres checkpoint & storage classes."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Protocol

from psycopg import Connection, pq
from psycopg.rows import DictRow
from psycopg_pool import ConnectionPool

Conn = Connection[DictRow] | ConnectionPool[Connection[DictRow]]


class SupportsMigrationExecution(Protocol):
    autocommit: bool
    info: Any


def in_transaction(conn: SupportsMigrationExecution) -> bool:
    return (
        not conn.autocommit or conn.info.transaction_status != pq.TransactionStatus.IDLE
    )


def transactional_migration_sql(migration: str, *, in_transaction: bool) -> str:
    if in_transaction:
        return migration.replace("CREATE INDEX CONCURRENTLY", "CREATE INDEX")
    return migration


def migration_sql_for_connection(
    conn: SupportsMigrationExecution, migration: str
) -> str:
    return transactional_migration_sql(migration, in_transaction=in_transaction(conn))


@contextmanager
def get_connection(conn: Conn) -> Iterator[Connection[DictRow]]:
    if isinstance(conn, Connection):
        yield conn
    elif isinstance(conn, ConnectionPool):
        with conn.connection() as conn:
            yield conn
    else:
        raise TypeError(f"Invalid connection type: {type(conn)}")
