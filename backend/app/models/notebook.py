from __future__ import annotations
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class NotebookCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Notebook name cannot be blank.")
        return stripped


class Notebook(BaseModel):
    """Row shape for the `notebooks` table; also used directly as an API response."""

    id: int
    name: str
    created_at: datetime
    updated_at: datetime
    document_count: int = 0

