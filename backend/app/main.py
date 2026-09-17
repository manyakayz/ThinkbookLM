from __future__ import annotations
"""
FastAPI application entrypoint.

Run with:  uvicorn app.main:app --reload   (from the backend/ directory)

This milestone wires up only:
  - app configuration
  - CORS (so the Vite dev server can call this API)
  - a health check route
  - a generic error handler so unhandled exceptions return JSON, not a
    stack trace, and never crash the running process

Routers for notebooks, documents, chat, retrieval, and study tools will be
added in later milestones under app/api/routes/ and included here.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import documents, health, notebooks, retrieval
from app.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.app_env)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ThinkBook LM API",
    description="Local-first AI research and learning assistant -- backend API.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all so an unexpected error returns a clean 500 JSON body
    instead of leaking a stack trace or crashing the worker."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."},
    )


app.include_router(health.router)
app.include_router(notebooks.router)
app.include_router(documents.router)
app.include_router(retrieval.router)


@app.get("/")
def root():
    return {"service": "thinkbook-lm-api", "status": "running"}

