from __future__ import annotations
"""
Ollama integration boundary.

This milestone only establishes how the backend will reach a locally running
Ollama instance. Prompt construction, RAG, and actual generation calls are
out of scope and will be added in a later milestone.

`ping()` hits Ollama's own `/api/tags` endpoint (lists locally pulled
models) as a lightweight way to confirm the service is reachable, without
requiring the target model to already be pulled.
"""


import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


async def ping() -> tuple[bool, str | None]:
    """Check whether the configured Ollama instance is reachable."""
    settings = get_settings()
    url = f"{settings.ollama_base_url.rstrip('/')}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(url)
            response.raise_for_status()
        return True, None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ollama ping failed: %s", exc)
        return False, str(exc)

