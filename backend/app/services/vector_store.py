from __future__ import annotations
"""
ChromaDB integration — vector storage and retrieval (Milestone 2).

Replaces the stub from Milestone 0. All ChromaDB calls go through this
module; no other file in the codebase imports chromadb directly.

Collection design
-----------------
One collection ("thinkbook_chunks") holds all vectors from all notebooks
and documents. Scope filtering (notebook / document) is done via ChromaDB's
`where` metadata filter — which is more flexible than separate collections
and avoids collection-proliferation on a laptop-scale deployment.

Vector ID format
----------------
  chunk:<document_id>:<chunk_index>

Deterministic: given the PostgreSQL chunk record, we always know its
ChromaDB ID. Given a ChromaDB result, we can reconstruct the PostgreSQL
primary key. Upsert semantics ensure re-indexing is safe.

Metadata stored per vector (kept flat; ChromaDB requires primitive values)
--------------------------------------------------------------------------
  document_id     int
  chunk_id        int   (PostgreSQL chunks.id)
  notebook_id     int
  chunk_index     int
  source_filename str
  file_type       str
  page_number     int | -1  (-1 = not available)
  section         str | ""  ("" = not available)
"""

import logging
import os
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

_COLLECTION_NAME = "thinkbook_chunks"
_client = None


# ---------------------------------------------------------------------------
# Client / collection access
# ---------------------------------------------------------------------------

def get_client():
    """Return a process-wide persistent ChromaDB client (lazy init)."""
    global _client
    if _client is None:
        import chromadb  # lazy import so a broken install doesn't block startup
        settings = get_settings()
        os.makedirs(settings.chroma_persist_dir, exist_ok=True)
        _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        logger.info("ChromaDB client initialised at %s", settings.chroma_persist_dir)
    return _client


def get_collection():
    """Return (and lazily create) the shared chunks collection."""
    client = get_client()
    # get_or_create is idempotent — safe to call on every request
    return client.get_or_create_collection(
        name=_COLLECTION_NAME,
        # cosine distance is the standard choice for sentence/text embeddings
        metadata={"hnsw:space": "cosine"},
    )


def ping() -> tuple[bool, str | None]:
    """Confirm the client can be created and the collection is accessible."""
    try:
        col = get_collection()
        col.count()  # lightweight sanity check
        return True, None
    except Exception as exc:  # noqa: BLE001
        logger.warning("ChromaDB ping failed: %s", exc)
        return False, str(exc)


# ---------------------------------------------------------------------------
# Vector ID helpers
# ---------------------------------------------------------------------------

def make_vector_id(document_id: int, chunk_index: int) -> str:
    return f"chunk:{document_id}:{chunk_index}"


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def upsert_chunks(
    *,
    document_id: int,
    notebook_id: int,
    source_filename: str,
    file_type: str,
    chunks: list[dict],
    embeddings: list[list[float]],
) -> int:
    """Upsert chunk vectors into ChromaDB.

    `chunks` items must have keys: id (PG chunk_id), chunk_index, text,
    page_number, section.

    Returns the number of vectors upserted.
    """
    if not chunks:
        return 0

    col = get_collection()
    ids = []
    docs = []
    metas: list[dict[str, Any]] = []

    for chunk in chunks:
        ids.append(make_vector_id(document_id, chunk["chunk_index"]))
        docs.append(chunk["text"])
        metas.append({
            "document_id": document_id,
            "chunk_id": chunk["id"],
            "notebook_id": notebook_id,
            "chunk_index": chunk["chunk_index"],
            "source_filename": source_filename,
            "file_type": file_type,
            # ChromaDB metadata must be primitives; use sentinel values for None
            "page_number": chunk.get("page_number") if chunk.get("page_number") is not None else -1,
            "section": chunk.get("section") or "",
        })

    col.upsert(ids=ids, documents=docs, embeddings=embeddings, metadatas=metas)
    logger.info("Upserted %d vectors for document_id=%d", len(ids), document_id)
    return len(ids)


def delete_document(document_id: int) -> None:
    """Delete all vectors belonging to a document (used before re-indexing)."""
    col = get_collection()
    col.delete(where={"document_id": {"$eq": document_id}})
    logger.info("Deleted vectors for document_id=%d", document_id)


# ---------------------------------------------------------------------------
# Query / retrieval
# ---------------------------------------------------------------------------

def query(
    *,
    embedding: list[float],
    notebook_id: int,
    document_ids: list[int],
    top_k: int,
) -> dict:
    """Execute a semantic similarity query with scope filtering.

    Scope rules:
    - If document_ids is non-empty, restrict to those specific documents
      (which must belong to notebook_id — validated by the caller).
    - Otherwise restrict to the entire notebook.

    Returns the raw ChromaDB query result dict.
    """
    col = get_collection()

    if document_ids:
        # Filter to specific documents
        if len(document_ids) == 1:
            where_filter = {"document_id": {"$eq": document_ids[0]}}
        else:
            where_filter = {"document_id": {"$in": document_ids}}
    else:
        # Whole-notebook scope
        where_filter = {"notebook_id": {"$eq": notebook_id}}

    results = col.query(
        query_embeddings=[embedding],
        n_results=top_k,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )
    return results
