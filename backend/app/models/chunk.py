from __future__ import annotations
from datetime import datetime

from pydantic import BaseModel


class Chunk(BaseModel):
    """Row shape for the `chunks` table; also used directly as an API response.

    Every field here (besides `text` and `id`s) is provenance metadata --
    what a future citation feature needs to answer "where did this text
    come from?". Fields are nullable because not every source format has
    every kind of location info (e.g. TXT has no page_number).
    """

    id: int
    document_id: int
    chunk_index: int
    text: str
    page_number: int | None
    section: str | None
    char_start: int | None
    char_end: int | None
    created_at: datetime

