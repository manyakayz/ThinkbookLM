import pytest
from pathlib import Path
import os
from app.services.ingestion.chunker import chunk_document, _windows_for_section
from app.services.ingestion.types import ExtractedDocument, ExtractedSection
from app.services.storage import validate_upload, UnsupportedFileType, FileTooLarge, EmptyFile
from app.services.ingestion.extractors import txt_extractor

def test_file_size_validation():
    # Empty file
    with pytest.raises(EmptyFile):
        validate_upload("test.txt", 0)
    
    # Too large file
    with pytest.raises(FileTooLarge):
        validate_upload("test.txt", 100 * 1024 * 1024) # 100MB

def test_unsupported_file_type():
    with pytest.raises(UnsupportedFileType):
        validate_upload("image.jpg", 1024)

def test_valid_upload():
    assert validate_upload("document.pdf", 1024) == "pdf"
    assert validate_upload("notes.TXT", 1024) == "txt"

def test_chunking_and_ordering():
    section = ExtractedSection(
        section_order=0,
        page_number=1,
        section_title="Introduction",
        text="This is a test paragraph.\n\nIt has multiple lines.\n\nAnd we want to chunk it."
    )
    doc = ExtractedDocument(source_filename="test.txt", sections=[section], page_count=1)
    
    # Small chunk size to force multiple chunks
    chunks = chunk_document(doc, chunk_size=30, overlap=5)
    
    assert len(chunks) > 0
    # Check ordering
    for i in range(len(chunks)):
        assert chunks[i].chunk_index == i
        assert chunks[i].page_number == 1
        assert chunks[i].section == "Introduction"

def test_chunk_metadata_provenance():
    section1 = ExtractedSection(section_order=0, page_number=1, section_title="S1", text="First page content")
    section2 = ExtractedSection(section_order=1, page_number=2, section_title="S2", text="Second page content")
    
    doc = ExtractedDocument(source_filename="test.pdf", sections=[section1, section2], page_count=2)
    chunks = chunk_document(doc, chunk_size=1000, overlap=100)
    
    assert len(chunks) == 2
    assert chunks[0].page_number == 1
    assert chunks[0].section == "S1"
    assert chunks[1].page_number == 2
    assert chunks[1].section == "S2"
    assert chunks[0].text == "First page content"
    assert chunks[1].text == "Second page content"

def test_txt_extraction(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello World!\n\nThis is a test.")
    
    doc = txt_extractor.extract(test_file, "test.txt")
    assert doc.source_filename == "test.txt"
    assert len(doc.sections) == 1
    assert doc.sections[0].text.replace('\r\n', '\n') == "Hello World!\n\nThis is a test."
    assert doc.sections[0].page_number is None

def test_invalid_document_handling():
    # Test handling of an invalid extraction
    with pytest.raises(Exception):
        from app.services.ingestion.extractors import pdf_extractor
        # Extracting a non-existent or corrupted file
        pdf_extractor.extract(Path("non_existent.pdf"), "non_existent.pdf")
