from __future__ import annotations
from pathlib import Path
from typing import Callable

from app.services.ingestion.extractors import docx_extractor, pdf_extractor, txt_extractor
from app.services.ingestion.types import ExtractedDocument

_EXTRACTORS: dict[str, Callable[[Path, str], ExtractedDocument]] = {
    "txt": txt_extractor.extract,
    "docx": docx_extractor.extract,
    "pdf": pdf_extractor.extract,
}


def extract(file_type: str, path: Path, source_filename: str) -> ExtractedDocument:
    try:
        extractor = _EXTRACTORS[file_type]
    except KeyError as exc:
        raise ValueError(f"No extractor registered for file type '{file_type}'.") from exc
    return extractor(path, source_filename)

