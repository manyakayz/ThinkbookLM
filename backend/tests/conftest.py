"""
Shared pytest fixtures for ThinkBook LM tests.
"""
from __future__ import annotations

import math
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# ChromaDB fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def chroma_tmp_dir(tmp_path):
    """Return a temporary directory path suitable for a ChromaDB PersistentClient."""
    return str(tmp_path / "chroma")


@pytest.fixture()
def fresh_chroma_collection(chroma_tmp_dir):
    """Create an isolated ChromaDB collection for each test."""
    import chromadb
    client = chromadb.PersistentClient(path=chroma_tmp_dir)
    col = client.get_or_create_collection(
        name="test_chunks",
        metadata={"hnsw:space": "cosine"},
    )
    return col


# ---------------------------------------------------------------------------
# Fake embedding helpers
# ---------------------------------------------------------------------------

FAKE_DIM = 8  # tiny dimension; just needs to be consistent


def make_fake_embedding(seed: int = 0) -> list[float]:
    """Return a deterministic unit-ish float vector of FAKE_DIM dimensions."""
    base = [float(seed + i + 1) for i in range(FAKE_DIM)]
    norm = math.sqrt(sum(x ** 2 for x in base)) or 1.0
    return [x / norm for x in base]


def make_fake_embeddings(n: int) -> list[list[float]]:
    return [make_fake_embedding(i) for i in range(n)]
