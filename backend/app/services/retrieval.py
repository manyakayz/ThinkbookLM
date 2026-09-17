from __future__ import annotations
"""
Retrieval service — semantic search over indexed document chunks.

Responsibility:
  1. Validate the request (empty query, invalid top_k).
  2. Generate a query embedding via the embedding service.
  3. Resolve notebook scope → list of document IDs.
  4. Query ChromaDB with a metadata filter.
  5. Enrich results with full provenance from PostgreSQL.
  6. Return a structured list of RetrievalResult objects.

Distance semantics
------------------
ChromaDB is configured with cosine distance ("hnsw:space": "cosine").
Cosine distance ∈ [0, 2], where:
  0   = identical
  1   = orthogonal
  2   = opposite
Lower is better. Results are returned sorted ascending (best first).
The API response exposes the raw distance value and calls it `distance`
— NOT "similarity" — to avoid ambiguity.
"""

import logging

from app.models.retrieval import RetrievalResult
from app.repositories import chunks as chunks_repo
from app.repositories import documents as documents_repo
from app.services import db, embedding, vector_store

logger = logging.getLogger(__name__)


class RetrievalError(Exception):
    """Raised for user-attributable retrieval errors (empty query, bad scope)."""


def retrieve(
    *,
    query: str,
    notebook_id: int,
    document_ids: list[int],
    top_k: int,
) -> list[RetrievalResult]:
    """Run a semantic search and return enriched results.

    Args:
        query:        Natural-language query string.
        notebook_id:  Restrict to documents in this notebook.
        document_ids: Further restrict to these specific documents.
                      Empty list = search all documents in the notebook.
        top_k:        Maximum number of results to return.

    Returns:
        List of RetrievalResult sorted by ascending cosine distance.
    """
    query = query.strip()
    if not query:
        raise RetrievalError("Query must not be empty.")

    pool = db.get_pool()

    # --- Resolve scope: if document_ids provided, validate they belong to notebook ---
    if document_ids:
        with pool.connection() as conn:
            notebook_doc_ids = set(documents_repo.list_ids_for_notebook(conn, notebook_id))
        invalid = [did for did in document_ids if did not in notebook_doc_ids]
        if invalid:
            raise RetrievalError(
                f"Document(s) {invalid} do not belong to notebook {notebook_id}."
            )

    # --- Embed the query ---
    logger.info("Embedding query for notebook=%d top_k=%d", notebook_id, top_k)
    query_embedding = embedding.embed_query(query)

    # --- Query ChromaDB ---
    logger.info(
        "Querying ChromaDB — notebook=%d doc_ids=%s top_k=%d",
        notebook_id, document_ids or "all", top_k,
    )
    raw = vector_store.query(
        embedding=query_embedding,
        notebook_id=notebook_id,
        document_ids=document_ids,
        top_k=top_k,
    )

    # ChromaDB returns lists-of-lists (one per query_embedding)
    ids = raw.get("ids", [[]])[0]
    metadatas = raw.get("metadatas", [[]])[0]
    distances = raw.get("distances", [[]])[0]

    if not ids:
        logger.info("No results for query in notebook=%d", notebook_id)
        return []

    # --- Enrich with PostgreSQL provenance ---
    # Extract PostgreSQL chunk IDs from metadata (ChromaDB stores them)
    pg_chunk_ids = [int(m["chunk_id"]) for m in metadatas]

    # Build lookup by chunk_id for fast access
    with pool.connection() as conn:
        pg_chunks = chunks_repo.get_by_ids(conn, pg_chunk_ids)
        pg_chunk_map = {c.id: c for c in pg_chunks}

        # Also need document names
        doc_ids_needed = list({int(m["document_id"]) for m in metadatas})
        docs = [documents_repo.get_by_id(conn, did) for did in doc_ids_needed]
        doc_map = {d.id: d for d in docs if d is not None}

    # --- Build structured results ---
    results: list[RetrievalResult] = []
    for vector_id, meta, distance in zip(ids, metadatas, distances):
        chunk_id = int(meta["chunk_id"])
        doc_id = int(meta["document_id"])
        pg_chunk = pg_chunk_map.get(chunk_id)
        pg_doc = doc_map.get(doc_id)

        if pg_chunk is None or pg_doc is None:
            # Vector exists in ChromaDB but PG record is gone — stale index
            logger.warning("Stale vector %s — PG record missing, skipping", vector_id)
            continue

        results.append(
            RetrievalResult(
                vector_id=vector_id,
                chunk_id=chunk_id,
                document_id=doc_id,
                chunk_index=pg_chunk.chunk_index,
                document_name=pg_doc.original_filename,
                file_type=pg_doc.file_type,
                page_number=pg_chunk.page_number,
                section=pg_chunk.section,
                char_start=pg_chunk.char_start,
                char_end=pg_chunk.char_end,
                text=pg_chunk.text,
                distance=round(float(distance), 6),
            )
        )

    logger.info(
        "Retrieval complete — %d results for notebook=%d", len(results), notebook_id
    )
    return results
