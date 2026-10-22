from __future__ import annotations
"""
Chat and text conversation API routes.

Provides a dedicated FastAPI endpoint for interactive conversations with the
configured local LLM (Qwen3 1.7B) via Ollama.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, verify_csrf
from app.models.chat import ChatMessage, ChatRequest, ChatResponse
from app.models.rag import RAGRequest, RAGResponse
from app.models.user import User
from app.repositories import notebooks as notebooks_repo
from app.services import db, llm, rag as rag_service
from app.services.embedding import EmbeddingModelNotFound, OllamaUnavailable as EmbeddingUnavailable

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse, dependencies=[Depends(verify_csrf)])
async def chat_conversation(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """Send a conversation turn or single prompt to the local LLM.

    Requires user authentication to ensure isolation and auditability.
    """
    if request.message and request.message.strip():
        messages = [ChatMessage(role="user", content=request.message.strip())]
    elif request.messages:
        messages = request.messages
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either 'message' or 'messages' must contain non-empty text.",
        )

    try:
        response = await llm.chat(
            messages=messages,
            model=request.model,
            system_prompt=request.system_prompt,
            temperature=request.temperature if request.temperature is not None else 0.7,
        )
        return response
    except llm.OllamaUnavailable as exc:
        logger.error("Ollama unavailable during chat request: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Ollama is not available: {exc}. Start Ollama with `ollama serve`.",
        ) from exc
    except llm.LLMModelNotFound as exc:
        logger.error("Requested LLM model not found in Ollama: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except llm.LLMGenerationError as exc:
        logger.error("LLM generation error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM generation failed: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error in chat endpoint: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error processing chat request.",
        ) from exc


@router.post("/rag", response_model=RAGResponse, dependencies=[Depends(verify_csrf)])
async def chat_rag(
    request: RAGRequest,
    current_user: User = Depends(get_current_user),
) -> RAGResponse:
    """Answer a question grounded in documents from a specific notebook."""
    pool = db.get_pool()
    with pool.connection() as conn:
        if not notebooks_repo.exists(conn, request.notebook_id, user_id=current_user.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notebook not found.",
            )

    try:
        response = await rag_service.answer(
            question=request.message,
            notebook_id=request.notebook_id,
            document_ids=request.document_ids,
            history=request.history,
            top_k=request.top_k,
            temperature=request.temperature,
            user_id=current_user.id,
            relevance_threshold=request.relevance_threshold,
        )
        return response
    except rag_service.RAGError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except (llm.OllamaUnavailable, EmbeddingUnavailable) as exc:
        logger.error("Ollama unavailable during RAG chat request: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Ollama is not available: {exc}. Start Ollama with `ollama serve`.",
        ) from exc
    except (llm.LLMModelNotFound, EmbeddingModelNotFound) as exc:
        logger.error("Model not found in Ollama during RAG chat request: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except llm.LLMGenerationError as exc:
        logger.error("LLM generation error during RAG chat request: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM generation failed: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error in RAG chat endpoint: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error processing RAG chat request.",
        ) from exc

