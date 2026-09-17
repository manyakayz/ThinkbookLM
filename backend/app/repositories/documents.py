from __future__ import annotations
from psycopg import Connection
from psycopg.rows import class_row

from app.models.document import Document

_COLUMNS = """
    id, notebook_id, original_filename, file_type, file_size,
    page_count, processing_status, error_message,
    indexing_status, indexing_error,
    created_at, updated_at
"""


def create(
    conn: Connection,
    *,
    notebook_id: int,
    original_filename: str,
    stored_filename: str,
    file_type: str,
    file_size: int,
) -> Document:
    """Insert a new document row in `pending` status."""
    with conn.cursor(row_factory=class_row(Document)) as cur:
        cur.execute(
            f"""
            INSERT INTO documents
                (notebook_id, original_filename, stored_filename, file_type, file_size, processing_status)
            VALUES (%s, %s, %s, %s, %s, 'pending')
            RETURNING {_COLUMNS}
            """,
            (notebook_id, original_filename, stored_filename, file_type, file_size),
        )
        return cur.fetchone()


def list_for_notebook(conn: Connection, notebook_id: int) -> list[Document]:
    with conn.cursor(row_factory=class_row(Document)) as cur:
        cur.execute(
            f"""
            SELECT {_COLUMNS}
            FROM documents
            WHERE notebook_id = %s
            ORDER BY created_at DESC
            """,
            (notebook_id,),
        )
        return cur.fetchall()


def get_by_id(conn: Connection, document_id: int) -> Document | None:
    with conn.cursor(row_factory=class_row(Document)) as cur:
        cur.execute(f"SELECT {_COLUMNS} FROM documents WHERE id = %s", (document_id,))
        return cur.fetchone()


def get_stored_filename(conn: Connection, document_id: int) -> str | None:
    with conn.cursor() as cur:
        cur.execute("SELECT stored_filename FROM documents WHERE id = %s", (document_id,))
        row = cur.fetchone()
        return row[0] if row else None


def mark_processing(conn: Connection, document_id: int) -> None:
    conn.execute(
        "UPDATE documents SET processing_status = 'processing', updated_at = now() WHERE id = %s",
        (document_id,),
    )


def mark_completed(conn: Connection, document_id: int, *, page_count: int | None) -> Document:
    with conn.cursor(row_factory=class_row(Document)) as cur:
        cur.execute(
            f"""
            UPDATE documents
            SET processing_status = 'completed', error_message = NULL, page_count = %s, updated_at = now()
            WHERE id = %s
            RETURNING {_COLUMNS}
            """,
            (page_count, document_id),
        )
        return cur.fetchone()


def mark_failed(conn: Connection, document_id: int, *, error_message: str) -> Document:
    with conn.cursor(row_factory=class_row(Document)) as cur:
        cur.execute(
            f"""
            UPDATE documents
            SET processing_status = 'failed', error_message = %s, updated_at = now()
            WHERE id = %s
            RETURNING {_COLUMNS}
            """,
            (error_message, document_id),
        )
        return cur.fetchone()


def delete(conn: Connection, document_id: int) -> None:
    """Used to clean up the row if we can't proceed past creation (e.g. disk write failed after insert)."""
    conn.execute("DELETE FROM documents WHERE id = %s", (document_id,))


# ---- Indexing state (Milestone 2) ----------------------------------------

def mark_indexing(conn: Connection, document_id: int) -> None:
    conn.execute(
        "UPDATE documents SET indexing_status = 'indexing', updated_at = now() WHERE id = %s",
        (document_id,),
    )


def mark_indexed(conn: Connection, document_id: int) -> Document:
    with conn.cursor(row_factory=class_row(Document)) as cur:
        cur.execute(
            f"""
            UPDATE documents
            SET indexing_status = 'indexed', indexing_error = NULL, updated_at = now()
            WHERE id = %s
            RETURNING {_COLUMNS}
            """,
            (document_id,),
        )
        return cur.fetchone()


def mark_index_failed(conn: Connection, document_id: int, *, error_message: str) -> Document:
    with conn.cursor(row_factory=class_row(Document)) as cur:
        cur.execute(
            f"""
            UPDATE documents
            SET indexing_status = 'failed', indexing_error = %s, updated_at = now()
            WHERE id = %s
            RETURNING {_COLUMNS}
            """,
            (error_message, document_id),
        )
        return cur.fetchone()


def list_ids_for_notebook(conn: Connection, notebook_id: int) -> list[int]:
    """Return all document IDs belonging to a notebook (used for scope filtering)."""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM documents WHERE notebook_id = %s", (notebook_id,))
        return [row[0] for row in cur.fetchall()]

