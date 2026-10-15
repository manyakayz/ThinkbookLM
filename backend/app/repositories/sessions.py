from __future__ import annotations
from datetime import datetime
from psycopg import Connection
from psycopg.rows import class_row

from app.models.session import UserSession

_SESSION_COLUMNS = "id, user_id, csrf_token, created_at, expires_at"


def create(
    conn: Connection,
    *,
    session_id: str,
    user_id: int,
    csrf_token: str,
    expires_at: datetime,
) -> UserSession:
    """Store a new authenticated user session."""
    with conn.cursor(row_factory=class_row(UserSession)) as cur:
        cur.execute(
            f"""
            INSERT INTO user_sessions (id, user_id, csrf_token, expires_at)
            VALUES (%s, %s, %s, %s)
            RETURNING {_SESSION_COLUMNS}
            """,
            (session_id, user_id, csrf_token, expires_at),
        )
        return cur.fetchone()


def get(conn: Connection, session_id: str) -> UserSession | None:
    """Fetch an active session by token. Returns None if non-existent or expired."""
    with conn.cursor(row_factory=class_row(UserSession)) as cur:
        cur.execute(
            f"""
            SELECT {_SESSION_COLUMNS}
            FROM user_sessions
            WHERE id = %s AND expires_at > now()
            """,
            (session_id,),
        )
        return cur.fetchone()


def delete(conn: Connection, session_id: str) -> None:
    """Invalidate a single session on logout."""
    conn.execute("DELETE FROM user_sessions WHERE id = %s", (session_id,))


def delete_for_user(conn: Connection, user_id: int) -> None:
    """Invalidate all active sessions for a user."""
    conn.execute("DELETE FROM user_sessions WHERE user_id = %s", (user_id,))


def delete_expired(conn: Connection) -> int:
    """Garbage-collect expired sessions."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM user_sessions WHERE expires_at <= now()")
        return cur.rowcount
