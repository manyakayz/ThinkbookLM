from __future__ import annotations
from pathlib import Path

from app.services.ingestion.types import ExtractedDocument, ExtractedSection, ExtractionError


def extract(path: Path, source_filename: str) -> ExtractedDocument:
    raw = path.read_bytes()

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        # Best-effort fallback for text files saved with a legacy encoding,
        # rather than failing the whole upload over an encoding mismatch.
        try:
            text = raw.decode("latin-1")
        except UnicodeDecodeError as exc:
            raise ExtractionError(f"Could not decode '{source_filename}' as text.") from exc

    text = text.strip()
    if not text:
        raise ExtractionError(f"'{source_filename}' has no readable text content.")

    section = ExtractedSection(
        section_order=0,
        page_number=None,
        section_title=None,
        text=text,
    )
    return ExtractedDocument(source_filename=source_filename, sections=[section], page_count=None)

