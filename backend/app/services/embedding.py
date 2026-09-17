from __future__ import annotations
"""
Embedding service — wraps Ollama's /api/embed endpoint via httpx.

All embedding calls (both document chunks and query-time) go through here
so the rest of the codebase never needs to know which model is in use or
what the Ollama wire protocol looks like.

Design notes:
- Uses /api/embed (Ollama's batch embedding endpoint) rather than
  /api/embeddings (deprecated single-text endpoint).
- The response has shape: {"embeddings": [[float, ...], ...]}
- Synchronous: embedding is currently done in the same thread as the
  upload handler. If this becomes a bottleneck, move to BackgroundTasks.
- Two explicit exception types so callers can give the user a useful message.
"""

import logging
import time

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class OllamaUnavailable(Exception):
    """Raised when the Ollama server cannot be reached at all."""


class EmbeddingModelNotFound(Exception):
    """Raised when Ollama is reachable but the embedding model is not pulled."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts in configurable batches.

    Returns one float vector per input text in the same order.
    Raises OllamaUnavailable or EmbeddingModelNotFound on failure.
    """
    if not texts:
        return []

    settings = get_settings()
    batch_size = settings.embedding_batch_size
    all_embeddings: list[list[float]] = []

    t0 = time.monotonic()
    for batch_start in range(0, len(texts), batch_size):
        batch = texts[batch_start: batch_start + batch_size]
        embeddings = _call_embed_api(batch, settings.embedding_model, settings.ollama_base_url)
        all_embeddings.extend(embeddings)

    elapsed = time.monotonic() - t0
    logger.info(
        "Embedded %d texts in %.2fs (model=%s, batch_size=%d)",
        len(texts), elapsed, settings.embedding_model, batch_size,
    )
    return all_embeddings


def embed_query(text: str) -> list[float]:
    """Generate a single embedding for a retrieval query."""
    results = embed_texts([text])
    return results[0]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _call_embed_api(
    texts: list[str],
    model: str,
    base_url: str,
) -> list[list[float]]:
    """Send one /api/embed batch request and return the embedding vectors."""
    url = f"{base_url.rstrip('/')}/api/embed"
    payload = {"model": model, "input": texts}

    try:
        with httpx.Client(timeout=120.0) as client:  # generous timeout for first call (model load)
            response = client.post(url, json=payload)
    except httpx.ConnectError as exc:
        raise OllamaUnavailable(
            f"Cannot reach Ollama at {base_url}. "
            "Make sure Ollama is running: `ollama serve`"
        ) from exc
    except httpx.TimeoutException as exc:
        raise OllamaUnavailable(
            f"Ollama at {base_url} timed out. "
            "The model may still be loading — try again in a moment."
        ) from exc

    if response.status_code == 404:
        raise EmbeddingModelNotFound(
            f"Embedding model '{model}' is not available in Ollama. "
            f"Pull it with: `ollama pull {model}`"
        )

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise OllamaUnavailable(
            f"Ollama returned HTTP {response.status_code}: {response.text}"
        ) from exc

    data = response.json()
    embeddings = data.get("embeddings")
    if not embeddings or not isinstance(embeddings, list):
        raise OllamaUnavailable(
            f"Unexpected response from Ollama /api/embed: {data!r}"
        )

    return embeddings
