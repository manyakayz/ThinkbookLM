from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.models.retrieval import RetrievalRequest, RetrievalResponse
from app.repositories import notebooks as notebooks_repo
from app.services import db
from app.services import retrieval as retrieval_service
from app.services.embedding import EmbeddingModelNotFound, OllamaUnavailable
from app.services.indexing import index_document
from app.services.retrieval import RetrievalError

router = APIRouter(tags=["retrieval"])


@router.post("/retrieve", response_model=RetrievalResponse)
def retrieve(request: RetrievalRequest):
    """Semantic search over indexed document chunks.

    Scope:
    - If document_ids is provided, restrict search to those documents
      (they must belong to the specified notebook).
    - Otherwise search all documents in the notebook.
    """
    pool = db.get_pool()
    with pool.connection() as conn:
        if not notebooks_repo.exists(conn, request.notebook_id):
            raise HTTPException(status_code=404, detail="Notebook not found.")

    try:
        results = retrieval_service.retrieve(
            query=request.query,
            notebook_id=request.notebook_id,
            document_ids=request.document_ids,
            top_k=request.top_k,
        )
    except RetrievalError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except OllamaUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama is not available: {exc}. Start Ollama with `ollama serve`.",
        )
    except EmbeddingModelNotFound as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        )

    return RetrievalResponse(
        query=request.query,
        notebook_id=request.notebook_id,
        document_ids=request.document_ids,
        top_k=request.top_k,
        results=results,
    )


@router.post("/documents/{document_id}/reindex", status_code=200)
def reindex_document(document_id: int):
    """Re-trigger embedding + ChromaDB indexing for a document.

    Useful when a previous indexing attempt failed (e.g. Ollama was offline).
    Requires processing_status='completed' — will not re-run text extraction.
    """
    pool = db.get_pool()
    from app.repositories import documents as documents_repo

    with pool.connection() as conn:
        document = documents_repo.get_by_id(conn, document_id)

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    if document.processing_status != "completed":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot re-index a document with processing_status='{document.processing_status}'. "
                "Only completed documents can be re-indexed."
            ),
        )

    try:
        count = index_document(document_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Re-indexing failed: {exc}")

    with pool.connection() as conn:
        updated = documents_repo.get_by_id(conn, document_id)

    return {
        "document_id": document_id,
        "indexing_status": updated.indexing_status,
        "vectors_indexed": count,
    }
