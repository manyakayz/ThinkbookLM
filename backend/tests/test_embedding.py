"""
Tests for the embedding service (app/services/embedding.py).

Unit tests use httpx mocks and do not require a running Ollama instance.
Integration tests are marked with @pytest.mark.integration and require
`ollama serve` with the qwen3-embedding:0.6b model pulled.

Run unit tests only:
    pytest tests/test_embedding.py -m "not integration"

Run all (requires Ollama):
    pytest tests/test_embedding.py
"""
from __future__ import annotations

import pytest
import httpx
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_embed_response(embeddings: list[list[float]], status: int = 200):
    """Build a mock httpx.Response for the /api/embed endpoint."""
    import json
    content = json.dumps({"embeddings": embeddings}).encode()
    request = httpx.Request("POST", "http://test")
    return httpx.Response(status_code=status, content=content, request=request)


# ---------------------------------------------------------------------------
# Configuration tests
# ---------------------------------------------------------------------------

def test_embedding_model_is_configurable():
    """EMBEDDING_MODEL setting must be exposed on the Settings object."""
    from app.config import Settings
    s = Settings(embedding_model="test-model:0.1b")
    assert s.embedding_model == "test-model:0.1b"


def test_embedding_batch_size_default():
    """Default batch size should be 16 (RAM-conscious for 8 GB target machine)."""
    from app.config import Settings
    s = Settings()
    assert s.embedding_batch_size == 16


def test_retrieval_top_k_default():
    """Default top_k should be 5."""
    from app.config import Settings
    s = Settings()
    assert s.retrieval_top_k == 5


# ---------------------------------------------------------------------------
# embed_texts — unit tests (mocked HTTP)
# ---------------------------------------------------------------------------

def test_embed_texts_empty_list_returns_empty():
    """embed_texts([]) must short-circuit and return [] without hitting Ollama."""
    from app.services.embedding import embed_texts
    result = embed_texts([])
    assert result == []


def test_embed_texts_returns_one_vector_per_input():
    """embed_texts must return exactly as many vectors as texts supplied."""
    fake_embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    response = _make_embed_response(fake_embeddings)

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = response
        mock_client_cls.return_value = mock_client

        from app.services import embedding as emb_module
        result = emb_module.embed_texts(["hello", "world"])

    assert len(result) == 2
    assert result[0] == [0.1, 0.2, 0.3]
    assert result[1] == [0.4, 0.5, 0.6]


def test_embed_query_returns_single_vector():
    """embed_query must unwrap the list and return a single 1-D vector."""
    fake_vec = [0.9, 0.8, 0.7]
    response = _make_embed_response([fake_vec])

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = response
        mock_client_cls.return_value = mock_client

        from app.services import embedding as emb_module
        result = emb_module.embed_query("what is this?")

    assert result == fake_vec


def test_ollama_unavailable_raises_correct_exception():
    """A ConnectError from httpx must be re-raised as OllamaUnavailable."""
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = httpx.ConnectError("refused")
        mock_client_cls.return_value = mock_client

        from app.services.embedding import embed_texts, OllamaUnavailable
        with pytest.raises(OllamaUnavailable):
            embed_texts(["test"])


def test_timeout_raises_ollama_unavailable():
    """A TimeoutException from httpx must also surface as OllamaUnavailable."""
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = httpx.TimeoutException("timeout")
        mock_client_cls.return_value = mock_client

        from app.services.embedding import embed_texts, OllamaUnavailable
        with pytest.raises(OllamaUnavailable):
            embed_texts(["test"])


def test_embedding_model_not_found_on_404():
    """An HTTP 404 from Ollama must be re-raised as EmbeddingModelNotFound."""
    response = httpx.Response(status_code=404, content=b"model not found")

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = response
        mock_client_cls.return_value = mock_client

        from app.services.embedding import embed_texts, EmbeddingModelNotFound
        with pytest.raises(EmbeddingModelNotFound) as exc_info:
            embed_texts(["test"])

    # Error message should guide the user on how to fix it
    assert "ollama pull" in str(exc_info.value).lower()


def test_batching_calls_api_multiple_times():
    """With batch_size=2 and 5 texts, the API must be called ceil(5/2)=3 times."""
    fake_vec = [0.1, 0.2]
    # Each call returns embeddings for the batch
    batch_responses = [
        _make_embed_response([fake_vec, fake_vec]),
        _make_embed_response([fake_vec, fake_vec]),
        _make_embed_response([fake_vec]),
    ]

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = batch_responses
        mock_client_cls.return_value = mock_client

        with patch("app.services.embedding.get_settings") as mock_settings:
            settings = MagicMock()
            settings.embedding_batch_size = 2
            settings.embedding_model = "test-model"
            settings.ollama_base_url = "http://localhost:11434"
            mock_settings.return_value = settings

            from app.services import embedding as emb_module
            # Force re-read of settings
            result = emb_module.embed_texts(["a", "b", "c", "d", "e"])

    assert mock_client.post.call_count == 3
    assert len(result) == 5


# ---------------------------------------------------------------------------
# Integration tests — require `ollama serve` + qwen3-embedding:0.6b pulled
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_real_embed_query_returns_float_vector():
    """Integration: embed a short string; result must be a non-empty float vector."""
    from app.services.embedding import embed_query
    vec = embed_query("What is the capital of France?")
    assert isinstance(vec, list)
    assert len(vec) > 0
    assert all(isinstance(v, float) for v in vec)


@pytest.mark.integration
def test_real_embed_texts_batch():
    """Integration: embed multiple texts; lengths and types must be correct."""
    from app.services.embedding import embed_texts
    texts = ["Hello world", "Second sentence", "Third one"]
    vecs = embed_texts(texts)
    assert len(vecs) == 3
    assert all(isinstance(v, list) for v in vecs)
    # All vectors must have the same dimension
    dims = {len(v) for v in vecs}
    assert len(dims) == 1
