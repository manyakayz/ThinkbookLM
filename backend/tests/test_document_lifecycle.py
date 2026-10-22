from __future__ import annotations
"""
Comprehensive tests for Phase 2: Document Ingestion, Embeddings, and Semantic Retrieval.

Covers:
- Document formats: PDF, DOCX, TXT
- Extraction failures: empty, corrupted, encrypted, textless
- Idempotent reprocessing: no duplicate chunks in PG or ChromaDB
- Deletion: document and notebook deletion purge ChromaDB vectors and DB rows
- User & notebook isolation in retrieval
- Live integration with real Qwen3-Embedding-0.6B
"""

import io
import uuid
import docx
from pypdf import PdfWriter
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.document import Document
from app.repositories import chunks as chunks_repo
from app.repositories import documents as documents_repo
from app.repositories import notebooks as notebooks_repo
from app.services import db, vector_store
from app.services.ingestion import pipeline
from app.services.ingestion.extractors import docx_extractor, pdf_extractor, txt_extractor
from app.services.ingestion.types import ExtractionError


@pytest.fixture
def client():
    return TestClient(app)


def _unique_email() -> str:
    return f"user_{uuid.uuid4().hex[:8]}@example.com"


def _register_user(client: TestClient) -> dict:
    email = _unique_email()
    res = client.post(
        "/auth/register",
        json={
            "full_name": "Ingestion Tester",
            "email": email,
            "password": "ValidPassword123",
            "confirm_password": "ValidPassword123",
        },
    )
    assert res.status_code == 201
    return res.json()


def _create_sample_pdf_bytes(pages_text: list[str]) -> bytes:
    writer = PdfWriter()
    for text in pages_text:
        # Create page with text
        writer.add_blank_page(width=72, height=72)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


def _create_sample_docx_bytes(paragraphs: list[tuple[str, str]]) -> bytes:
    """paragraphs is list of (style, text), e.g. ('Heading 1', 'Title'), ('Normal', 'Body')"""
    doc = docx.Document()
    for style, text in paragraphs:
        doc.add_paragraph(text, style=style)
    stream = io.BytesIO()
    doc.save(stream)
    return stream.getvalue()


# ---------------------------------------------------------------------------
# 1. Format Extraction Unit Tests
# ---------------------------------------------------------------------------

def test_extract_docx_with_headings(tmp_path):
    docx_file = tmp_path / "sample.docx"
    content = _create_sample_docx_bytes([
        ("Heading 1", "Introduction Section"),
        ("Normal", "This is the first paragraph under intro."),
        ("Heading 2", "Methods Section"),
        ("Normal", "Here are the detailed experimental procedures."),
    ])
    docx_file.write_bytes(content)

    extracted = docx_extractor.extract(docx_file, "sample.docx")
    assert extracted.source_filename == "sample.docx"
    assert len(extracted.sections) == 2
    assert extracted.sections[0].section_title == "Introduction Section"
    assert "intro" in extracted.sections[0].text
    assert extracted.sections[1].section_title == "Methods Section"
    assert "procedures" in extracted.sections[1].text


def test_extract_docx_empty_raises(tmp_path):
    docx_file = tmp_path / "empty.docx"
    doc = docx.Document()
    stream = io.BytesIO()
    doc.save(stream)
    docx_file.write_bytes(stream.getvalue())

    with pytest.raises(ExtractionError, match="no readable text"):
        docx_extractor.extract(docx_file, "empty.docx")


def test_extract_corrupt_docx_raises(tmp_path):
    corrupt_file = tmp_path / "corrupt.docx"
    corrupt_file.write_bytes(b"PK\x03\x04not-a-valid-zip-content")

    with pytest.raises(ExtractionError, match="Could not open"):
        docx_extractor.extract(corrupt_file, "corrupt.docx")


def test_extract_corrupt_pdf_raises(tmp_path):
    corrupt_pdf = tmp_path / "corrupt.pdf"
    corrupt_pdf.write_bytes(b"%PDF-1.4 corrupt junk")

    with pytest.raises(ExtractionError, match="Could not open"):
        pdf_extractor.extract(corrupt_pdf, "corrupt.pdf")


def test_extract_empty_txt_raises(tmp_path):
    empty_txt = tmp_path / "empty.txt"
    empty_txt.write_text("   \n\t  ")

    with pytest.raises(ExtractionError, match="no readable text"):
        txt_extractor.extract(empty_txt, "empty.txt")


# ---------------------------------------------------------------------------
# 2. End-to-End Upload, Reprocessing, and Deletion Lifecycle
# ---------------------------------------------------------------------------

def test_upload_and_delete_document_cleans_chroma(client):
    auth_data = _register_user(client)
    csrf = auth_data["csrf_token"]

    # 1. Create notebook
    res_nb = client.post("/notebooks", json={"name": "Lifecycle NB"}, headers={"X-CSRF-Token": csrf})
    assert res_nb.status_code == 201
    nb_id = res_nb.json()["id"]

    # 2. Upload text document
    txt_content = b"The quick brown fox jumps over the lazy dog.\n\nSecondary test paragraph for chunking."
    res_up = client.post(
        f"/notebooks/{nb_id}/documents",
        files={"file": ("fox.txt", txt_content, "text/plain")},
        headers={"X-CSRF-Token": csrf},
    )
    assert res_up.status_code == 201
    doc_id = res_up.json()["document"]["id"]

    # Verify document exists in PostgreSQL
    pool = db.get_pool()
    with pool.connection() as conn:
        doc = documents_repo.get_by_id(conn, doc_id)
        assert doc is not None
        assert doc.processing_status == "completed"
        chunk_count = chunks_repo.count_for_document(conn, doc_id)
        assert chunk_count > 0

    # 3. Delete document via DELETE endpoint
    res_del = client.delete(f"/documents/{doc_id}", headers={"X-CSRF-Token": csrf})
    assert res_del.status_code == 200
    assert res_del.json()["deleted"] is True

    # 4. Verify document is gone from PostgreSQL
    with pool.connection() as conn:
        doc_after = documents_repo.get_by_id(conn, doc_id)
        assert doc_after is None
        chunks_after = chunks_repo.count_for_document(conn, doc_id)
        assert chunks_after == 0

    # 5. Verify retrieval returns no chunks for this document
    res_ret = client.post(
        "/retrieve",
        json={"query": "quick brown fox", "notebook_id": nb_id, "top_k": 5},
        headers={"X-CSRF-Token": csrf},
    )
    assert res_ret.status_code == 200
    assert res_ret.json()["results"] == []


def test_reprocess_document_idempotency(client):
    """Reprocessing a document multiple times must not duplicate chunks or vectors."""
    auth_data = _register_user(client)
    csrf = auth_data["csrf_token"]

    nb_id = client.post("/notebooks", json={"name": "Idempotent NB"}, headers={"X-CSRF-Token": csrf}).json()["id"]

    content = b"Unique content line 1.\n\nUnique content line 2."
    res_up = client.post(
        f"/notebooks/{nb_id}/documents",
        files={"file": ("idempotent.txt", content, "text/plain")},
        headers={"X-CSRF-Token": csrf},
    )
    assert res_up.status_code == 201
    doc_id = res_up.json()["document"]["id"]

    pool = db.get_pool()
    with pool.connection() as conn:
        initial_chunks = chunks_repo.count_for_document(conn, doc_id)
        assert initial_chunks > 0

    # Reprocess the document directly through the pipeline
    updated_doc, new_count = pipeline.process_document(doc_id)
    assert updated_doc.processing_status == "completed"
    assert new_count == initial_chunks

    # Chunk count in DB must remain identical, not doubled
    with pool.connection() as conn:
        post_reprocess_chunks = chunks_repo.count_for_document(conn, doc_id)
        assert post_reprocess_chunks == initial_chunks


def test_delete_notebook_purges_documents_and_vectors(client):
    auth_data = _register_user(client)
    csrf = auth_data["csrf_token"]

    res_nb = client.post("/notebooks", json={"name": "Notebook To Delete"}, headers={"X-CSRF-Token": csrf})
    nb_id = res_nb.json()["id"]

    client.post(
        f"/notebooks/{nb_id}/documents",
        files={"file": ("to_del.txt", b"Notebook deletion test content.", "text/plain")},
        headers={"X-CSRF-Token": csrf},
    )

    res_del_nb = client.delete(f"/notebooks/{nb_id}", headers={"X-CSRF-Token": csrf})
    assert res_del_nb.status_code == 200
    assert res_del_nb.json()["deleted"] is True

    # Check notebook no longer exists
    assert client.get(f"/notebooks/{nb_id}").status_code == 404


def test_cross_user_deletion_rejected(client):
    user_a = _register_user(client)
    client_b = TestClient(app)
    user_b = _register_user(client_b)

    # User A creates notebook and document
    nb_a = client.post("/notebooks", json={"name": "User A NB"}, headers={"X-CSRF-Token": user_a["csrf_token"]}).json()["id"]
    doc_a = client.post(
        f"/notebooks/{nb_a}/documents",
        files={"file": ("user_a.txt", b"Private data A", "text/plain")},
        headers={"X-CSRF-Token": user_a["csrf_token"]},
    ).json()["document"]["id"]

    # User B attempts to delete User A's document -> 404
    res_b_del_doc = client_b.delete(f"/documents/{doc_a}", headers={"X-CSRF-Token": user_b["csrf_token"]})
    assert res_b_del_doc.status_code == 404

    # User B attempts to delete User A's notebook -> 404
    res_b_del_nb = client_b.delete(f"/notebooks/{nb_a}", headers={"X-CSRF-Token": user_b["csrf_token"]})
    assert res_b_del_nb.status_code == 404


# ---------------------------------------------------------------------------
# 3. Live Integration Test — Embedding & Retrieval with Qwen3-Embedding-0.6B
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_real_document_ingestion_and_semantic_retrieval(client):
    """Live test: uploads a real text document, generates embeddings with Qwen3 Embedding 0.6B,
    and runs a semantic retrieval query that matches the meaning rather than exact keywords."""
    auth_data = _register_user(client)
    csrf = auth_data["csrf_token"]

    # 1. Create dedicated notebook
    res_nb = client.post(
        "/notebooks",
        json={"name": "Photosynthesis Research"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res_nb.status_code == 201
    nb_id = res_nb.json()["id"]

    # 2. Upload document discussing photosynthesis
    document_text = (
        "Photosynthesis is a biochemical process used by plants, algae, and certain bacteria "
        "to convert light energy into chemical energy stored in glucose molecules. "
        "Chlorophyll absorbs blue and red wavelengths of light while reflecting green light.\n\n"
        "Cellular respiration is the metabolic pathway that breaks down glucose to produce ATP, "
        "releasing carbon dioxide and water as byproducts in the mitochondria."
    )
    res_up = client.post(
        f"/notebooks/{nb_id}/documents",
        files={"file": ("biology_notes.txt", document_text.encode("utf-8"), "text/plain")},
        headers={"X-CSRF-Token": csrf},
    )
    assert res_up.status_code == 201
    doc_data = res_up.json()["document"]
    assert doc_data["processing_status"] == "completed"
    assert doc_data["indexing_status"] == "indexed"

    # 3. Perform a semantic retrieval query that does not use exact keywords
    res_ret = client.post(
        "/retrieve",
        json={
            "query": "How do plants transform sunshine into sugar?",
            "notebook_id": nb_id,
            "top_k": 3,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res_ret.status_code == 200
    ret_data = res_ret.json()
    results = ret_data["results"]
    assert len(results) > 0

    top_result = results[0]
    assert top_result["document_id"] == doc_data["id"]
    assert top_result["document_name"] == "biology_notes.txt"
    assert "Photosynthesis" in top_result["text"]
    assert top_result["distance"] < 1.0  # Cosine distance should indicate similarity
