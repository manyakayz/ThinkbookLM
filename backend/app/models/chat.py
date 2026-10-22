from __future__ import annotations
"""
Pydantic models for the LLM chat and text conversation API.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator


class ChatMessage(BaseModel):
    """A single message in a conversation thread."""

    role: Literal["system", "user", "assistant"] = Field(
        default="user",
        description="Role of the message author: 'system', 'user', or 'assistant'.",
    )
    content: str = Field(..., min_length=1, description="Text content of the message.")


class ChatRequest(BaseModel):
    """Body for POST /chat conversation endpoint."""

    message: Optional[str] = Field(
        default=None,
        description="Single prompt or user turn. Can be used instead of 'messages'.",
    )
    messages: Optional[list[ChatMessage]] = Field(
        default=None,
        description="Full conversation history as a list of ChatMessage objects.",
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="Optional system prompt to steer model behavior or persona.",
    )
    model: Optional[str] = Field(
        default=None,
        description="Optional model identifier override. Defaults to OLLAMA_MODEL (e.g. qwen3:1.7b).",
    )
    temperature: Optional[float] = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature between 0.0 and 2.0.",
    )

    @model_validator(mode="after")
    def validate_has_content(self) -> ChatRequest:
        has_message = bool(self.message and self.message.strip())
        has_messages = bool(self.messages and len(self.messages) > 0)
        if not has_message and not has_messages:
            raise ValueError("Either 'message' or non-empty 'messages' must be provided.")
        return self


class ChatResponse(BaseModel):
    """Structured response from the LLM chat endpoint."""

    model: str = Field(..., description="The Ollama model identifier that generated the response.")
    message: ChatMessage = Field(..., description="The assistant's generated chat message.")
    response: str = Field(..., description="Direct text shortcut of the assistant's response.")
    done: bool = Field(default=True, description="Indicates whether generation completed.")
    total_duration: Optional[int] = Field(default=None, description="Total generation duration in nanoseconds.")
    prompt_eval_count: Optional[int] = Field(default=None, description="Number of tokens in the prompt.")
    eval_count: Optional[int] = Field(default=None, description="Number of generated output tokens.")
