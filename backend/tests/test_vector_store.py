"""
Tests for the vector store service (app/services/vector_store.py).

All tests use an isolated temporary ChromaDB directory so they never
touch the real ./data/chroma directory.

These tests do NOT require Ollama — embeddings are tiny fake float vectors.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch
from tests.conftest import make_fake_embedding, make_fake_embeddings, FAKE_DIM

import chromadb

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chunk_dict(chunk_index: int, doc_id: int = 1, pg_id: int = None) -> dict:
    return {
        "id": pg_id if pg_id is not None else chunk_index + 100,
        "chunk_index": chunk_index,
        "text": f"Chunk text number {chunk_index}",
        "page_number": chunk_index + 1,
        "section": f"Section {chunk_index}",
    }


@pytest.fixture(autouse=True)
def isolated_chroma(monkeypatch):
    """Ensure every test gets a fresh, ephemeral ChromaDB client."""
    import app.services.vector_store as vs
    # Use EphemeralClient instead of PersistentClient for testing
    client = chromadb.EphemeralClient()
    monkeypatch.setattr("chromadb.PersistentClient", lambda path=None: client)
    # Clear the cached client
    vs._client = None
    yield
    try:
        client.delete_collection("thinkbook_chunks")
    except Exception:
        pass
    vs._client = None


# ---------------------------------------------------------------------------
# Vector ID format
# ---------------------------------------------------------------------------

def test_make_vector_id_format():
    """Vector IDs must be deterministic strings in the expected format."""
    from app.services.vector_store import make_vector_id
    vid = make_vector_id(document_id=42, chunk_index=7)
    assert vid == "chunk:42:7"


def test_make_vector_id_is_deterministic():
    """Calling make_vector_id twice with the same args must return the same string."""
    from app.services.vector_store import make_vector_id
    assert make_vector_id(1, 0) == make_vector_id(1, 0)


def test_make_vector_id_different_docs_differ():
    """Two different documents must produce different IDs for the same chunk_index."""
    from app.services.vector_store import make_vector_id
    assert make_vector_id(1, 0) != make_vector_id(2, 0)


def test_make_vector_id_different_chunks_differ():
    """Two different chunk indices in the same doc must produce different IDs."""
    from app.services.vector_store import make_vector_id
    assert make_vector_id(1, 0) != make_vector_id(1, 1)


# ---------------------------------------------------------------------------
# Upsert + retrieval
# ---------------------------------------------------------------------------

def test_upsert_chunks_returns_count():
    """upsert_chunks must return the number of vectors inserted."""
    import app.services.vector_store as vs
    chunks = [_make_chunk_dict(i) for i in range(3)]
    embeddings = make_fake_embeddings(3)

    count = vs.upsert_chunks(
        document_id=1,
        notebook_id=10,
        source_filename="test.pdf",
        file_type="pdf",
        chunks=chunks,
        embeddings=embeddings,
    )

    assert count == 3


def test_upsert_empty_chunks_returns_zero():
    """upsert_chunks with an empty list must return 0 without touching ChromaDB."""
    import app.services.vector_store as vs
    count = vs.upsert_chunks(
        document_id=1, notebook_id=10,
        source_filename="x.txt", file_type="txt",
        chunks=[], embeddings=[],
    )
    assert count == 0


def test_upsert_is_idempotent():
    """Upserting the same chunks twice must NOT create duplicates."""
    import app.services.vector_store as vs
    chunks = [_make_chunk_dict(i) for i in range(4)]
    embeddings = make_fake_embeddings(4)

    kwargs = dict(
        document_id=2, notebook_id=10,
        source_filename="dup.pdf", file_type="pdf",
        chunks=chunks, embeddings=embeddings,
    )

    vs.upsert_chunks(**kwargs)
    vs.upsert_chunks(**kwargs)  # second call — should be a no-op in count terms

    col = vs.get_collection()
    # ChromaDB upsert: same IDs → overwrite, not duplicate
    assert col.count() == 4


def test_delete_document_removes_vectors():
    """delete_document must remove all vectors for a given document_id."""
    import app.services.vector_store as vs
    chunks = [_make_chunk_dict(i) for i in range(3)]
    embeddings = make_fake_embeddings(3)

    vs.upsert_chunks(
        document_id=5, notebook_id=10,
        source_filename="del.txt", file_type="txt",
        chunks=chunks, embeddings=embeddings,
    )
    vs.delete_document(5)
    assert vs.get_collection().count() == 0


def test_reindex_without_duplicates():
    """Re-indexing a document (delete + upsert) must not leave duplicates."""
    import app.services.vector_store as vs
    chunks = [_make_chunk_dict(i) for i in range(3)]
    embeddings = make_fake_embeddings(3)

    # First index
    vs.upsert_chunks(
        document_id=6, notebook_id=10,
        source_filename="re.pdf", file_type="pdf",
        chunks=chunks, embeddings=embeddings,
    )
    # Simulate re-index: delete then upsert
    vs.delete_document(6)
    vs.upsert_chunks(
        document_id=6, notebook_id=10,
        source_filename="re.pdf", file_type="pdf",
        chunks=chunks, embeddings=embeddings,
    )

    assert vs.get_collection().count() == 3


# ---------------------------------------------------------------------------
# Scope filtering
# ---------------------------------------------------------------------------

def _seed_two_notebooks(vs, nb1_docs, nb2_docs):
    """Utility: insert chunks for two notebooks with disjoint document IDs."""
    # Notebook 1 — documents 1..nb1_docs
    for doc_id in range(1, nb1_docs + 1):
        chunks = [_make_chunk_dict(i, doc_id=doc_id, pg_id=doc_id * 100 + i) for i in range(2)]
        vs.upsert_chunks(
            document_id=doc_id, notebook_id=1,
            source_filename=f"nb1_doc{doc_id}.txt", file_type="txt",
            chunks=chunks, embeddings=make_fake_embeddings(2),
        )
    # Notebook 2 — documents 10..10+nb2_docs
    for doc_id in range(10, 10 + nb2_docs):
        chunks = [_make_chunk_dict(i, doc_id=doc_id, pg_id=doc_id * 100 + i) for i in range(2)]
        vs.upsert_chunks(
            document_id=doc_id, notebook_id=2,
            source_filename=f"nb2_doc{doc_id}.txt", file_type="txt",
            chunks=chunks, embeddings=make_fake_embeddings(2),
        )


def test_notebook_scope_does_not_bleed():
    """Querying notebook 1 must never return vectors from notebook 2."""
    import app.services.vector_store as vs
    _seed_two_notebooks(vs, nb1_docs=2, nb2_docs=2)

    query_vec = make_fake_embedding(0)
    results = vs.query(
        embedding=query_vec,
        notebook_id=1,
        document_ids=[],
        top_k=10,
    )
    metadatas = results["metadatas"][0]
    for meta in metadatas:
        assert meta["notebook_id"] == 1, f"Got result from notebook {meta['notebook_id']}"


def test_single_document_scope():
    """Querying with document_ids=[doc_id] must return only that document's chunks."""
    import app.services.vector_store as vs
    _seed_two_notebooks(vs, nb1_docs=3, nb2_docs=1)

    query_vec = make_fake_embedding(0)
    results = vs.query(
        embedding=query_vec,
        notebook_id=1,
        document_ids=[2],  # only document 2
        top_k=10,
    )
    metadatas = results["metadatas"][0]
    for meta in metadatas:
        assert meta["document_id"] == 2


def test_selected_documents_scope():
    """Querying with document_ids=[1,3] must not include document 2's chunks."""
    import app.services.vector_store as vs
    _seed_two_notebooks(vs, nb1_docs=3, nb2_docs=1)

    query_vec = make_fake_embedding(0)
    results = vs.query(
        embedding=query_vec,
        notebook_id=1,
        document_ids=[1, 3],
        top_k=10,
    )
    metadatas = results["metadatas"][0]
    returned_doc_ids = {m["document_id"] for m in metadatas}
    assert 2 not in returned_doc_ids, "document 2 should not appear in result"
    assert returned_doc_ids.issubset({1, 3})


def test_top_k_limits_results():
    """top_k must cap the number of returned results."""
    import app.services.vector_store as vs

    # Insert 10 chunks for one document
    chunks = [_make_chunk_dict(i) for i in range(10)]
    vs.upsert_chunks(
        document_id=99, notebook_id=5,
        source_filename="many.pdf", file_type="pdf",
        chunks=chunks, embeddings=make_fake_embeddings(10),
    )

    query_vec = make_fake_embedding(0)
    results = vs.query(
        embedding=query_vec,
        notebook_id=5,
        document_ids=[],
        top_k=3,
    )
    assert len(results["ids"][0]) <= 3


def test_empty_collection_returns_empty():
    """Querying an empty collection must return empty lists, not raise."""
    import app.services.vector_store as vs

    results = vs.query(
        embedding=make_fake_embedding(0),
        notebook_id=1,
        document_ids=[],
        top_k=5,
    )
    assert results["ids"] == [[]]
    assert results["metadatas"] == [[]]
    assert results["distances"] == [[]]


# ---------------------------------------------------------------------------
# Metadata preservation
# ---------------------------------------------------------------------------

def test_provenance_metadata_stored():
    """All required provenance fields must survive the upsert→query round trip."""
    import app.services.vector_store as vs

    chunk = {
        "id": 777,
        "chunk_index": 0,
        "text": "Provenance test chunk.",
        "page_number": 3,
        "section": "Introduction",
    }
    vs.upsert_chunks(
        document_id=7, notebook_id=99,
        source_filename="prov.pdf", file_type="pdf",
        chunks=[chunk], embeddings=[make_fake_embedding(0)],
    )

    results = vs.query(
        embedding=make_fake_embedding(0),
        notebook_id=99,
        document_ids=[],
        top_k=1,
    )
    meta = results["metadatas"][0][0]
    assert meta["document_id"] == 7
    assert meta["chunk_id"] == 777
    assert meta["notebook_id"] == 99
    assert meta["chunk_index"] == 0
    assert meta["source_filename"] == "prov.pdf"
    assert meta["file_type"] == "pdf"
    assert meta["page_number"] == 3
    assert meta["section"] == "Introduction"


def test_none_page_number_stored_as_sentinel():
    """page_number=None must be stored as -1 (ChromaDB requires primitive values)."""
    import app.services.vector_store as vs

    chunk = {"id": 1, "chunk_index": 0, "text": "no page", "page_number": None, "section": None}
    vs.upsert_chunks(
        document_id=8, notebook_id=1,
        source_filename="nopg.txt", file_type="txt",
        chunks=[chunk], embeddings=[make_fake_embedding(0)],
    )
    results = vs.query(
        embedding=make_fake_embedding(0),
        notebook_id=1, document_ids=[], top_k=1,
    )
    meta = results["metadatas"][0][0]
    assert meta["page_number"] == -1
    assert meta["section"] == ""


# ---------------------------------------------------------------------------
# ping()
# ---------------------------------------------------------------------------

def test_ping_returns_true_when_healthy():
    import app.services.vector_store as vs
    ok, err = vs.ping()
    assert ok is True
    assert err is None
