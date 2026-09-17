from __future__ import annotations
"""
Centralized application configuration.

All environment-driven settings live here so the rest of the codebase never
reads `os.environ` directly. Values are loaded from a `.env` file in the
`backend/` directory (see `.env.example` for the full list of variables and
what they mean) and can be overridden by real environment variables.

Nothing in this file should require any external service (Postgres, Chroma,
Ollama) to actually be running -- it only describes how to reach them.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- PostgreSQL ---
    postgres_dsn: str = "postgresql://thinkbook:thinkbook@localhost:5432/thinkbook_lm"

    # --- ChromaDB ---
    chroma_persist_dir: str = "./data/chroma"

    # --- Ollama ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:1.7b"
    # Embedding model (Milestone 2). Must be pulled via `ollama pull <name>`.
    embedding_model: str = "qwen3-embedding:0.6b"
    # Number of chunk texts sent in a single /api/embed batch call. Lowering
    # this reduces peak RAM usage on the 8 GB target machine.
    embedding_batch_size: int = 16

    # --- Document ingestion (Milestone 1) ---
    # Local, on-disk directory where uploaded source files are stored.
    document_storage_dir: str = "./data/documents"
    # Single source of truth for the upload size limit -- read here, not
    # hard-coded at each place that checks it.
    max_upload_size_mb: int = 25
    # Comma-separated list of extensions accepted at upload time.
    allowed_file_types: str = "pdf,docx,txt"
    # Chunking is character-based (not token-based) for this milestone to
    # avoid adding a tokenizer dependency before the embedding model is
    # wired up; revisit sizing once Qwen3-Embedding-0.6B is integrated.
    chunk_size_chars: int = 1200
    chunk_overlap_chars: int = 200

    # --- Retrieval (Milestone 2) ---
    # Default number of chunks returned per query. Validated at the API layer.
    retrieval_top_k: int = 5

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def allowed_file_types_list(self) -> list[str]:
        return [ext.strip().lower() for ext in self.allowed_file_types.split(",") if ext.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Settings are cheap to build but we only need one instance per process."""
    return Settings()

