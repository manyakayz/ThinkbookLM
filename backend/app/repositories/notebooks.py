from __future__ import annotations
from psycopg import Connection
from psycopg.rows import class_row

from app.models.notebook import Notebook


def create(conn: Connection, name: str) -> Notebook:
    with conn.cursor(row_factory=class_row(Notebook)) as cur:
        cur.execute(
            """
            INSERT INTO notebooks (name)
            VALUES (%s)
            RETURNING id, name, created_at, updated_at, 0 AS document_count
            """,
            (name,),
        )
        return cur.fetchone()


def list_all(conn: Connection) -> list[Notebook]:
    with conn.cursor(row_factory=class_row(Notebook)) as cur:
        cur.execute(
            """
            SELECT
                n.id, n.name, n.created_at, n.updated_at,
                COUNT(d.id) AS document_count
            FROM notebooks n
            LEFT JOIN documents d ON d.notebook_id = n.id
            GROUP BY n.id
            ORDER BY n.created_at DESC
            """
        )
        return cur.fetchall()


def get_by_id(conn: Connection, notebook_id: int) -> Notebook | None:
    with conn.cursor(row_factory=class_row(Notebook)) as cur:
        cur.execute(
            """
            SELECT
                n.id, n.name, n.created_at, n.updated_at,
                COUNT(d.id) AS document_count
            FROM notebooks n
            LEFT JOIN documents d ON d.notebook_id = n.id
            WHERE n.id = %s
            GROUP BY n.id
            """,
            (notebook_id,),
        )
        return cur.fetchone()


def exists(conn: Connection, notebook_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM notebooks WHERE id = %s", (notebook_id,))
        return cur.fetchone() is not None

