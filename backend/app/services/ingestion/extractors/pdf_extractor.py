from __future__ import annotations
from pathlib import Path

from pypdf import PdfReader

from app.services.ingestion.types import ExtractedDocument, ExtractedSection, ExtractionError


def extract(path: Path, source_filename: str) -> ExtractedDocument:
    try:
        reader = PdfReader(str(path))
    except Exception as exc:  # noqa: BLE001 - pypdf raises several exception types for a bad/corrupt file
        raise ExtractionError(f"Could not open '{source_filename}' as a PDF.") from exc

    if reader.is_encrypted:
        raise ExtractionError(f"'{source_filename}' is password-protected and can't be read.")

    page_count = len(reader.pages)
    sections: list[ExtractedSection] = []

    for index, page in enumerate(reader.pages):
        try:
            text = (page.extract_text() or "").strip()
        except Exception as exc:  # noqa: BLE001 - a single malformed page shouldn't fail the whole document
            raise ExtractionError(f"Failed to extract text from page {index + 1} of '{source_filename}'.") from exc

        if text:
            sections.append(
                ExtractedSection(
                    section_order=index,
                    page_number=index + 1,
                    section_title=None,
                    text=text,
                )
            )

    if not sections:
        # Most likely a scanned/image-only PDF. OCR is explicitly out of
        # scope for this milestone, so we reject cleanly instead of
        # silently producing an empty document.
        raise ExtractionError(
            f"'{source_filename}' has no extractable text (it may be a scanned/image-only PDF, "
            "which isn't supported yet)."
        )

    return ExtractedDocument(source_filename=source_filename, sections=sections, page_count=page_count)

