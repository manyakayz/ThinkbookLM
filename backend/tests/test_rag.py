from __future__ import annotations
"""
Unit and integration tests for Phase 3: RAG conversation pipeline.

Covers:
- Unauthenticated requests rejected (401)
- Notebook ownership & cross-notebook isolation (404)
- Document scope validation (400)
- Grounded RAG with mocked retrieval + mocked LLM
- Empty retrieval fallback (grounded=False, model called, sources=[])
- Conversation history forwarding and truncation at MAX_HISTORY_TURNS
- Evidence block building and chunk truncation
- Verified source attribution strictly from retrieval metadata
- Error handling (OllamaUnavailable -> 503, ModelNotFound -> 503, LLMGenerationError -> 502, RAGError -> 400)
- Live end-to-end integration test with real Ollama Qwen3 1.7B and Qwen3 Embedding 0.6B
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.chat import ChatMessage, ChatResponse
from app.models.rag import RAGMessage, RAGRequest, RAGResponse, SourceReference
from app.models.retrieval import RetrievalResult
from app.services import db, llm, rag as rag_service
from app.services.embedding import EmbeddingModelNotFound, OllamaUnavailable as EmbeddingUnavailable
from app.services.rag import (
    MAX_CHUNK_CHARS,
    MAX_EVIDENCE_CHARS,
    MAX_EVIDENCE_CHUNKS,
    MAX_HISTORY_TURNS,
    RAGError,
    _build_evidence_block,
    _build_sources,
    _compose_messages,
)
from app.services.retrieval import RetrievalError


@pytest.fixture
def client():
    return TestClient(app)


def _unique_email() -> str:
    return f"rag_user_{uuid.uuid4().hex[:8]}@example.com"


def _register_user(client: TestClient) -> dict:
    email = _unique_email()
    res = client.post(
        "/auth/register",
        json={
            "full_name": "RAG Tester",
            "email": email,
            "password": "ValidPassword123",
            "confirm_password": "ValidPassword123",
        },
    )
    assert res.status_code == 201
    return res.json()


def _create_notebook(client: TestClient, csrf_token: str, name: str = "Test Notebook") -> int:
    res = client.post(
        "/notebooks",
        json={"name": name},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _make_retrieval_chunk(
    chunk_id: int = 1,
    doc_id: int = 10,
    doc_name: str = "quantum_computing.txt",
    file_type: str = "txt",
    chunk_index: int = 0,
    text: str = "Quantum computers leverage qubits to perform computations exponentially faster.",
    page_number: int | None = None,
    section: str | None = None,
    distance: float = 0.25,
    char_start: int | None = 0,
    char_end: int | None = 100,
) -> RetrievalResult:
    return RetrievalResult(
        vector_id=f"chunk:{doc_id}:{chunk_index}",
        chunk_id=chunk_id,
        document_id=doc_id,
        document_name=doc_name,
        file_type=file_type,
        chunk_index=chunk_index,
        text=text,
        page_number=page_number,
        section=section,
        char_start=char_start,
        char_end=char_end,
        distance=distance,
    )


# ===========================================================================
# 1. Unit Tests for rag_service helpers
# ===========================================================================

def test_build_sources_preserves_retrieval_metadata():
    chunks = [
        _make_retrieval_chunk(chunk_id=101, doc_id=5, doc_name="guide.pdf", page_number=3, distance=0.15),
        _make_retrieval_chunk(chunk_id=102, doc_id=5, doc_name="guide.pdf", page_number=4, distance=0.22),
    ]
    sources = _build_sources(chunks)
    assert len(sources) == 2
    assert sources[0].chunk_id == 101
    assert sources[0].document_name == "guide.pdf"
    assert sources[0].page_number == 3
    assert sources[0].distance == 0.15
    assert sources[1].chunk_id == 102
    assert sources[1].page_number == 4


def test_build_evidence_block_truncates_long_chunks():
    long_text = "A" * (MAX_CHUNK_CHARS + 500)
    chunk = _make_retrieval_chunk(text=long_text)
    block = _build_evidence_block([chunk])
    assert "[truncated]" in block
    # Chunk content within the block should not exceed MAX_CHUNK_CHARS + suffix overhead
    assert len(block) < MAX_CHUNK_CHARS + 200


def test_build_evidence_block_respects_max_evidence_chars():
    chunks = [
        _make_retrieval_chunk(chunk_id=i, text="B" * (MAX_CHUNK_CHARS - 100))
        for i in range(10)
    ]
    block = _build_evidence_block(chunks)
    assert len(block) <= MAX_EVIDENCE_CHARS + 200


def test_compose_messages_empty_retrieval():
    messages = _compose_messages(
        question="What is dark matter?",
        history=[],
        evidence_text="",
        grounded=False,
    )
    assert len(messages) == 1
    assert messages[0].role == "user"
    assert "<EVIDENCE>" in messages[0].content
    assert "No relevant document content was found" in messages[0].content
    assert "Question: What is dark matter?" in messages[0].content


def test_compose_messages_with_history_truncation():
    # Provide 8 pairs (16 messages) -> should be truncated to MAX_HISTORY_TURNS * 2 = 10
    history = [
        RAGMessage(role="user" if i % 2 == 0 else "assistant", content=f"Turn {i}")
        for i in range(16)
    ]
    messages = _compose_messages(
        question="Latest question?",
        history=history,
        evidence_text="[1] Evidence snippet",
        grounded=True,
    )
    # 10 history messages + 1 user prompt turn = 11 total
    assert len(messages) == (MAX_HISTORY_TURNS * 2) + 1
    assert messages[0].content == "Turn 6"
    assert messages[-1].role == "user"
    assert "Question: Latest question?" in messages[-1].content
    assert "<EVIDENCE>" in messages[-1].content
    assert "[1] Evidence snippet" in messages[-1].content


# ===========================================================================
# 2. Endpoint Security & Validation Tests
# ===========================================================================

def test_rag_unauthenticated_rejected(client):
    res = client.post(
        "/chat/rag",
        json={"message": "What is this?", "notebook_id": 1},
    )
    assert res.status_code == 401
    assert "Authentication required" in res.json()["detail"]


def test_rag_notebook_not_found(client):
    auth_data = _register_user(client)
    csrf = auth_data["csrf_token"]

    res = client.post(
        "/chat/rag",
        json={"message": "What is this?", "notebook_id": 999999},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 404
    assert "Notebook not found" in res.json()["detail"]


def test_rag_cross_user_isolation(client):
    user_a = _register_user(client)
    nb_a = _create_notebook(client, user_a["csrf_token"], "User A Notebook")

    client_b = TestClient(app)
    user_b = _register_user(client_b)

    # User B attempts to access User A's notebook
    res = client_b.post(
        "/chat/rag",
        json={"message": "Infiltrate notes", "notebook_id": nb_a},
        headers={"X-CSRF-Token": user_b["csrf_token"]},
    )
    assert res.status_code == 404
    assert "Notebook not found" in res.json()["detail"]


def test_rag_empty_message_rejected(client):
    auth_data = _register_user(client)
    csrf = auth_data["csrf_token"]
    nb_id = _create_notebook(client, csrf)

    res = client.post(
        "/chat/rag",
        json={"message": "   ", "notebook_id": nb_id},
        headers={"X-CSRF-Token": csrf},
    )
    # Either Pydantic min_length or empty validation
    assert res.status_code in (400, 422)


# ===========================================================================
# 3. RAG Pipeline Behavior (Mocked Services)
# ===========================================================================

def test_rag_grounded_answer_success(client):
    auth_data = _register_user(client)
    csrf = auth_data["csrf_token"]
    nb_id = _create_notebook(client, csrf)

    fake_chunks = [
        _make_retrieval_chunk(chunk_id=42, doc_id=7, doc_name="report.pdf", page_number=2, distance=0.18),
    ]

    fake_llm_response = ChatResponse(
        model="qwen3:1.7b",
        message=ChatMessage(role="assistant", content="The report highlights a 45% efficiency boost."),
        response="The report highlights a 45% efficiency boost.",
        done=True,
        eval_count=25,
    )

    with patch("app.services.rag.retrieval_service.retrieve", return_value=fake_chunks) as mock_ret, \
         patch("app.services.rag.llm.chat", new_callable=AsyncMock, return_value=fake_llm_response) as mock_llm:

        res = client.post(
            "/chat/rag",
            json={
                "message": "What was the efficiency boost?",
                "notebook_id": nb_id,
                "top_k": 3,
                "temperature": 0.2,
            },
            headers={"X-CSRF-Token": csrf},
        )

        assert res.status_code == 200
        data = res.json()
        assert data["answer"] == "The report highlights a 45% efficiency boost."
        assert data["grounded"] is True
        assert data["retrieved_count"] == 1
        assert data["notebook_id"] == nb_id
        assert data["model"] == "qwen3:1.7b"

        assert len(data["sources"]) == 1
        source = data["sources"][0]
        assert source["chunk_id"] == 42
        assert source["document_id"] == 7
        assert source["document_name"] == "report.pdf"
        assert source["page_number"] == 2
        assert source["distance"] == 0.18

        mock_ret.assert_called_once()
        mock_llm.assert_called_once()


def test_rag_empty_retrieval_falls_back_ungrounded(client):
    auth_data = _register_user(client)
    csrf = auth_data["csrf_token"]
    nb_id = _create_notebook(client, csrf)

    fake_llm_response = ChatResponse(
        model="qwen3:1.7b",
        message=ChatMessage(role="assistant", content="I cannot find that in the documents, but generally speaking..."),
        response="I cannot find that in the documents, but generally speaking...",
        done=True,
        eval_count=30,
    )

    with patch("app.services.rag.retrieval_service.retrieve", return_value=[]) as mock_ret, \
         patch("app.services.rag.llm.chat", new_callable=AsyncMock, return_value=fake_llm_response) as mock_llm:

        res = client.post(
            "/chat/rag",
            json={"message": "Unrelated topic?", "notebook_id": nb_id},
            headers={"X-CSRF-Token": csrf},
        )

        assert res.status_code == 200
        data = res.json()
        assert data["grounded"] is False
        assert data["sources"] == []
        assert data["retrieved_count"] == 0
        assert "documents" in data["answer"]
        mock_ret.assert_called_once()
        mock_llm.assert_called_once()


def test_rag_passes_history_to_llm(client):
    auth_data = _register_user(client)
    csrf = auth_data["csrf_token"]
    nb_id = _create_notebook(client, csrf)

    fake_chunks = [_make_retrieval_chunk()]
    fake_llm_response = ChatResponse(
        model="qwen3:1.7b",
        message=ChatMessage(role="assistant", content="As mentioned before, it operates via qubits."),
        response="As mentioned before, it operates via qubits.",
        done=True,
    )

    with patch("app.services.rag.retrieval_service.retrieve", return_value=fake_chunks), \
         patch("app.services.rag.llm.chat", new_callable=AsyncMock, return_value=fake_llm_response) as mock_llm:

        history_payload = [
            {"role": "user", "content": "What are qubits?"},
            {"role": "assistant", "content": "Qubits are basic units of quantum information."},
        ]

        res = client.post(
            "/chat/rag",
            json={
                "message": "How do they compute?",
                "notebook_id": nb_id,
                "history": history_payload,
            },
            headers={"X-CSRF-Token": csrf},
        )

        assert res.status_code == 200
        sent_messages = mock_llm.call_args.kwargs["messages"]
        assert len(sent_messages) == 3
        assert sent_messages[0].role == "user"
        assert sent_messages[0].content == "What are qubits?"
        assert sent_messages[1].role == "assistant"
        assert sent_messages[1].content == "Qubits are basic units of quantum information."
        assert sent_messages[2].role == "user"
        assert "How do they compute?" in sent_messages[2].content


def test_rag_invalid_scope_returns_400(client):
    auth_data = _register_user(client)
    csrf = auth_data["csrf_token"]
    nb_id = _create_notebook(client, csrf)

    with patch("app.services.rag.retrieval_service.retrieve", side_effect=RetrievalError("Document IDs [99] do not belong to notebook")):
        res = client.post(
            "/chat/rag",
            json={
                "message": "Test question",
                "notebook_id": nb_id,
                "document_ids": [99],
            },
            headers={"X-CSRF-Token": csrf},
        )
        assert res.status_code == 400
        assert "do not belong" in res.json()["detail"]


def test_rag_ollama_unavailable_returns_503(client):
    auth_data = _register_user(client)
    csrf = auth_data["csrf_token"]
    nb_id = _create_notebook(client, csrf)

    with patch("app.services.rag.retrieval_service.retrieve", side_effect=EmbeddingUnavailable("Connection refused")):
        res = client.post(
            "/chat/rag",
            json={"message": "Any query", "notebook_id": nb_id},
            headers={"X-CSRF-Token": csrf},
        )
        assert res.status_code == 503
        assert "Ollama is not available" in res.json()["detail"]


def test_rag_llm_model_not_found_returns_503(client):
    auth_data = _register_user(client)
    csrf = auth_data["csrf_token"]
    nb_id = _create_notebook(client, csrf)

    with patch("app.services.rag.retrieval_service.retrieve", return_value=[]), \
         patch("app.services.rag.llm.chat", new_callable=AsyncMock, side_effect=llm.LLMModelNotFound("Model 'qwen3:1.7b' is not available in Ollama")):
        res = client.post(
            "/chat/rag",
            json={"message": "Any query", "notebook_id": nb_id},
            headers={"X-CSRF-Token": csrf},
        )
        assert res.status_code == 503
        assert "not available in Ollama" in res.json()["detail"]


def test_rag_llm_generation_error_returns_502(client):
    auth_data = _register_user(client)
    csrf = auth_data["csrf_token"]
    nb_id = _create_notebook(client, csrf)

    with patch("app.services.rag.retrieval_service.retrieve", return_value=[]), \
         patch("app.services.rag.llm.chat", new_callable=AsyncMock, side_effect=llm.LLMGenerationError("Inference failed")):
        res = client.post(
            "/chat/rag",
            json={"message": "Any query", "notebook_id": nb_id},
            headers={"X-CSRF-Token": csrf},
        )
        assert res.status_code == 502
        assert "LLM generation failed" in res.json()["detail"]


def test_rag_unrelated_query_exceeding_threshold_is_ungrounded(client):
    """When retrieved chunks have cosine distance > threshold, they are discarded."""
    auth_data = _register_user(client)
    csrf = auth_data["csrf_token"]
    nb_id = _create_notebook(client, csrf)

    # Chunk exists in notebook, but cosine distance is 0.78 (unrelated)
    distant_chunk = _make_retrieval_chunk(
        chunk_id=99,
        doc_id=1,
        doc_name="finance.pdf",
        text="Q3 quarterly revenue exceeded projections by 12 percent.",
        distance=0.78,
    )

    fake_llm_response = ChatResponse(
        model="qwen3:1.7b",
        message=ChatMessage(role="assistant", content="No document information was found about astronomy."),
        response="No document information was found about astronomy.",
        done=True,
    )

    with patch("app.services.rag.retrieval_service.retrieve", return_value=[distant_chunk]), \
         patch("app.services.rag.llm.chat", new_callable=AsyncMock, return_value=fake_llm_response) as mock_llm:

        res = client.post(
            "/chat/rag",
            json={"message": "How many moons does Saturn have?", "notebook_id": nb_id},
            headers={"X-CSRF-Token": csrf},
        )

        assert res.status_code == 200
        data = res.json()
        assert data["grounded"] is False
        assert data["sources"] == []
        assert data["retrieved_count"] == 1  # 1 candidate was retrieved from Chroma

        # Verify LLM was informed that no relevant document content was found
        sent_messages = mock_llm.call_args.kwargs["messages"]
        user_turn = sent_messages[-1].content
        assert "No relevant document content was found" in user_turn
        assert "finance.pdf" not in user_turn


def test_rag_partial_evidence_filters_distant_chunks_conservatively(client):
    """When some chunks are relevant (distance <= 0.60) and some are distant, only relevant chunks are used."""
    auth_data = _register_user(client)
    csrf = auth_data["csrf_token"]
    nb_id = _create_notebook(client, csrf)

    chunks = [
        _make_retrieval_chunk(chunk_id=1, text="Primary thruster produces 500 N thrust.", distance=0.22),
        _make_retrieval_chunk(chunk_id=2, text="Secondary attitude control uses cold gas.", distance=0.48),
        _make_retrieval_chunk(chunk_id=3, text="Cafeteria menu offers chicken soup on Tuesdays.", distance=0.82),
    ]

    fake_llm_response = ChatResponse(
        model="qwen3:1.7b",
        message=ChatMessage(role="assistant", content="The thruster produces 500 N and uses cold gas for attitude."),
        response="The thruster produces 500 N and uses cold gas for attitude.",
        done=True,
    )

    with patch("app.services.rag.retrieval_service.retrieve", return_value=chunks), \
         patch("app.services.rag.llm.chat", new_callable=AsyncMock, return_value=fake_llm_response) as mock_llm:

        res = client.post(
            "/chat/rag",
            json={"message": "Describe propulsion and attitude systems", "notebook_id": nb_id},
            headers={"X-CSRF-Token": csrf},
        )

        assert res.status_code == 200
        data = res.json()
        assert data["grounded"] is True
        assert data["retrieved_count"] == 3
        # Only chunks 1 and 2 should be in sources; chunk 3 (0.82) must be excluded
        assert len(data["sources"]) == 2
        assert data["sources"][0]["chunk_id"] == 1
        assert data["sources"][1]["chunk_id"] == 2

        # Verify chunk 3 is not in the prompt sent to LLM
        sent_messages = mock_llm.call_args.kwargs["messages"]
        prompt_text = sent_messages[-1].content
        assert "Primary thruster" in prompt_text
        assert "Secondary attitude" in prompt_text
        assert "Cafeteria menu" not in prompt_text


def test_rag_custom_relevance_threshold_override(client):
    """Callers can provide a tighter or looser relevance_threshold in the request."""
    auth_data = _register_user(client)
    csrf = auth_data["csrf_token"]
    nb_id = _create_notebook(client, csrf)

    chunk = _make_retrieval_chunk(chunk_id=1, text="Marginally relevant information.", distance=0.55)

    fake_llm_response = ChatResponse(
        model="qwen3:1.7b",
        message=ChatMessage(role="assistant", content="Response text."),
        response="Response text.",
        done=True,
    )

    with patch("app.services.rag.retrieval_service.retrieve", return_value=[chunk]), \
         patch("app.services.rag.llm.chat", new_callable=AsyncMock, return_value=fake_llm_response):

        # 1. With tight threshold 0.50 -> 0.55 chunk is filtered out
        res_tight = client.post(
            "/chat/rag",
            json={"message": "Query", "notebook_id": nb_id, "relevance_threshold": 0.50},
            headers={"X-CSRF-Token": csrf},
        )
        assert res_tight.status_code == 200
        assert res_tight.json()["grounded"] is False
        assert res_tight.json()["sources"] == []

        # 2. With loose threshold 0.70 -> 0.55 chunk is accepted
        res_loose = client.post(
            "/chat/rag",
            json={"message": "Query", "notebook_id": nb_id, "relevance_threshold": 0.70},
            headers={"X-CSRF-Token": csrf},
        )
        assert res_loose.status_code == 200
        assert res_loose.json()["grounded"] is True
        assert len(res_loose.json()["sources"]) == 1


# ===========================================================================
# 4. End-to-End Integration Test (Live Ollama & Postgres & ChromaDB)
# ===========================================================================

@pytest.mark.integration
def test_real_rag_pipeline_live(client):
    """Full live test: create notebook, upload doc, retrieve, and ask Qwen3 1.7B."""
    auth_data = _register_user(client)
    csrf = auth_data["csrf_token"]
    nb_id = _create_notebook(client, csrf, "Mars Mission Notebook")

    # Upload document with specific distinct facts
    doc_text = (
        "Project Ares Flight Plan:\n"
        "The spacecraft designated 'Ares-7' was launched on March 14, 2028.\n"
        "Its primary propulsion system uses a magnetoplasmadynamic thruster with Xenon propellant.\n"
        "The mission commander is Dr. Elena Rostova, and the journey to Martian orbit takes 180 days."
    )

    up_res = client.post(
        f"/notebooks/{nb_id}/documents",
        files={"file": ("ares_flight_plan.txt", doc_text.encode("utf-8"), "text/plain")},
        headers={"X-CSRF-Token": csrf},
    )
    assert up_res.status_code == 201
    doc_id = up_res.json()["document"]["id"]

    # 1. Ask a question specifically answered by the document
    rag_res = client.post(
        "/chat/rag",
        json={
            "message": "What is the name of the spacecraft and who is the mission commander?",
            "notebook_id": nb_id,
            "document_ids": [doc_id],
            "top_k": 3,
            "temperature": 0.1,
        },
        headers={"X-CSRF-Token": csrf},
    )

    assert rag_res.status_code == 200, f"RAG request failed: {rag_res.text}"
    data = rag_res.json()

    assert data["grounded"] is True
    assert data["retrieved_count"] > 0
    assert len(data["sources"]) > 0

    first_source = data["sources"][0]
    assert first_source["document_name"] == "ares_flight_plan.txt"
    assert first_source["document_id"] == doc_id
    assert first_source["distance"] <= 0.60  # Meets relevance threshold

    # Answer should contain information from the document
    answer = data["answer"]
    assert "Ares-7" in answer or "Ares" in answer
    assert "Elena" in answer or "Rostova" in answer

    # 2. Ask an unrelated question to verify ungrounded fallback on live pipeline
    unrelated_res = client.post(
        "/chat/rag",
        json={
            "message": "What is the traditional recipe for baking sourdough bread?",
            "notebook_id": nb_id,
            "document_ids": [doc_id],
            "temperature": 0.1,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert unrelated_res.status_code == 200
    unrelated_data = unrelated_res.json()
    assert unrelated_data["grounded"] is False
    assert unrelated_data["sources"] == []
    assert unrelated_data["retrieved_count"] > 0

