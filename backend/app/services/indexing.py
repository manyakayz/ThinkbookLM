from __future__ import annotations
"""
Indexing service — glue between PostgreSQL chunks and ChromaDB.

Responsibility: given a document_id whose chunks are already in PostgreSQL,
generate embeddings and upsert them into ChromaDB, then update the document's
indexing_status in PostgreSQL.

Idempotency: this function first deletes any existing vectors for the
document (via vector_store.delete_document), then upserts fresh ones.
Running it twice on the same document therefore does NOT create duplicates.

Separation: this module is intentionally separate from the ingestion pipeline
so it can be:
  - called from the pipeline after successful extraction/chunking
  - called from a re-index endpoint when a previous indexing attempt failed
  - moved to a background worker in a future milestone without changing the
    extraction pipeline
"""

import logging
import time

from app.repositories import chunks as chunks_repo
from app.repositories import documents as documents_repo
from app.services import db, embedding, vector_store
from app.services.embedding import EmbeddingModelNotFound, OllamaUnavailable

logger = logging.getLogger(__name__)


def index_document(document_id: int) -> int:
    """Embed and index all chunks for a document.

    Returns the number of vectors indexed.
    Raises nothing for ordinary failures — those are recorded in the DB.

    Flow:
      1. Mark indexing_status = 'indexing'.
      2. Fetch chunks from PostgreSQL.
      3. Delete existing ChromaDB vectors (idempotency).
      4. Generate embeddings in batches.
      5. Upsert vectors to ChromaDB.
      6. Mark indexing_status = 'indexed'.
      On any error → mark indexing_status = 'failed' with error_message.
    """
    pool = db.get_pool()

    # --- 1. Fetch document + mark as indexing ---
    with pool.connection() as conn:
        document = documents_repo.get_by_id(conn, document_id)
        if document is None:
            logger.error("index_document: document_id=%d not found", document_id)
            return 0
        chunks = chunks_repo.list_for_document(conn, document_id)

    if not chunks:
        logger.warning("Document %d has no chunks — skipping indexing", document_id)
        with pool.connection() as conn:
            documents_repo.mark_index_failed(
                conn, document_id,
                error_message="No chunks found for this document.",
            )
        return 0

    with pool.connection() as conn:
        documents_repo.mark_indexing(conn, document_id)

    logger.info(
        "Indexing document %d ('%s') — %d chunks",
        document_id, document.original_filename, len(chunks),
    )

    try:
        # --- 2. Delete stale vectors (idempotency) ---
        vector_store.delete_document(document_id)

        # --- 3. Generate embeddings ---
        t0 = time.monotonic()
        texts = [c.text for c in chunks]
        embeddings = embedding.embed_texts(texts)
        embed_elapsed = time.monotonic() - t0

        logger.info(
            "Generated %d embeddings for document %d in %.2fs",
            len(embeddings), document_id, embed_elapsed,
        )

        # --- 4. Upsert to ChromaDB ---
        t1 = time.monotonic()
        chunk_dicts = [
            {
                "id": c.id,
                "chunk_index": c.chunk_index,
                "text": c.text,
                "page_number": c.page_number,
                "section": c.section,
            }
            for c in chunks
        ]
        count = vector_store.upsert_chunks(
            document_id=document_id,
            notebook_id=document.notebook_id,
            source_filename=document.original_filename,
            file_type=document.file_type,
            chunks=chunk_dicts,
            embeddings=embeddings,
        )
        index_elapsed = time.monotonic() - t1

        logger.info(
            "ChromaDB upsert complete for document %d — %d vectors in %.2fs",
            document_id, count, index_elapsed,
        )

    except (OllamaUnavailable, EmbeddingModelNotFound) as exc:
        logger.warning("Indexing failed for document %d: %s", document_id, exc)
        with pool.connection() as conn:
            documents_repo.mark_index_failed(conn, document_id, error_message=str(exc))
        return 0

    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error indexing document %d", document_id)
        with pool.connection() as conn:
            documents_repo.mark_index_failed(
                conn, document_id,
                error_message=f"Unexpected indexing error: {exc}",
            )
        return 0

    # --- 5. Mark indexed ---
    with pool.connection() as conn:
        documents_repo.mark_indexed(conn, document_id)

    return count
