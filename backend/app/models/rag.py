from __future__ import annotations
"""
Pydantic models for the RAG (Retrieval-Augmented Generation) chat endpoint.

Kept separate from the generic /chat models so the two APIs can evolve
independently. The /chat/rag endpoint is notebook-scoped and always returns
grounded source references alongside the answer.
"""

from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class RAGMessage(BaseModel):
    """A single turn in a conversation passed as history context."""

    role: str = Field(..., description="'user' or 'assistant'.")
    content: str = Field(..., min_length=1, description="Text of the turn.")


class RAGRequest(BaseModel):
    """Body for POST /chat/rag."""

    # The current user question.
    message: str = Field(..., min_length=1, max_length=4000, description="User's question.")

    # Scope: which notebook (required) and optionally a subset of documents.
    notebook_id: int = Field(..., description="Restrict retrieval to this notebook.")
    document_ids: list[int] = Field(
        default_factory=list,
        description="Further restrict to these documents. Empty = whole notebook.",
    )

    # Optional conversation history. Only the last N turns are used; older
    # context is silently dropped to protect the model's context window.
    # Each dict has "role" and "content" keys.
    history: list[RAGMessage] = Field(
        default_factory=list,
        description="Previous turns in this conversation (oldest first).",
    )

    # Retrieval tuning.
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of chunks to retrieve. Clamped server-side.",
    )

    # Generation tuning.
    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Sampling temperature. Lower = more factual.",
    )

    # Optional relevance threshold override (cosine distance; 0=identical, 1=orthogonal).
    relevance_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Maximum cosine distance for chunks to be considered relevant evidence.",
    )


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

class SourceReference(BaseModel):
    """A verified reference to one retrieved chunk used in the answer.

    All fields come directly from PostgreSQL metadata — the model never
    invents or infers these values.
    """

    chunk_id: int = Field(..., description="PostgreSQL chunk ID.")
    document_id: int = Field(..., description="PostgreSQL document ID.")
    document_name: str = Field(..., description="Original filename of the source document.")
    chunk_index: int = Field(..., description="Zero-based position of this chunk in the document.")
    page_number: Optional[int] = Field(None, description="Page number if available (PDF only).")
    section: Optional[str] = Field(None, description="Section heading if available (DOCX only).")
    distance: float = Field(..., description="Cosine distance (lower = more similar).")


class RAGResponse(BaseModel):
    """Response from POST /chat/rag."""

    answer: str = Field(..., description="The model's answer grounded in retrieved content.")
    sources: list[SourceReference] = Field(
        ...,
        description=(
            "Verified source chunks that were supplied to the model. "
            "Only chunks actually passed in the prompt are included."
        ),
    )
    # Indicates whether the answer could be grounded in retrieved documents.
    grounded: bool = Field(
        ...,
        description=(
            "True if at least one relevant chunk was found and used. "
            "False if the model answered from general knowledge due to empty retrieval."
        ),
    )
    # Retrieval diagnostics.
    retrieved_count: int = Field(..., description="Number of chunks retrieved from ChromaDB.")
    notebook_id: int
    model: str = Field(..., description="Ollama model that generated the answer.")
