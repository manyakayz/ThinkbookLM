from __future__ import annotations
"""
Internal representation shared by every extractor and by the chunker.

Extractors turn a source file into an `ExtractedDocument`: an ordered list
of `ExtractedSection`s, each just a piece of text plus where it came from
(page number and/or a section/heading label -- whichever the format has).
The chunker then only has to deal with this one shape, regardless of
whether the source was a PDF, DOCX, or TXT file.
"""


from dataclasses import dataclass


@dataclass
class ExtractedSection:
    # 0-indexed position of this section within the document, used only to
    # keep sections in original order -- not stored anywhere.
    section_order: int
    # 1-indexed page number, when the format has real pages (PDF). None
    # otherwise (DOCX, TXT).
    page_number: int | None
    # A human-readable section label, when the format has one (e.g. a DOCX
    # heading the text falls under). None otherwise.
    section_title: str | None
    text: str


@dataclass
class ExtractedDocument:
    source_filename: str
    sections: list[ExtractedSection]
    # Total page count, when known (PDF). Stored on the document row.
    page_count: int | None


@dataclass
class ChunkRecord:
    chunk_index: int
    text: str
    page_number: int | None
    section: str | None
    char_start: int | None
    char_end: int | None

    def as_dict(self) -> dict:
        return {
            "chunk_index": self.chunk_index,
            "text": self.text,
            "page_number": self.page_number,
            "section": self.section,
            "char_start": self.char_start,
            "char_end": self.char_end,
        }


class ExtractionError(Exception):
    """Raised by an extractor when a file can't be parsed. Caught by the
    pipeline and turned into a `failed` document status with this message."""

