from __future__ import annotations
"""
Ollama LLM integration service.

Handles communication with a local Ollama instance for text generation
and chat conversations using Qwen3 1.7B (or configured model).
"""

import logging
import time
from typing import Any, Optional, Union

import httpx

from app.config import get_settings
from app.models.chat import ChatMessage, ChatResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class OllamaUnavailable(Exception):
    """Raised when the Ollama server cannot be reached or times out."""


class LLMModelNotFound(Exception):
    """Raised when Ollama is reachable but the requested model is not installed."""


class LLMGenerationError(Exception):
    """Raised when Ollama returns an error during text generation."""


# ---------------------------------------------------------------------------
# Service Availability Check
# ---------------------------------------------------------------------------

async def ping() -> tuple[bool, str | None]:
    """Check whether the configured Ollama instance is reachable."""
    settings = get_settings()
    url = f"{settings.ollama_base_url.rstrip('/')}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            response.raise_for_status()
        return True, None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ollama ping failed: %s", exc)
        return False, str(exc)


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------

def _format_messages(
    messages: list[Union[ChatMessage, dict[str, Any]]],
    system_prompt: Optional[str] = None,
) -> list[dict[str, str]]:
    """Normalize input messages into Ollama wire format dicts."""
    formatted: list[dict[str, str]] = []

    # Insert system prompt first if provided and not already present
    if system_prompt and system_prompt.strip():
        has_system = any(
            (isinstance(m, ChatMessage) and m.role == "system")
            or (isinstance(m, dict) and m.get("role") == "system")
            for m in messages
        )
        if not has_system:
            formatted.append({"role": "system", "content": system_prompt.strip()})

    for msg in messages:
        if isinstance(msg, ChatMessage):
            formatted.append({"role": msg.role, "content": msg.content})
        elif isinstance(msg, dict):
            formatted.append({"role": str(msg.get("role", "user")), "content": str(msg.get("content", ""))})
        else:
            raise ValueError(f"Unsupported message type: {type(msg)}")

    return formatted


def _build_payload(
    formatted_messages: list[dict[str, str]],
    model: str,
    temperature: float,
) -> dict[str, Any]:
    return {
        "model": model,
        "messages": formatted_messages,
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }


def _parse_chat_response(data: dict[str, Any], default_model: str) -> ChatResponse:
    raw_message = data.get("message")
    if not isinstance(raw_message, dict) or "content" not in raw_message:
        raise LLMGenerationError(f"Unexpected response structure from Ollama: {data!r}")

    content = raw_message.get("content", "")
    role = raw_message.get("role", "assistant")
    model_name = data.get("model", default_model)

    return ChatResponse(
        model=model_name,
        message=ChatMessage(role=role, content=content),
        response=content,
        done=data.get("done", True),
        total_duration=data.get("total_duration"),
        prompt_eval_count=data.get("prompt_eval_count"),
        eval_count=data.get("eval_count"),
    )


# ---------------------------------------------------------------------------
# Asynchronous Public API
# ---------------------------------------------------------------------------

async def chat(
    messages: list[Union[ChatMessage, dict[str, Any]]],
    *,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    timeout: Optional[float] = None,
) -> ChatResponse:
    """Send a conversation to Ollama /api/chat asynchronously and return structured ChatResponse.

    Raises:
        OllamaUnavailable: If Ollama cannot be reached or times out.
        LLMModelNotFound: If the requested model is not installed.
        LLMGenerationError: If Ollama returns an HTTP error or unexpected payload.
    """
    settings = get_settings()
    target_model = model or settings.ollama_model
    req_timeout = timeout if timeout is not None else settings.ollama_timeout_seconds
    base_url = settings.ollama_base_url.rstrip("/")
    url = f"{base_url}/api/chat"

    formatted_messages = _format_messages(messages, system_prompt=system_prompt)
    payload = _build_payload(formatted_messages, target_model, temperature)

    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=req_timeout) as client:
            response = await client.post(url, json=payload)
    except httpx.ConnectError as exc:
        raise OllamaUnavailable(
            f"Cannot reach Ollama at {base_url}. Make sure Ollama is running: `ollama serve`"
        ) from exc
    except httpx.TimeoutException as exc:
        raise OllamaUnavailable(
            f"Ollama at {base_url} timed out after {req_timeout:.1f}s. "
            "The model may still be loading or generating — try again in a moment."
        ) from exc

    if response.status_code == 404:
        raise LLMModelNotFound(
            f"LLM model '{target_model}' is not available in Ollama. "
            f"Pull it with: `ollama pull {target_model}`"
        )

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise LLMGenerationError(
            f"Ollama returned HTTP {response.status_code}: {response.text}"
        ) from exc

    try:
        data = response.json()
    except Exception as exc:
        raise LLMGenerationError(f"Failed to parse Ollama JSON response: {response.text}") from exc

    chat_resp = _parse_chat_response(data, default_model=target_model)
    elapsed = time.monotonic() - t0
    logger.info("Generated chat response in %.2fs (model=%s, tokens=%s)", elapsed, target_model, chat_resp.eval_count)
    return chat_resp


async def generate(
    prompt: str,
    *,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    timeout: Optional[float] = None,
) -> str:
    """Helper to send a single text prompt and return the assistant response string."""
    msg = ChatMessage(role="user", content=prompt)
    chat_resp = await chat(
        [msg],
        model=model,
        system_prompt=system_prompt,
        temperature=temperature,
        timeout=timeout,
    )
    return chat_resp.response


# ---------------------------------------------------------------------------
# Synchronous Public API (convenience for non-async contexts)
# ---------------------------------------------------------------------------

def chat_sync(
    messages: list[Union[ChatMessage, dict[str, Any]]],
    *,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    timeout: Optional[float] = None,
) -> ChatResponse:
    """Synchronous version of chat()."""
    settings = get_settings()
    target_model = model or settings.ollama_model
    req_timeout = timeout if timeout is not None else settings.ollama_timeout_seconds
    base_url = settings.ollama_base_url.rstrip("/")
    url = f"{base_url}/api/chat"

    formatted_messages = _format_messages(messages, system_prompt=system_prompt)
    payload = _build_payload(formatted_messages, target_model, temperature)

    t0 = time.monotonic()
    try:
        with httpx.Client(timeout=req_timeout) as client:
            response = client.post(url, json=payload)
    except httpx.ConnectError as exc:
        raise OllamaUnavailable(
            f"Cannot reach Ollama at {base_url}. Make sure Ollama is running: `ollama serve`"
        ) from exc
    except httpx.TimeoutException as exc:
        raise OllamaUnavailable(
            f"Ollama at {base_url} timed out after {req_timeout:.1f}s. "
            "The model may still be loading or generating — try again in a moment."
        ) from exc

    if response.status_code == 404:
        raise LLMModelNotFound(
            f"LLM model '{target_model}' is not available in Ollama. "
            f"Pull it with: `ollama pull {target_model}`"
        )

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise LLMGenerationError(
            f"Ollama returned HTTP {response.status_code}: {response.text}"
        ) from exc

    try:
        data = response.json()
    except Exception as exc:
        raise LLMGenerationError(f"Failed to parse Ollama JSON response: {response.text}") from exc

    chat_resp = _parse_chat_response(data, default_model=target_model)
    elapsed = time.monotonic() - t0
    logger.info("Generated sync chat response in %.2fs (model=%s, tokens=%s)", elapsed, target_model, chat_resp.eval_count)
    return chat_resp


def generate_sync(
    prompt: str,
    *,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    timeout: Optional[float] = None,
) -> str:
    """Synchronous version of generate()."""
    msg = ChatMessage(role="user", content=prompt)
    chat_resp = chat_sync(
        [msg],
        model=model,
        system_prompt=system_prompt,
        temperature=temperature,
        timeout=timeout,
    )
    return chat_resp.response
