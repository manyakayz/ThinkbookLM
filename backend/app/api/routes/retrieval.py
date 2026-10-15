from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, verify_csrf
from app.models.retrieval import RetrievalRequest, RetrievalResponse
from app.models.user import User
from app.repositories import documents as documents_repo
from app.repositories import notebooks as notebooks_repo
from app.services import db
from app.services import retrieval as retrieval_service
from app.services.embedding import EmbeddingModelNotFound, OllamaUnavailable
from app.services.indexing import index_document
from app.services.retrieval import RetrievalError

router = APIRouter(tags=["retrieval"])


@router.post("/retrieve", response_model=RetrievalResponse, dependencies=[Depends(verify_csrf)])
def retrieve(request: RetrievalRequest, current_user: User = Depends(get_current_user)):
    """Semantic search over indexed document chunks, isolated to the authenticated user."""
    pool = db.get_pool()
    with pool.connection() as conn:
        if not notebooks_repo.exists(conn, request.notebook_id, user_id=current_user.id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found.")

    try:
        results = retrieval_service.retrieve(
            query=request.query,
            notebook_id=request.notebook_id,
            document_ids=request.document_ids,
            top_k=request.top_k,
            user_id=current_user.id,
        )
    except RetrievalError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except OllamaUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Ollama is not available: {exc}. Start Ollama with `ollama serve`.",
        )
    except EmbeddingModelNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

    return RetrievalResponse(
        query=request.query,
        notebook_id=request.notebook_id,
        document_ids=request.document_ids,
        top_k=request.top_k,
        results=results,
    )


@router.post("/documents/{document_id}/reindex", status_code=status.HTTP_200_OK, dependencies=[Depends(verify_csrf)])
def reindex_document(document_id: int, current_user: User = Depends(get_current_user)):
    """Re-trigger embedding + ChromaDB indexing for a document owned by the current user."""
    pool = db.get_pool()

    with pool.connection() as conn:
        document = documents_repo.get_by_id(conn, document_id, user_id=current_user.id)

    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    if document.processing_status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot re-index a document with processing_status='{document.processing_status}'. "
                "Only completed documents can be re-indexed."
            ),
        )

    try:
        count = index_document(document_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Re-indexing failed: {exc}")

    with pool.connection() as conn:
        updated = documents_repo.get_by_id(conn, document_id, user_id=current_user.id)

    return {
        "document_id": document_id,
        "indexing_status": updated.indexing_status if updated else "unknown",
        "vectors_indexed": count,
    }
