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
    collection = client.get_or_create_collection(
        "thinkbook_chunks",
        metadata={"hnsw:space": "cosine"},
    )

    if expected_dim is not None:
        current_dim = getattr(getattr(collection, "_model", None), "dimension", None)
        if current_dim is not None and current_dim != expected_dim:
            logger.warning(
                "ChromaDB collection 'thinkbook_chunks' has dimension %d "
                "but embeddings have dimension %d — deleting and recreating.",
                current_dim,
                expected_dim,
            )
            client.delete_collection("thinkbook_chunks")
            collection = client.get_or_create_collection(
                "thinkbook_chunks",
                metadata={"hnsw:space": "cosine"},
            )
        elif current_dim is None and collection.count() > 0:
            try:
                sample = collection.get(include=["embeddings"], limit=1)
                raw_embeddings = sample.get("embeddings")
                if raw_embeddings is not None and len(raw_embeddings) > 0:
                    first_emb = raw_embeddings[0]
                    if len(first_emb) != expected_dim:
                        client.delete_collection("thinkbook_chunks")
                        collection = client.get_or_create_collection(
                            "thinkbook_chunks",
                            metadata={"hnsw:space": "cosine"},
                        )
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


def _combine_where_clauses(clauses: list[dict[str, Any]]) -> dict[str, Any]:
    if not clauses:
        return {}
    if len(clauses) == 1:
        return clauses[0]
    res = clauses[0]
    for c in clauses[1:]:
        res = {"$and": [res, c]}
    return res


def upsert_chunks(
    document_id: int,
    notebook_id: int,
    source_filename: str,
    file_type: str,
    chunks: list[dict],
    embeddings: list[list[float]],
    user_id: int | None = None,
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
                "user_id": user_id if user_id is not None else -1,
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
    if collection.count() == 0:
        return
    collection.delete(where={"document_id": document_id})


def delete_notebook(notebook_id: int) -> None:
    collection = get_collection()
    if collection.count() == 0:
        return
    collection.delete(where={"notebook_id": notebook_id})


def query(
    embedding: list[float],
    notebook_id: int,
    document_ids: list[int],
    top_k: int,
    user_id: int | None = None,
) -> dict[str, Any]:
    dim = len(embedding) if embedding else None
    collection = get_collection(expected_dim=dim)
    
    # Fast path for empty collection to avoid ValueError on some chromadb versions
    if collection.count() == 0:
        return {"ids": [[]], "distances": [[]], "metadatas": [[]], "documents": [[]]}

    clauses: list[dict[str, Any]] = [{"notebook_id": notebook_id}]
    if user_id is not None:
        clauses.append({"user_id": user_id})

    if document_ids:
        if len(document_ids) == 1:
            clauses.append({"document_id": document_ids[0]})
        else:
            clauses.append({"document_id": {"$in": document_ids}})

    where_clause = _combine_where_clauses(clauses)

    results = collection.query(
        query_embeddings=[embedding],
        n_results=top_k,
        where=where_clause,
    )

    return results
