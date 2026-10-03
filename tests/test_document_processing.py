"""Test suite for Phase 1: Document Processing, Parsing, Table Extraction, and Chunking."""

from pathlib import Path
import pytest
from app.document.loader import DocumentLoader
from app.document.parser import DocumentParser
from app.document.chunker import HierarchicalChunker
from app.document.metadata import DocumentRegistry
from app.models.schemas import DocumentMetadata

SAMPLE_DIR = Path("data/sample_docs")


def test_loader_validation():
    sample_file = SAMPLE_DIR / "ApexCorp_Annual_Report_FY2024.pdf"
    assert sample_file.exists(), "Sample PDF must exist"
    
    valid, msg = DocumentLoader.validate_file(sample_file)
    assert valid is True
    assert msg == "Valid"

    # Test invalid extension
    invalid_file = Path("test_fake.exe")
    valid_inv, msg_inv = DocumentLoader.validate_file(invalid_file)
    assert valid_inv is False


def test_pdf_parsing_and_tables():
    sample_file = SAMPLE_DIR / "ApexCorp_Annual_Report_FY2024.pdf"
    pages, tables, meta = DocumentParser.parse(sample_file, "doc_test_01")
    
    assert len(pages) == 2, f"Expected 2 pages, got {len(pages)}"
    assert len(tables) >= 2, f"Expected at least 2 tables, got {len(tables)}"
    
    # Verify table headers
    t1 = tables[0]
    assert "Financial Metric" in t1.headers
    assert "Total Revenue" in [r[0] for r in t1.rows]


def test_hierarchical_chunking():
    sample_file = SAMPLE_DIR / "ApexCorp_Annual_Report_FY2024.pdf"
    pages, tables, meta = DocumentParser.parse(sample_file, "doc_test_01")
    
    chunker = HierarchicalChunker(chunk_size=400, chunk_overlap=80)
    chunks = chunker.chunk_document("doc_test_01", sample_file.name, pages)
    
    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.document_id == "doc_test_01"
        assert chunk.filename == sample_file.name
        assert chunk.page in [1, 2]
        assert len(chunk.text) > 0


def test_document_registry():
    reg = DocumentRegistry(Path("data/processed/test_registry.json"))
    meta = DocumentMetadata(
        document_id="doc_test_reg",
        filename="ApexCorp_Annual_Report_FY2024.pdf",
        file_type=".pdf",
        file_size_bytes=1024,
        num_pages=2,
        num_chunks=5,
        num_tables=2,
        document_type="Financial",
        domain="Finance"
    )
    reg.register(meta)
    retrieved = reg.get("doc_test_reg")
    assert retrieved is not None
    assert retrieved.filename == "ApexCorp_Annual_Report_FY2024.pdf"
    reg.delete("doc_test_reg")
    assert reg.get("doc_test_reg") is None


if __name__ == "__main__":
    test_loader_validation()
    test_pdf_parsing_and_tables()
    test_hierarchical_chunking()
    test_document_registry()
    print("ALL PHASE 1 DOCUMENT PROCESSING TESTS PASSED!")
