from __future__ import annotations

import logging
from typing import Any

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from app.config import get_settings

logger = logging.getLogger(__name__)

# Cache the client so it's reused across the process lifecycle
_client: ClientAPI | None = None


def get_client() -> ClientAPI:
    global _client
    if _client is None:
        settings = get_settings()
        _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return _client


def get_collection(expected_dim: int | None = None) -> Collection:
    """Return (or create) the thinkbook_chunks collection.

    If *expected_dim* is supplied and the existing collection was built with a
    different embedding dimension (e.g. dim-8 from the test suite), the stale
    collection is deleted and recreated so the server never crashes with
    ``InvalidDimensionException``.
    """
    client = get_client()
    collection = client.get_or_create_collection("thinkbook_chunks")

    if expected_dim is not None and collection.count() > 0:
        # Peek at one vector to check its dimension
        try:
            sample = collection.peek(limit=1)
            if sample["embeddings"] and len(sample["embeddings"][0]) != expected_dim:
                logger.warning(
                    "ChromaDB collection 'thinkbook_chunks' has dimension %d "
                    "but embeddings have dimension %d — deleting and recreating.",
                    len(sample["embeddings"][0]),
                    expected_dim,
                )
                client.delete_collection("thinkbook_chunks")
                collection = client.get_or_create_collection("thinkbook_chunks")
        except Exception as exc:
            logger.warning("Could not validate collection dimension: %s", exc)

    return collection


def make_vector_id(document_id: int, chunk_index: int) -> str:
    return f"chunk:{document_id}:{chunk_index}"


def ping() -> tuple[bool, str | None]:
    try:
        client = get_client()
        client.heartbeat()
        return True, None
    except Exception as e:
        return False, str(e)


def upsert_chunks(
    document_id: int,
    notebook_id: int,
    source_filename: str,
    file_type: str,
    chunks: list[dict],
    embeddings: list[list[float]],
) -> int:
    if not chunks:
        return 0

    dim = len(embeddings[0]) if embeddings else None
    collection = get_collection(expected_dim=dim)

    ids = []
    documents = []
    metadatas = []

    for chunk, embedding in zip(chunks, embeddings):
        ids.append(make_vector_id(document_id, chunk["chunk_index"]))
        documents.append(chunk["text"])
        metadatas.append(
            {
                "document_id": document_id,
                "chunk_id": chunk["id"],
                "notebook_id": notebook_id,
                "chunk_index": chunk["chunk_index"],
                "source_filename": source_filename,
                "file_type": file_type,
                "page_number": chunk["page_number"] if chunk["page_number"] is not None else -1,
                "section": chunk["section"] if chunk["section"] is not None else "",
            }
        )

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    return len(ids)


def delete_document(document_id: int) -> None:
    collection = get_collection()
    collection.delete(where={"document_id": document_id})


def query(
    embedding: list[float],
    notebook_id: int,
    document_ids: list[int],
    top_k: int,
) -> dict[str, Any]:
    collection = get_collection()
    
    # Fast path for empty collection to avoid ValueError on some chromadb versions
    if collection.count() == 0:
        return {"ids": [[]], "distances": [[]], "metadatas": [[]], "documents": [[]]}

    where_clause: dict[str, Any] = {"notebook_id": notebook_id}

    if document_ids:
        if len(document_ids) == 1:
            where_clause = {
                "$and": [
                    {"notebook_id": notebook_id},
                    {"document_id": document_ids[0]},
                ]
            }
        else:
            where_clause = {
                "$and": [
                    {"notebook_id": notebook_id},
                    {"document_id": {"$in": document_ids}},
                ]
            }

    results = collection.query(
        query_embeddings=[embedding],
        n_results=top_k,
        where=where_clause,
    )

    return results
