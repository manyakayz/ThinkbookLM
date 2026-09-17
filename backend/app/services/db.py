from __future__ import annotations
"""
PostgreSQL connection boundary.

Deliberately minimal for this milestone: no ORM, no schema, no migrations.
Just a lazily-created connection pool and a `ping()` helper that later
milestones (and the health endpoint) can use to check connectivity.

The pool is created lazily (on first use) rather than at import/startup time
so that the backend can start up even if Postgres isn't running yet. That's
important on a student laptop where the DB, vector store, and LLM may not
all be running at once during development.
"""


import logging

from psycopg_pool import ConnectionPool

from app.config import get_settings

logger = logging.getLogger(__name__)

_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    """Return a process-wide connection pool, creating it on first call.

    `ConnectionPool` itself connects lazily in the background (open=False
    below), so constructing it does not require Postgres to be reachable.
    Actually borrowing a connection (e.g. via `ping()`) is what can fail.
    """
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = ConnectionPool(
            conninfo=settings.postgres_dsn,
            min_size=0,
            max_size=5,
            open=False,
            kwargs={"connect_timeout": 3},
        )
        _pool.open()
    return _pool


def ping() -> tuple[bool, str | None]:
    """Try to run `SELECT 1`. Returns (ok, error_message)."""
    try:
        with get_pool().connection(timeout=3) as conn:
            conn.execute("SELECT 1")
        return True, None
    except Exception as exc:  # noqa: BLE001 - we want to report *any* failure
        logger.warning("Postgres ping failed: %s", exc)
        return False, str(exc)

