from __future__ import annotations
from psycopg import Connection
from psycopg.rows import class_row

from app.models.chunk import Chunk

_COLUMNS = "id, document_id, chunk_index, text, page_number, section, char_start, char_end, created_at"


def insert_many(conn: Connection, document_id: int, chunks: list[dict]) -> int:
    """Bulk-insert chunk rows for a document. `chunks` items must have keys:
    chunk_index, text, page_number, section, char_start, char_end.

    Returns the number of rows inserted. Callers are expected to run this
    inside a transaction alongside the document status update, so a failure
    here rolls back cleanly without leaving partial chunk sets behind.
    """
    if not chunks:
        return 0

    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO chunks (document_id, chunk_index, text, page_number, section, char_start, char_end)
            VALUES (%(document_id)s, %(chunk_index)s, %(text)s, %(page_number)s, %(section)s, %(char_start)s, %(char_end)s)
            """,
            [{**c, "document_id": document_id} for c in chunks],
            prepare=False,
        )
        return cur.rowcount


def list_for_document(conn: Connection, document_id: int) -> list[Chunk]:
    with conn.cursor(row_factory=class_row(Chunk)) as cur:
        cur.execute(
            f"""
            SELECT {_COLUMNS}
            FROM chunks
            WHERE document_id = %s
            ORDER BY chunk_index ASC
            """,
            (document_id,),
        )
        return cur.fetchall()


def count_for_document(conn: Connection, document_id: int) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM chunks WHERE document_id = %s", (document_id,))
        return cur.fetchone()[0]


def get_by_ids(conn: Connection, chunk_ids: list[int]) -> list[Chunk]:
    """Fetch specific chunk rows by their PostgreSQL IDs.

    Used to enrich ChromaDB retrieval results with full provenance metadata
    from the authoritative PostgreSQL record.
    """
    if not chunk_ids:
        return []
    with conn.cursor(row_factory=class_row(Chunk)) as cur:
        cur.execute(
            f"SELECT {_COLUMNS} FROM chunks WHERE id = ANY(%s) ORDER BY chunk_index ASC",
            (chunk_ids,),
        )
        return cur.fetchall()

