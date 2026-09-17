from __future__ import annotations
"""
Deterministic, character-based chunking with overlap.

Character-based (not token-based) on purpose for this milestone: sizing
chunks precisely for Qwen3-Embedding-0.6B's tokenizer belongs with the
embedding integration itself, not here. `chunk_size_chars` is a rough,
easy-to-reason-about proxy in the meantime -- see app/config.py.

Strategy: paragraphs (text separated by a blank line) are greedily packed
into windows up to `chunk_size` characters. A paragraph too large to fit in
one window on its own is hard-split into fixed-size, overlapping windows,
since we don't have a sentence tokenizer to do better. Either way, every
window keeps `overlap` characters of trailing context from its predecessor.

Every chunk keeps the page_number/section_title of the ExtractedSection it
came from, and a chunk_index that is stable and sequential across the whole
document (not reset per page/section).
"""


import re

from app.services.ingestion.types import ChunkRecord, ExtractedDocument

_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n+")


def chunk_document(doc: ExtractedDocument, chunk_size: int, overlap: int) -> list[ChunkRecord]:
    overlap = min(overlap, max(chunk_size - 1, 0))  # defensive: overlap must be smaller than chunk_size

    records: list[ChunkRecord] = []
    chunk_index = 0

    for section in doc.sections:
        for window_text, char_start, char_end in _windows_for_section(section.text, chunk_size, overlap):
            if not window_text.strip():
                continue
            records.append(
                ChunkRecord(
                    chunk_index=chunk_index,
                    text=window_text,
                    page_number=section.page_number,
                    section=section.section_title,
                    char_start=char_start,
                    char_end=char_end,
                )
            )
            chunk_index += 1

    return records


def _windows_for_section(text: str, chunk_size: int, overlap: int) -> list[tuple[str, int, int]]:
    """Returns (window_text, char_start, char_end) tuples, offsets relative
    to this section's own text (not the whole document)."""
    text = text.strip()
    if not text:
        return []

    paragraphs = _paragraph_offsets(text)

    windows: list[tuple[str, int, int]] = []
    buffer_start: int | None = None
    buffer_end: int | None = None

    def flush():
        if buffer_start is not None:
            windows.append((text[buffer_start:buffer_end], buffer_start, buffer_end))

    for para_start, para_end in paragraphs:
        if para_end - para_start > chunk_size:
            # A single paragraph bigger than one window: flush what we have,
            # hard-split this paragraph on its own, then continue.
            flush()
            buffer_start = buffer_end = None
            windows.extend(_hard_split(text, para_start, para_end, chunk_size, overlap))
            continue

        if buffer_start is None:
            buffer_start, buffer_end = para_start, para_end
        elif para_end - buffer_start <= chunk_size:
            buffer_end = para_end
        else:
            flush()
            overlap_start = max(para_start - overlap, 0)
            buffer_start, buffer_end = overlap_start, para_end

    flush()
    return windows


def _paragraph_offsets(text: str) -> list[tuple[int, int]]:
    """Split `text` into (start, end) offsets for non-empty paragraphs,
    using blank lines as the separator. Falls back to the whole text as a
    single paragraph when there are no blank-line breaks."""
    offsets: list[tuple[int, int]] = []
    pos = 0
    for raw_para in _PARAGRAPH_SPLIT_RE.split(text):
        stripped = raw_para.strip()
        if not stripped:
            continue
        start = text.index(stripped, pos)
        end = start + len(stripped)
        offsets.append((start, end))
        pos = end
    return offsets


def _hard_split(text: str, start: int, end: int, chunk_size: int, overlap: int) -> list[tuple[str, int, int]]:
    """Fixed-size, overlapping windows over text[start:end], used when a
    single paragraph is too long to fit in one chunk on its own."""
    windows = []
    step = max(chunk_size - overlap, 1)
    pos = start
    while pos < end:
        window_end = min(pos + chunk_size, end)
        windows.append((text[pos:window_end], pos, window_end))
        if window_end >= end:
            break
        pos += step
    return windows

