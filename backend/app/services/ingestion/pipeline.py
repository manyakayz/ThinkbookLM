from __future__ import annotations
"""
Orchestrates one document's journey from `pending` to `completed`/`failed`,
then immediately triggers embedding and ChromaDB indexing (Milestone 2).

Deliberately synchronous for this milestone. Kept as a plain function taking
only a `document_id` so it can be called from a background worker later
without changes.

Transaction shape (unchanged from Milestone 1):
  Extraction and chunking happen outside any DB transaction.
  Chunks + completed status are written atomically together.
  If that write fails, the document stays in `processing` — retryable.

Indexing (Milestone 2 addition):
  Runs after the atomic chunk/status write. A failure here sets
  indexing_status = 'failed' but leaves processing_status = 'completed'.
  The chunks are in PostgreSQL; only the vectors are missing. The re-index
  endpoint can retry without re-running extraction.
"""


import logging

from app.config import get_settings
from app.models.document import Document
from app.repositories import chunks as chunks_repo
from app.repositories import documents as documents_repo
from app.services import db, storage
from app.services import indexing as indexing_service
from app.services.ingestion import chunker
from app.services.ingestion.extractors import registry
from app.services.ingestion.types import ExtractionError

logger = logging.getLogger(__name__)


class DocumentNotFound(Exception):
    pass


def process_document(document_id: int) -> tuple[Document, int]:
    """Run extraction + chunking + persistence + indexing for one document.

    Returns (updated_document, chunk_count). Never raises for ordinary
    extraction or indexing failures — those result in a status update instead.
    """
    settings = get_settings()
    pool = db.get_pool()

    with pool.connection() as conn:
        document = documents_repo.get_by_id(conn, document_id)
        if document is None:
            raise DocumentNotFound(f"Document {document_id} not found.")
        stored_filename = documents_repo.get_stored_filename(conn, document_id)

    with pool.connection() as conn:
        documents_repo.mark_processing(conn, document_id)

    file_path = storage.path_for(stored_filename)

    try:
        extracted = registry.extract(document.file_type, file_path, document.original_filename)
        chunk_records = chunker.chunk_document(
            extracted,
            chunk_size=settings.chunk_size_chars,
            overlap=settings.chunk_overlap_chars,
        )
        if not chunk_records:
            raise ExtractionError(f"'{document.original_filename}' produced no usable text chunks.")

    except ExtractionError as exc:
        logger.info("Document %s failed processing: %s", document_id, exc)
        with pool.connection() as conn:
            updated = documents_repo.mark_failed(conn, document_id, error_message=str(exc))
        return updated, 0

    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error processing document %s", document_id)
        with pool.connection() as conn:
            updated = documents_repo.mark_failed(conn, document_id, error_message=f"Unexpected error: {exc}")
        return updated, 0

    # Chunks + completed status written atomically
    with pool.connection() as conn:
        chunks_repo.insert_many(conn, document_id, [c.as_dict() for c in chunk_records])
        updated = documents_repo.mark_completed(conn, document_id, page_count=extracted.page_count)

    chunk_count = len(chunk_records)
    logger.info("Document %d extraction complete — %d chunks", document_id, chunk_count)

    # --- Milestone 2: Embed + index into ChromaDB ---
    # Run after the atomic PG write so chunks are guaranteed to exist.
    # index_document handles its own errors and updates indexing_status.
    indexing_service.index_document(document_id)

    # Re-fetch so the returned document has the latest indexing_status
    with pool.connection() as conn:
        updated = documents_repo.get_by_id(conn, document_id)

    return updated, chunk_count


