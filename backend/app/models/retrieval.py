from __future__ import annotations
"""
Pydantic models for the semantic retrieval API (Milestone 2).

Kept separate from document/chunk models because the retrieval response
is a projection across multiple tables (chunk + document) with additional
vector-search metadata (distance) that has no place in the raw DB models.
"""

from typing import Optional

from pydantic import BaseModel, Field


class RetrievalRequest(BaseModel):
    """Body for POST /retrieve."""

    query: str = Field(..., min_length=1, description="Natural-language search query.")
    notebook_id: int = Field(..., description="Restrict retrieval to this notebook.")
    # If provided, further restrict to this subset of documents within the notebook.
    # Empty list or omitted → search entire notebook.
    document_ids: list[int] = Field(default_factory=list)
    # How many chunks to return. Clamped server-side to [1, 50].
    top_k: int = Field(default=5, ge=1, le=50)


class RetrievalResult(BaseModel):
    """A single retrieved chunk with full provenance."""

    # ChromaDB vector ID (format: chunk:<document_id>:<chunk_index>)
    vector_id: str
    # PostgreSQL identifiers
    chunk_id: int
    document_id: int
    chunk_index: int
    # Document metadata
    document_name: str
    file_type: str
    # Provenance within the document
    page_number: int | None
    section: str | None
    char_start: int | None
    char_end: int | None
    # The actual text content
    text: str
    # ChromaDB cosine distance (lower = more similar; 0 = identical).
    # NOT called "score" or "similarity" to avoid confusion.
    distance: float


class RetrievalResponse(BaseModel):
    """Response for POST /retrieve."""

    query: str
    notebook_id: int
    document_ids: list[int]  # empty = whole notebook was searched
    top_k: int
    results: list[RetrievalResult]
