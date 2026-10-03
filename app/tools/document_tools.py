"""Document inspection tools for page viewing, table extraction, and metadata retrieval."""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import pymupdf

from app.document.metadata import registry
from app.document.table_extractor import TableExtractor
from app.tools.base_tool import BaseTool, ToolResult, tool_registry
from app.utils.config import settings


class GetDocumentPageTool(BaseTool):
    """Retrieves full text and layout of an exact document page."""

    name = "get_document_page"
    description = "Fetches the full raw text content of a specific page within an uploaded document."
    parameters = {
        "document_id": "Unique document ID (str)",
        "page_number": "1-indexed page number (int)"
    }

    def execute(self, document_id: str, page_number: int, **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        meta = registry.get(document_id)
        if not meta:
            return ToolResult(success=False, data=None, error=f"Document ID '{document_id}' not found.")

        # Locate file in uploads or sample_docs
        file_path = settings.UPLOAD_DIR / Path(meta.storage_filename or meta.filename).name
        if not file_path.exists():
            file_path = settings.SAMPLE_DOCS_DIR / meta.filename

        if not file_path.exists():
            return ToolResult(success=False, data=None, error=f"Source file '{meta.filename}' not found on disk.")

        try:
            doc = pymupdf.open(file_path)
            if page_number < 1 or page_number > len(doc):
                doc.close()
                return ToolResult(success=False, data=None, error=f"Page {page_number} out of range (1-{len(doc)}).")

            page = doc[page_number - 1]
            text = page.get_text("text")
            doc.close()

            return ToolResult(
                success=True,
                data={"document_id": document_id, "filename": meta.filename, "page": page_number, "text": text},
                execution_time_ms=(time.perf_counter() - start_t) * 1000
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e), execution_time_ms=(time.perf_counter() - start_t) * 1000)


class ExtractTableTool(BaseTool):
    """Extracts structured tables from a specific document page."""

    name = "extract_table"
    description = "Extracts structured tabular data (headers, rows, dataframes) from a document page."
    parameters = {
        "document_id": "Unique document ID (str)",
        "page_number": "1-indexed page number (int, optional)"
    }

    def execute(self, document_id: str, page_number: Optional[int] = None, **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        meta = registry.get(document_id)
        if not meta:
            return ToolResult(success=False, data=None, error=f"Document ID '{document_id}' not found.")

        file_path = settings.UPLOAD_DIR / Path(meta.storage_filename or meta.filename).name
        if not file_path.exists():
            file_path = settings.SAMPLE_DOCS_DIR / meta.filename

        if not file_path.exists():
            return ToolResult(success=False, data=None, error=f"Source file '{meta.filename}' not found.")

        try:
            doc = pymupdf.open(file_path)
            tables = []
            target_pages = [page_number] if page_number is not None else list(range(1, len(doc) + 1))

            for p_num in target_pages:
                if 1 <= p_num <= len(doc):
                    page = doc[p_num - 1]
                    t_list = TableExtractor.extract_from_pdf_page(page, document_id, meta.filename, p_num)
                    tables.extend([t.model_dump() for t in t_list])

            doc.close()
            return ToolResult(success=True, data=tables, execution_time_ms=(time.perf_counter() - start_t) * 1000)
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e), execution_time_ms=(time.perf_counter() - start_t) * 1000)


class GetDocumentMetadataTool(BaseTool):
    """Retrieves document statistics and metadata."""

    name = "get_document_metadata"
    description = "Retrieves stored metadata, document type, domain, page count, and chunk count for a document."
    parameters = {
        "document_id": "Unique document ID (str)"
    }

    def execute(self, document_id: str, **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        meta = registry.get(document_id)
        if not meta:
            return ToolResult(success=False, data=None, error=f"Document ID '{document_id}' not found.")
        return ToolResult(success=True, data=meta.model_dump(), execution_time_ms=(time.perf_counter() - start_t) * 1000)


get_page_tool = GetDocumentPageTool()
extract_table_tool = ExtractTableTool()
get_meta_tool = GetDocumentMetadataTool()

tool_registry.register(get_page_tool)
tool_registry.register(extract_table_tool)
tool_registry.register(get_meta_tool)
