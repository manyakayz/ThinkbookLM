from __future__ import annotations
"""
Tests for the /chat API routes (app/api/routes/chat.py).
"""

import uuid
from unittest.mock import AsyncMock, patch
import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.chat import ChatMessage, ChatResponse
from app.services import llm


@pytest.fixture
def client():
    return TestClient(app)


def _unique_email() -> str:
    return f"user_{uuid.uuid4().hex[:8]}@example.com"


def _register_and_get_client() -> tuple[TestClient, dict]:
    client = TestClient(app)
    email = _unique_email()
    res = client.post(
        "/auth/register",
        json={
            "full_name": "Chat Test User",
            "email": email,
            "password": "ValidPassword123",
            "confirm_password": "ValidPassword123",
        },
    )
    assert res.status_code == 201
    return client, res.json()


# ---------------------------------------------------------------------------
# Route Security & Validation
# ---------------------------------------------------------------------------

def test_chat_unauthenticated_rejected(client):
    res = client.post("/chat", json={"message": "Hello without auth"})
    assert res.status_code == 401
    assert "Authentication required" in res.json()["detail"]


def test_chat_validation_empty_body(client):
    auth_client, auth_data = _register_and_get_client()
    res = auth_client.post("/chat", json={}, headers={"X-CSRF-Token": auth_data["csrf_token"]})
    assert res.status_code == 422


def test_chat_validation_empty_message(client):
    auth_client, auth_data = _register_and_get_client()
    res = auth_client.post(
        "/chat",
        json={"message": "   "},
        headers={"X-CSRF-Token": auth_data["csrf_token"]},
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Route Behavior with Mocked LLM Service
# ---------------------------------------------------------------------------

def test_chat_success_with_single_message():
    auth_client, auth_data = _register_and_get_client()

    fake_response = ChatResponse(
        model="qwen3:1.7b",
        message=ChatMessage(role="assistant", content="The capital of Japan is Tokyo."),
        response="The capital of Japan is Tokyo.",
        done=True,
        eval_count=20,
    )

    with patch("app.services.llm.chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = fake_response

        res = auth_client.post(
            "/chat",
            json={"message": "What is the capital of Japan?"},
            headers={"X-CSRF-Token": auth_data["csrf_token"]},
        )

        assert res.status_code == 200
        data = res.json()
        assert data["response"] == "The capital of Japan is Tokyo."
        assert data["model"] == "qwen3:1.7b"
        assert data["message"]["role"] == "assistant"
        assert mock_chat.called


def test_chat_success_with_messages_list():
    auth_client, auth_data = _register_and_get_client()

    fake_response = ChatResponse(
        model="qwen3:1.7b",
        message=ChatMessage(role="assistant", content="I remember your name is Alice!"),
        response="I remember your name is Alice!",
        done=True,
    )

    with patch("app.services.llm.chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = fake_response

        messages_payload = [
            {"role": "user", "content": "My name is Alice."},
            {"role": "assistant", "content": "Nice to meet you, Alice!"},
            {"role": "user", "content": "Do you remember my name?"},
        ]

        res = auth_client.post(
            "/chat",
            json={"messages": messages_payload},
            headers={"X-CSRF-Token": auth_data["csrf_token"]},
        )

        assert res.status_code == 200
        data = res.json()
        assert "Alice" in data["response"]


def test_chat_ollama_unavailable_returns_503():
    auth_client, auth_data = _register_and_get_client()

    with patch("app.services.llm.chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.side_effect = llm.OllamaUnavailable("Cannot reach Ollama at http://localhost:11434")

        res = auth_client.post(
            "/chat",
            json={"message": "Hello"},
            headers={"X-CSRF-Token": auth_data["csrf_token"]},
        )

        assert res.status_code == 503
        assert "Ollama is not available" in res.json()["detail"]


def test_chat_model_not_found_returns_503():
    auth_client, auth_data = _register_and_get_client()

    with patch("app.services.llm.chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.side_effect = llm.LLMModelNotFound("Model 'qwen3:1.7b' is not available in Ollama. Pull it with: `ollama pull qwen3:1.7b`")

        res = auth_client.post(
            "/chat",
            json={"message": "Hello"},
            headers={"X-CSRF-Token": auth_data["csrf_token"]},
        )

        assert res.status_code == 503
        assert "ollama pull" in res.json()["detail"]


def test_chat_generation_error_returns_502():
    auth_client, auth_data = _register_and_get_client()

    with patch("app.services.llm.chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.side_effect = llm.LLMGenerationError("Ollama returned HTTP 500: Server crashed")

        res = auth_client.post(
            "/chat",
            json={"message": "Hello"},
            headers={"X-CSRF-Token": auth_data["csrf_token"]},
        )

        assert res.status_code == 502
        assert "LLM generation failed" in res.json()["detail"]


# ---------------------------------------------------------------------------
# Integration Test — Real Qwen3 1.7B through the API endpoint
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_real_chat_endpoint_with_qwen3():
    """Live test hitting POST /chat through FastAPI, calling real Qwen3 1.7B via Ollama."""
    auth_client, auth_data = _register_and_get_client()

    res = auth_client.post(
        "/chat",
        json={"message": "Reply with only the word 'BANANA' and no other words."},
        headers={"X-CSRF-Token": auth_data["csrf_token"]},
    )

    assert res.status_code == 200, f"Chat endpoint failed: {res.text}"
    data = res.json()
    assert "response" in data
    assert len(data["response"].strip()) > 0
    assert "BANANA" in data["response"].upper()
    assert data["model"] == "qwen3:1.7b"
