from __future__ import annotations
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ProcessingStatus = Literal["pending", "processing", "completed", "failed"]
IndexingStatus = Literal["pending", "indexing", "indexed", "failed"]
FileType = Literal["pdf", "docx", "txt"]


class Document(BaseModel):
    """Row shape for the `documents` table; also used directly as an API response.

    Deliberately excludes `stored_filename` -- that's an internal storage
    detail, never exposed to clients.
    """

    id: int
    notebook_id: int
    original_filename: str
    file_type: FileType
    file_size: int
    page_count: int | None
    processing_status: ProcessingStatus
    error_message: str | None
    indexing_status: IndexingStatus
    indexing_error: str | None
    created_at: datetime
    updated_at: datetime


class DocumentUploadResult(BaseModel):
    """Returned right after an upload finishes processing (this milestone is synchronous)."""

    document: Document
    chunk_count: int

