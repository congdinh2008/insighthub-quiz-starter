"""Synchronous psycopg pool, used only from threadpool-backed handlers."""

import logging
import threading
from contextlib import contextmanager

from psycopg_pool import ConnectionPool, PoolTimeout
from psycopg.errors import QueryCanceled

from app.core.deadline import check_deadline, remaining_timeout
from app.core.errors import DeadlineExceeded
from pgvector.psycopg import register_vector

from app.core.config import get_settings

logger = logging.getLogger("insighthub.db")
_pool: ConnectionPool | None = None
_pool_lock = threading.Lock()


def _configure(conn):
    register_vector(conn)
    conn.commit()  # Pool configure callbacks must leave the connection idle.


def get_pool() -> ConnectionPool:
    global _pool
    with _pool_lock:
        if _pool is None:
            _pool = ConnectionPool(
                conninfo=get_settings().database_url,
                min_size=2,
                max_size=10,
                configure=_configure,
                timeout=10,
                open=True,
            )
    return _pool


class DeadlineConnection:
    """Refresh the SQL budget before every statement, including advisory locks."""
    def __init__(self, connection):
        self.connection = connection

    def __getattr__(self, name):
        return getattr(self.connection, name)

    def execute(self, query, params=None, **kwargs):
        budget = remaining_timeout(10)
        self.connection.execute("SELECT set_config('statement_timeout', %s, true)", (f"{max(1, int(budget * 1000))}ms",))
        try:
            result = self.connection.execute(query, params, **kwargs)
        except QueryCanceled:
            raise DeadlineExceeded() from None
        check_deadline()
        return result

    @contextmanager
    def transaction(self, **kwargs):
        with self.connection.transaction(**kwargs):
            yield
            check_deadline()


@contextmanager
def get_conn(*, read_only=False):
    try:
        with get_pool().connection(timeout=remaining_timeout(10)) as conn:
            bounded = DeadlineConnection(conn)
            if read_only:
                bounded.execute('SET TRANSACTION READ ONLY')
            yield bounded
            # Lock-only transactions cannot publish data. Releasing their locks
            # after error cleanup must not replace the persisted error response.
            if not read_only:
                check_deadline()  # Expired writes must roll back, never commit success.
    except PoolTimeout:
        raise DeadlineExceeded() from None


def initialize_database():
    from app.core.index import check_schema, ensure_index_identity
    from app.core.migrations import run_migrations

    get_pool().wait(timeout=15)
    with get_conn() as conn:
        run_migrations(conn)
        check_schema(conn)
        recover_interrupted_operations(conn)
        ensure_index_identity(conn, claim=False)


def recover_interrupted_operations(conn):
    """Startup fencing: no processing row can survive a process restart."""
    from psycopg.types.json import Jsonb

    with conn.transaction():
        interrupted_attempts = conn.execute(
            "UPDATE ingestion_attempts SET status='failed',error_code='interrupted',finished_at=now() "
            "WHERE status='processing' RETURNING document_id"
        ).fetchall()
        if interrupted_attempts:
            conn.execute(
                "UPDATE documents SET status='failed',chunk_count=0,embedding_identity_id=NULL,"
                "error_code='interrupted',updated_at=now() WHERE id=ANY(%s) AND status='pending'",
                ([row[0] for row in interrupted_attempts],),
            )
        conn.execute(
            "UPDATE operation_records SET status='failed',http_status=500,error_code='interrupted',"
            "response_body=%s,updated_at=now() WHERE status='processing'",
            (Jsonb({"detail": "Operation bị gián đoạn khi tiến trình khởi động lại.", "code": "interrupted"}),),
        )
        # AI Job scaffold chạy đồng bộ trong request: job còn Processing khi khởi động là job bị gián đoạn.
        if conn.execute("SELECT to_regclass('ai_jobs')").fetchone()[0] is not None:
            conn.execute(
                "UPDATE ai_jobs SET status='Failed',error_code='interrupted',finished_at=now() WHERE status='Processing'"
            )


def healthcheck() -> bool:
    try:
        from app.core.index import check_schema, ensure_index_identity

        with get_conn() as conn:
            check_schema(conn)
            ensure_index_identity(conn, claim=False)
        return True
    except Exception:
        logger.warning("Database readiness check failed")
        return False


def close_pool():
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.close()
            _pool = None
