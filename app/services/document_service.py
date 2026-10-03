"""Document ingestion and orchestration of evidence-based document services."""

import uuid
from pathlib import Path
from typing import Optional, Tuple

from app.document.chunker import HierarchicalChunker
from app.document.loader import DocumentLoader
from app.document.metadata import registry
from app.document.parser import DocumentParser
from app.models.schemas import DocumentMetadata, DocumentSummary, CompareResponse
from app.rag.vector_store import vector_store
from app.services.evidence_service import compare_documents, summarize_document
from app.utils.logging import logger


class DocumentService:
    """Coordinates parsing, indexing, classification, and supported analysis."""

    def __init__(self):
        self.chunker = HierarchicalChunker()

    def ingest_document(self, file_path: Path, original_filename: Optional[str] = None) -> Tuple[DocumentMetadata, DocumentSummary]:
        filename = original_filename or file_path.name
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        valid, message = DocumentLoader.validate_file(file_path)
        if not valid:
            raise ValueError(f"File validation failed: {message}")

        pages, tables, parsed_metadata = DocumentParser.parse(file_path, doc_id)
        if not pages or not any((page.text or "").strip() for page in pages):
            raise ValueError(f"No readable text could be extracted from {filename}.")

        chunks = self.chunker.chunk_document(doc_id=doc_id, filename=filename, pages=pages)
        if not chunks:
            raise ValueError(f"No searchable text could be extracted from {filename}.")
        vector_store.add_chunks(chunks)

        full_text = "\n".join(page.text for page in pages)
        from app.agents.classifier_agent import classifier_agent
        classification = classifier_agent.classify_document(full_text, filename)

        metadata = DocumentMetadata(
            document_id=doc_id,
            filename=filename,
            file_type=file_path.suffix.lower(),
            file_size_bytes=file_path.stat().st_size,
            num_pages=len(pages),
            num_chunks=len(chunks),
            num_tables=len(tables),
            title=parsed_metadata.get("title") or file_path.stem,
            document_type=classification["document_type"],
            domain=classification["domain"],
            classification_confidence=classification["confidence"],
            storage_filename=file_path.name,
        )
        registry.register(metadata)
        summary = self.generate_document_summary(doc_id, filename, metadata.document_type, pages, tables)
        logger.info(
            "Ingested document %s ('%s'): %s pages, %s chunks, type=%s",
            doc_id, filename, len(pages), len(chunks), metadata.document_type,
        )
        return metadata, summary

    def generate_document_summary(
        self, doc_id: str, filename: str, doc_type: str, pages: list, tables: list
    ) -> DocumentSummary:
        """Persists a summary whose factual fields are extracted from the parsed document."""
        summary = summarize_document(doc_id, filename, doc_type, pages, tables)
        from app.utils.config import settings
        summary_path = settings.PROCESSED_DIR / f"{doc_id}_summary.json"
        summary_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
        return summary

    def compare_documents(self, doc1_id: str, doc2_id: str) -> CompareResponse:
        return compare_documents(doc1_id, doc2_id)


document_service = DocumentService()
