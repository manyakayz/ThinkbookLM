from __future__ import annotations
from psycopg import Connection
from psycopg.rows import class_row

from app.models.user import User, UserInDB

_USER_COLUMNS = "id, full_name, email, created_at, updated_at"
_USER_IN_DB_COLUMNS = "id, full_name, email, password_hash, created_at, updated_at"


def create(conn: Connection, *, full_name: str, email: str, password_hash: str) -> User:
    """Create a new user record. Expects normalized email."""
    with conn.cursor(row_factory=class_row(User)) as cur:
        cur.execute(
            f"""
            INSERT INTO users (full_name, email, password_hash)
            VALUES (%s, %s, %s)
            RETURNING {_USER_COLUMNS}
            """,
            (full_name, email.strip().lower(), password_hash),
        )
        return cur.fetchone()


def get_by_id(conn: Connection, user_id: int) -> User | None:
    """Fetch user by primary key."""
    with conn.cursor(row_factory=class_row(User)) as cur:
        cur.execute(
            f"SELECT {_USER_COLUMNS} FROM users WHERE id = %s",
            (user_id,),
        )
        return cur.fetchone()


def get_by_email(conn: Connection, email: str) -> UserInDB | None:
    """Fetch user by normalized email, including password_hash for authentication."""
    with conn.cursor(row_factory=class_row(UserInDB)) as cur:
        cur.execute(
            f"SELECT {_USER_IN_DB_COLUMNS} FROM users WHERE email = %s",
            (email.strip().lower(),),
        )
        return cur.fetchone()


def exists_by_email(conn: Connection, email: str) -> bool:
    """Check if an account with this normalized email already exists."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM users WHERE email = %s",
            (email.strip().lower(),),
        )
        return cur.fetchone() is not None
