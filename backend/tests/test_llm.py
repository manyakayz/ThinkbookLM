from __future__ import annotations
"""
Tests for Ollama LLM service (app/services/llm.py).
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest

from app.models.chat import ChatMessage, ChatResponse
from app.services import llm


def _make_mock_ollama_chat_response(
    content: str = "Hello, I am Qwen3!",
    role: str = "assistant",
    model: str = "qwen3:1.7b",
    status_code: int = 200,
) -> httpx.Response:
    payload = {
        "model": model,
        "created_at": "2026-10-22T00:00:00Z",
        "message": {"role": role, "content": content},
        "done": True,
        "total_duration": 12345678,
        "prompt_eval_count": 10,
        "eval_count": 15,
    }
    request = httpx.Request("POST", "http://localhost:11434/api/chat")
    return httpx.Response(status_code=status_code, json=payload, request=request)


# ---------------------------------------------------------------------------
# Unit tests with mocked HTTP client
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_llm_ping_success():
    request = httpx.Request("GET", "http://localhost:11434/api/tags")
    resp = httpx.Response(status_code=200, json={"models": []}, request=request)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = resp
        ok, err = await llm.ping()
        assert ok is True
        assert err is None


@pytest.mark.anyio
async def test_llm_ping_failure():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.ConnectError("Connection refused")
        ok, err = await llm.ping()
        assert ok is False
        assert "Connection refused" in err


@pytest.mark.anyio
async def test_llm_chat_success():
    mock_resp = _make_mock_ollama_chat_response(content="Paris is the capital of France.")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        messages = [ChatMessage(role="user", content="What is the capital of France?")]
        result = await llm.chat(messages)

        assert isinstance(result, ChatResponse)
        assert result.response == "Paris is the capital of France."
        assert result.message.role == "assistant"
        assert result.model == "qwen3:1.7b"
        assert result.done is True
        assert result.eval_count == 15

        # Check call arguments
        call_kwargs = mock_post.call_args.kwargs
        payload = call_kwargs["json"]
        assert payload["model"] == "qwen3:1.7b"
        assert payload["messages"] == [{"role": "user", "content": "What is the capital of France?"}]


@pytest.mark.anyio
async def test_llm_chat_with_system_prompt():
    mock_resp = _make_mock_ollama_chat_response(content="I am a concise tutor.")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        messages = [ChatMessage(role="user", content="Who are you?")]
        result = await llm.chat(
            messages,
            system_prompt="You are a helpful tutor.",
            temperature=0.2,
        )

        assert result.response == "I am a concise tutor."
        payload = mock_post.call_args.kwargs["json"]
        assert payload["messages"][0] == {"role": "system", "content": "You are a helpful tutor."}
        assert payload["messages"][1] == {"role": "user", "content": "Who are you?"}
        assert payload["options"]["temperature"] == 0.2


@pytest.mark.anyio
async def test_llm_generate_helper():
    mock_resp = _make_mock_ollama_chat_response(content="Generated answer.")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await llm.generate("Explain quantum computing in 1 sentence.")
        assert result == "Generated answer."


@pytest.mark.anyio
async def test_llm_chat_connection_error():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ConnectError("Connection refused")

        with pytest.raises(llm.OllamaUnavailable) as exc_info:
            await llm.chat([ChatMessage(role="user", content="Hi")])

        assert "Cannot reach Ollama" in str(exc_info.value)
        assert "ollama serve" in str(exc_info.value)


@pytest.mark.anyio
async def test_llm_chat_timeout_error():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Timed out")

        with pytest.raises(llm.OllamaUnavailable) as exc_info:
            await llm.chat([ChatMessage(role="user", content="Hi")])

        assert "timed out" in str(exc_info.value).lower()


@pytest.mark.anyio
async def test_llm_chat_model_not_found():
    req = httpx.Request("POST", "http://localhost:11434/api/chat")
    resp_404 = httpx.Response(status_code=404, text='{"error":"model \'nonexistent\' not found"}', request=req)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = resp_404

        with pytest.raises(llm.LLMModelNotFound) as exc_info:
            await llm.chat([ChatMessage(role="user", content="Hi")], model="nonexistent")

        assert "not available in Ollama" in str(exc_info.value)
        assert "ollama pull nonexistent" in str(exc_info.value)


@pytest.mark.anyio
async def test_llm_chat_server_error():
    req = httpx.Request("POST", "http://localhost:11434/api/chat")
    resp_500 = httpx.Response(status_code=500, text="Internal error", request=req)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = resp_500

        with pytest.raises(llm.LLMGenerationError) as exc_info:
            await llm.chat([ChatMessage(role="user", content="Hi")])

        assert "HTTP 500" in str(exc_info.value)


def test_llm_chat_sync():
    mock_resp = _make_mock_ollama_chat_response(content="Sync answer.")

    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value = mock_resp
        res = llm.chat_sync([ChatMessage(role="user", content="Hello")])
        assert res.response == "Sync answer."


def test_llm_generate_sync():
    mock_resp = _make_mock_ollama_chat_response(content="Sync prompt answer.")

    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value = mock_resp
        res = llm.generate_sync("Hello sync")
        assert res == "Sync prompt answer."


# ---------------------------------------------------------------------------
# Integration tests — requires running Ollama with qwen3:1.7b
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.anyio
async def test_real_llm_ping():
    """Verify live connectivity to Ollama server."""
    ok, err = await llm.ping()
    assert ok is True, f"Ollama ping failed: {err}"


@pytest.mark.integration
@pytest.mark.anyio
async def test_real_qwen3_chat_generation():
    """Verify real Qwen3 1.7B response to a prompt."""
    prompt = "Reply with exactly the word 'PONG' and nothing else."
    response = await llm.generate(prompt, temperature=0.1)
    assert response is not None
    assert len(response.strip()) > 0
    assert "PONG" in response.upper()
