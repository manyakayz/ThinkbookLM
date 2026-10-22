from __future__ import annotations
from psycopg import Connection
from psycopg.rows import class_row

from app.models.notebook import Notebook


def create(conn: Connection, name: str, user_id: int | None = None) -> Notebook:
    with conn.cursor(row_factory=class_row(Notebook)) as cur:
        cur.execute(
            """
            INSERT INTO notebooks (name, user_id)
            VALUES (%s, %s)
            RETURNING id, name, created_at, updated_at, 0 AS document_count, user_id
            """,
            (name, user_id),
        )
        return cur.fetchone()


def list_all(conn: Connection, user_id: int | None = None) -> list[Notebook]:
    with conn.cursor(row_factory=class_row(Notebook)) as cur:
        if user_id is not None:
            cur.execute(
                """
                SELECT
                    n.id, n.name, n.created_at, n.updated_at,
                    COUNT(d.id) AS document_count,
                    n.user_id
                FROM notebooks n
                LEFT JOIN documents d ON d.notebook_id = n.id
                WHERE n.user_id = %s
                GROUP BY n.id
                ORDER BY n.created_at DESC
                """,
                (user_id,),
            )
        else:
            cur.execute(
                """
                SELECT
                    n.id, n.name, n.created_at, n.updated_at,
                    COUNT(d.id) AS document_count,
                    n.user_id
                FROM notebooks n
                LEFT JOIN documents d ON d.notebook_id = n.id
                GROUP BY n.id
                ORDER BY n.created_at DESC
                """
            )
        return cur.fetchall()


def get_by_id(conn: Connection, notebook_id: int, user_id: int | None = None) -> Notebook | None:
    with conn.cursor(row_factory=class_row(Notebook)) as cur:
        if user_id is not None:
            cur.execute(
                """
                SELECT
                    n.id, n.name, n.created_at, n.updated_at,
                    COUNT(d.id) AS document_count,
                    n.user_id
                FROM notebooks n
                LEFT JOIN documents d ON d.notebook_id = n.id
                WHERE n.id = %s AND n.user_id = %s
                GROUP BY n.id
                """,
                (notebook_id, user_id),
            )
        else:
            cur.execute(
                """
                SELECT
                    n.id, n.name, n.created_at, n.updated_at,
                    COUNT(d.id) AS document_count,
                    n.user_id
                FROM notebooks n
                LEFT JOIN documents d ON d.notebook_id = n.id
                WHERE n.id = %s
                GROUP BY n.id
                """,
                (notebook_id,),
            )
        return cur.fetchone()


def exists(conn: Connection, notebook_id: int, user_id: int | None = None) -> bool:
    with conn.cursor() as cur:
        if user_id is not None:
            cur.execute("SELECT 1 FROM notebooks WHERE id = %s AND user_id = %s", (notebook_id, user_id))
        else:
            cur.execute("SELECT 1 FROM notebooks WHERE id = %s", (notebook_id,))
        return cur.fetchone() is not None


def delete(conn: Connection, notebook_id: int, user_id: int | None = None) -> bool:
    with conn.cursor() as cur:
        if user_id is not None:
            cur.execute("DELETE FROM notebooks WHERE id = %s AND user_id = %s", (notebook_id, user_id))
        else:
            cur.execute("DELETE FROM notebooks WHERE id = %s", (notebook_id,))
        return cur.rowcount > 0
