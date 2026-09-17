from __future__ import annotations
"""
Health check endpoints.

`GET /health` is the minimal liveness check the frontend uses to confirm it
can talk to the backend at all -- it does not touch Postgres, Chroma, or
Ollama, so it stays fast and always succeeds as long as the API process is
up.

`GET /health/services` is a slightly deeper check that reports whether each
external system is currently reachable. It's informational only: none of
these services being down will ever cause the backend itself to fail to
start or to fail this endpoint.
"""

from fastapi import APIRouter

from app.services import db, llm, vector_store

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health():
    return {"status": "ok"}


@router.get("/services")
async def services_health():
    postgres_ok, postgres_error = db.ping()
    chroma_ok, chroma_error = vector_store.ping()
    ollama_ok, ollama_error = await llm.ping()

    return {
        "postgres": {"reachable": postgres_ok, "error": postgres_error},
        "chroma": {"reachable": chroma_ok, "error": chroma_error},
        "ollama": {"reachable": ollama_ok, "error": ollama_error},
    }

