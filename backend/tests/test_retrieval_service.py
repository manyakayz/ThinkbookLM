"""
Tests for the retrieval service (app/services/retrieval.py).

All external dependencies (DB pool, embedding service, vector store) are
mocked so these tests run without Postgres, Ollama, or ChromaDB.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock, call

from app.models.retrieval import RetrievalResult
from app.services.retrieval import retrieve, RetrievalError
from app.services.embedding import OllamaUnavailable, EmbeddingModelNotFound


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pg_chunk(chunk_id=1, doc_id=1, chunk_index=0, page=1, section="Intro"):
    chunk = MagicMock()
    chunk.id = chunk_id
    chunk.document_id = doc_id
    chunk.chunk_index = chunk_index
    chunk.text = f"Chunk text for chunk_id={chunk_id}"
    chunk.page_number = page
    chunk.section = section
    chunk.char_start = 0
    chunk.char_end = 100
    return chunk


def _make_pg_doc(doc_id=1, notebook_id=1, filename="test.pdf", file_type="pdf"):
    doc = MagicMock()
    doc.id = doc_id
    doc.notebook_id = notebook_id
    doc.original_filename = filename
    doc.file_type = file_type
    return doc


def _chroma_result(vector_ids, chunk_ids, doc_ids, distances):
    """Build a fake ChromaDB query result dict."""
    return {
        "ids": [vector_ids],
        "metadatas": [[{"chunk_id": cid, "document_id": did}
                       for cid, did in zip(chunk_ids, doc_ids)]],
        "distances": [distances],
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_pool():
    """A mock psycopg3 connection pool that yields a usable connection."""
    pool = MagicMock()
    conn = MagicMock()
    pool.connection.return_value.__enter__ = MagicMock(return_value=conn)
    pool.connection.return_value.__exit__ = MagicMock(return_value=False)
    return pool, conn


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def test_empty_query_raises_retrieval_error(mock_pool):
    pool, conn = mock_pool
    with patch("app.services.retrieval.db") as mock_db:
        mock_db.get_pool.return_value = pool

        with pytest.raises(RetrievalError, match="empty"):
            retrieve(query="   ", notebook_id=1, document_ids=[], top_k=5)


def test_whitespace_only_query_raises_retrieval_error(mock_pool):
    pool, conn = mock_pool
    with patch("app.services.retrieval.db") as mock_db:
        mock_db.get_pool.return_value = pool

        with pytest.raises(RetrievalError):
            retrieve(query="\t\n ", notebook_id=1, document_ids=[], top_k=5)


def test_documents_outside_notebook_raises_retrieval_error(mock_pool):
    """document_ids that don't belong to the notebook must raise RetrievalError."""
    pool, conn = mock_pool
    with patch("app.services.retrieval.db") as mock_db, \
         patch("app.services.retrieval.documents_repo") as mock_docs_repo:
        mock_db.get_pool.return_value = pool
        # Notebook only contains doc 1; caller requests doc 99
        mock_docs_repo.list_ids_for_notebook.return_value = [1]

        with pytest.raises(RetrievalError, match="do not belong"):
            retrieve(query="test query", notebook_id=1, document_ids=[99], top_k=5)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_retrieve_returns_results_with_provenance(mock_pool):
    """A successful retrieval must return RetrievalResult objects with full provenance."""
    pool, conn = mock_pool

    pg_chunk = _make_pg_chunk(chunk_id=42, doc_id=7, chunk_index=3, page=2, section="Methods")
    pg_doc = _make_pg_doc(doc_id=7, filename="paper.pdf", file_type="pdf")

    chroma_raw = _chroma_result(
        vector_ids=["chunk:7:3"],
        chunk_ids=[42],
        doc_ids=[7],
        distances=[0.1234],
    )

    with patch("app.services.retrieval.db") as mock_db, \
         patch("app.services.retrieval.documents_repo") as mock_docs_repo, \
         patch("app.services.retrieval.chunks_repo") as mock_chunks_repo, \
         patch("app.services.retrieval.embedding") as mock_emb, \
         patch("app.services.retrieval.vector_store") as mock_vs:

        mock_db.get_pool.return_value = pool
        mock_docs_repo.list_ids_for_notebook.return_value = [7]
        mock_docs_repo.get_by_id.return_value = pg_doc
        mock_chunks_repo.get_by_ids.return_value = [pg_chunk]
        mock_emb.embed_query.return_value = [0.1] * 8
        mock_vs.query.return_value = chroma_raw

        results = retrieve(
            query="What is the methodology?",
            notebook_id=1,
            document_ids=[7],
            top_k=5,
        )

    assert len(results) == 1
    r = results[0]
    assert isinstance(r, RetrievalResult)
    assert r.vector_id == "chunk:7:3"
    assert r.chunk_id == 42
    assert r.document_id == 7
    assert r.chunk_index == 3
    assert r.document_name == "paper.pdf"
    assert r.file_type == "pdf"
    assert r.page_number == 2
    assert r.section == "Methods"
    assert r.distance == round(0.1234, 6)
    assert "chunk_id=42" in r.text  # from our fake chunk text


def test_no_results_returns_empty_list(mock_pool):
    """When ChromaDB returns nothing, retrieve must return an empty list (not raise)."""
    pool, conn = mock_pool
    chroma_raw = {"ids": [[]], "metadatas": [[]], "distances": [[]]}

    with patch("app.services.retrieval.db") as mock_db, \
         patch("app.services.retrieval.documents_repo") as mock_docs_repo, \
         patch("app.services.retrieval.embedding") as mock_emb, \
         patch("app.services.retrieval.vector_store") as mock_vs:

        mock_db.get_pool.return_value = pool
        mock_docs_repo.list_ids_for_notebook.return_value = []
        mock_emb.embed_query.return_value = [0.0] * 8
        mock_vs.query.return_value = chroma_raw

        results = retrieve(query="anything", notebook_id=1, document_ids=[], top_k=5)

    assert results == []


def test_stale_vector_is_skipped(mock_pool):
    """A ChromaDB result whose PG chunk is missing must be silently skipped."""
    pool, conn = mock_pool

    # ChromaDB says chunk_id=999 exists, but PG has no such chunk
    chroma_raw = _chroma_result(
        vector_ids=["chunk:1:0"], chunk_ids=[999], doc_ids=[1], distances=[0.05],
    )

    with patch("app.services.retrieval.db") as mock_db, \
         patch("app.services.retrieval.documents_repo") as mock_docs_repo, \
         patch("app.services.retrieval.chunks_repo") as mock_chunks_repo, \
         patch("app.services.retrieval.embedding") as mock_emb, \
         patch("app.services.retrieval.vector_store") as mock_vs:

        mock_db.get_pool.return_value = pool
        mock_docs_repo.list_ids_for_notebook.return_value = [1]
        mock_docs_repo.get_by_id.return_value = _make_pg_doc()
        mock_chunks_repo.get_by_ids.return_value = []  # PG chunk not found
        mock_emb.embed_query.return_value = [0.0] * 8
        mock_vs.query.return_value = chroma_raw

        results = retrieve(query="something", notebook_id=1, document_ids=[1], top_k=5)

    assert results == []


# ---------------------------------------------------------------------------
# Ollama / embedding failures bubble up
# ---------------------------------------------------------------------------

def test_ollama_unavailable_propagates(mock_pool):
    pool, conn = mock_pool
    with patch("app.services.retrieval.db") as mock_db, \
         patch("app.services.retrieval.documents_repo") as mock_docs_repo, \
         patch("app.services.retrieval.embedding") as mock_emb:

        mock_db.get_pool.return_value = pool
        mock_docs_repo.list_ids_for_notebook.return_value = []
        mock_emb.embed_query.side_effect = OllamaUnavailable("server down")

        with pytest.raises(OllamaUnavailable):
            retrieve(query="test", notebook_id=1, document_ids=[], top_k=5)


def test_embedding_model_not_found_propagates(mock_pool):
    pool, conn = mock_pool
    with patch("app.services.retrieval.db") as mock_db, \
         patch("app.services.retrieval.documents_repo") as mock_docs_repo, \
         patch("app.services.retrieval.embedding") as mock_emb:

        mock_db.get_pool.return_value = pool
        mock_docs_repo.list_ids_for_notebook.return_value = []
        mock_emb.embed_query.side_effect = EmbeddingModelNotFound("model missing")

        with pytest.raises(EmbeddingModelNotFound):
            retrieve(query="test", notebook_id=1, document_ids=[], top_k=5)


# ---------------------------------------------------------------------------
# Scope isolation
# ---------------------------------------------------------------------------

def test_whole_notebook_scope_uses_notebook_filter(mock_pool):
    """With document_ids=[], vector_store.query must be called with notebook_id scope."""
    pool, conn = mock_pool
    chroma_raw = {"ids": [[]], "metadatas": [[]], "distances": [[]]}

    with patch("app.services.retrieval.db") as mock_db, \
         patch("app.services.retrieval.documents_repo") as mock_docs_repo, \
         patch("app.services.retrieval.embedding") as mock_emb, \
         patch("app.services.retrieval.vector_store") as mock_vs:

        mock_db.get_pool.return_value = pool
        mock_docs_repo.list_ids_for_notebook.return_value = []
        mock_emb.embed_query.return_value = [0.0] * 8
        mock_vs.query.return_value = chroma_raw

        retrieve(query="scope test", notebook_id=42, document_ids=[], top_k=5)

        call_kwargs = mock_vs.query.call_args.kwargs
        assert call_kwargs["notebook_id"] == 42
        assert call_kwargs["document_ids"] == []


def test_document_scope_passes_ids_to_vector_store(mock_pool):
    """With document_ids=[1,2], vector_store.query must receive those exact IDs."""
    pool, conn = mock_pool
    chroma_raw = {"ids": [[]], "metadatas": [[]], "distances": [[]]}

    with patch("app.services.retrieval.db") as mock_db, \
         patch("app.services.retrieval.documents_repo") as mock_docs_repo, \
         patch("app.services.retrieval.embedding") as mock_emb, \
         patch("app.services.retrieval.vector_store") as mock_vs:

        mock_db.get_pool.return_value = pool
        mock_docs_repo.list_ids_for_notebook.return_value = [1, 2, 3]
        mock_emb.embed_query.return_value = [0.0] * 8
        mock_vs.query.return_value = chroma_raw

        retrieve(query="scoped", notebook_id=1, document_ids=[1, 2], top_k=3)

        call_kwargs = mock_vs.query.call_args.kwargs
        assert set(call_kwargs["document_ids"]) == {1, 2}
        assert call_kwargs["top_k"] == 3


# ---------------------------------------------------------------------------
# Indexing failure state
# ---------------------------------------------------------------------------

def test_indexing_failure_state_is_separate_from_processing():
    """Document model must have distinct processing_status and indexing_status fields."""
    from app.models.document import Document
    from datetime import datetime
    doc = Document(
        id=1,
        notebook_id=1,
        original_filename="test.pdf",
        file_type="pdf",
        file_size=1024,
        page_count=None,
        processing_status="completed",
        error_message=None,
        indexing_status="failed",
        indexing_error="Ollama unavailable",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    # A doc can be "completed" (text extracted) but "failed" (not indexed)
    assert doc.processing_status == "completed"
    assert doc.indexing_status == "failed"
    assert doc.indexing_error == "Ollama unavailable"
