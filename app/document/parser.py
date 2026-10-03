"""Document Parser for extracting text, sections, headings, and tables across formats."""

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple
import pymupdf
import docx

from app.document.table_extractor import TableExtractor
from app.models.schemas import ExtractedTable
from app.utils.logging import logger


class ParsedPage:
    """Represents the parsed textual and structural content of a single page."""
    def __init__(self, page_number: int, text: str, sections: List[Dict[str, str]], tables: List[ExtractedTable]):
        self.page_number = page_number
        self.text = text
        self.sections = sections  # list of {"heading": str, "content": str}
        self.tables = tables


class DocumentParser:
    """Parses PDF, DOCX, TXT, CSV, and XLSX documents."""

    @classmethod
    def parse(cls, file_path: Path, doc_id: str) -> Tuple[List[ParsedPage], List[ExtractedTable], Dict[str, Any]]:
        """Main entry point to parse a document into structured pages, tables, and metadata."""
        ext = file_path.suffix.lower()
        if ext == ".pdf":
            return cls._parse_pdf(file_path, doc_id)
        elif ext == ".docx":
            return cls._parse_docx(file_path, doc_id)
        elif ext == ".txt":
            return cls._parse_txt(file_path, doc_id)
        elif ext == ".csv":
            return cls._parse_csv(file_path, doc_id)
        elif ext == ".xlsx":
            return cls._parse_xlsx(file_path, doc_id)
        else:
            raise ValueError(f"Unsupported format: {ext}")

    @classmethod
    def _parse_pdf(cls, file_path: Path, doc_id: str) -> Tuple[List[ParsedPage], List[ExtractedTable], Dict[str, Any]]:
        pages: List[ParsedPage] = []
        all_tables: List[ExtractedTable] = []
        doc_meta: Dict[str, Any] = {"title": file_path.stem}

        try:
            doc = pymupdf.open(file_path)
            meta = doc.metadata or {}
            if meta.get("title"):
                doc_meta["title"] = meta["title"]

            for page_idx in range(len(doc)):
                page = doc[page_idx]
                page_num = page_idx + 1
                text = page.get_text("text") or ""

                # Extract tables on this page
                tables = TableExtractor.extract_from_pdf_page(page, doc_id, file_path.name, page_num)
                all_tables.extend(tables)

                # Identify sections by headings
                sections = cls._identify_sections(text)
                pages.append(ParsedPage(page_number=page_num, text=text, sections=sections, tables=tables))

            doc.close()
        except Exception as e:
            logger.error(f"Error parsing PDF {file_path.name}: {e}")
            raise

        return pages, all_tables, doc_meta

    @classmethod
    def _parse_docx(cls, file_path: Path, doc_id: str) -> Tuple[List[ParsedPage], List[ExtractedTable], Dict[str, Any]]:
        pages: List[ParsedPage] = []
        all_tables: List[ExtractedTable] = []
        doc_meta: Dict[str, Any] = {"title": file_path.stem}

        try:
            doc = docx.Document(file_path)
            full_text_paragraphs = []
            sections = []
            current_heading = "Introduction"
            current_buffer = []

            for p in doc.paragraphs:
                p_text = p.text.strip()
                if not p_text:
                    continue

                if p.style and p.style.name.startswith("Heading"):
                    if current_buffer:
                        sections.append({"heading": current_heading, "content": "\n".join(current_buffer)})
                        current_buffer = []
                    current_heading = p_text
                else:
                    current_buffer.append(p_text)
                full_text_paragraphs.append(p_text)

            if current_buffer:
                sections.append({"heading": current_heading, "content": "\n".join(current_buffer)})

            # Extract docx tables
            for idx, table in enumerate(doc.tables):
                headers = [cell.text.strip() for cell in table.rows[0].cells]
                rows = []
                for row in table.rows[1:]:
                    r_data = [cell.text.strip() for cell in row.cells]
                    if any(r_data):
                        rows.append(r_data)
                
                if headers and rows:
                    all_tables.append(
                        ExtractedTable(
                            table_id=f"tab_{doc_id}_1_{idx+1}",
                            document_id=doc_id,
                            filename=file_path.name,
                            page=1,
                            title=f"Table {idx+1}",
                            headers=headers,
                            rows=rows,
                            structured_data=[dict(zip(headers, r)) for r in rows],
                        )
                    )

            # Paginate approximately 500 words per page
            full_text = "\n\n".join(full_text_paragraphs)
            pages.append(ParsedPage(page_number=1, text=full_text, sections=sections, tables=all_tables))

        except Exception as e:
            logger.error(f"Error parsing DOCX {file_path.name}: {e}")
            raise

        return pages, all_tables, doc_meta

    @classmethod
    def _parse_txt(cls, file_path: Path, doc_id: str) -> Tuple[List[ParsedPage], List[ExtractedTable], Dict[str, Any]]:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        sections = cls._identify_sections(text)
        page = ParsedPage(page_number=1, text=text, sections=sections, tables=[])
        return [page], [], {"title": file_path.stem}

    @classmethod
    def _parse_csv(cls, file_path: Path, doc_id: str) -> Tuple[List[ParsedPage], List[ExtractedTable], Dict[str, Any]]:
        tables = TableExtractor.extract_from_csv(file_path, doc_id)
        text_repr = f"Spreadsheet data from {file_path.name}:\n"
        if tables and tables[0].rows:
            text_repr += f"Headers: {', '.join(tables[0].headers)}\n"
            text_repr += f"Sample rows ({len(tables[0].rows)} total rows):\n"
            for r in tables[0].rows[:10]:
                text_repr += " | ".join(r) + "\n"
        page = ParsedPage(page_number=1, text=text_repr, sections=[{"heading": "Table", "content": text_repr}], tables=tables)
        return [page], tables, {"title": file_path.stem}

    @classmethod
    def _parse_xlsx(cls, file_path: Path, doc_id: str) -> Tuple[List[ParsedPage], List[ExtractedTable], Dict[str, Any]]:
        tables = TableExtractor.extract_from_excel(file_path, doc_id)
        text_repr = f"Workbook data from {file_path.name}:\n"
        for t in tables:
            text_repr += f"\n--- {t.title} ---\nHeaders: {', '.join(t.headers)}\nRows count: {len(t.rows)}\n"
        page = ParsedPage(page_number=1, text=text_repr, sections=[{"heading": "Workbook", "content": text_repr}], tables=tables)
        return [page], tables, {"title": file_path.stem}

    @classmethod
    def _identify_sections(cls, text: str) -> List[Dict[str, str]]:
        """Heuristic section/heading detector based on casing, colon endings, and markdown tags."""
        lines = text.split("\n")
        sections: List[Dict[str, str]] = []
        current_heading = "General"
        current_lines: List[str] = []

        heading_pattern = re.compile(r"^([A-Z0-9\s\.\-]{3,60}:?|#+\s+.+|[0-9]+\.[0-9]*\s+[A-Z].+)$")

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Check if this line looks like a section header
            is_heading = False
            if len(stripped) <= 70:
                if stripped.isupper() and len(stripped) > 3:
                    is_heading = True
                elif heading_pattern.match(stripped):
                    is_heading = True
                elif stripped.endswith(":") and len(stripped.split()) <= 6:
                    is_heading = True

            if is_heading:
                if current_lines:
                    sections.append({"heading": current_heading, "content": " ".join(current_lines)})
                    current_lines = []
                current_heading = stripped.rstrip(":")
            else:
                current_lines.append(stripped)

        if current_lines:
            sections.append({"heading": current_heading, "content": " ".join(current_lines)})

        return sections or [{"heading": "General", "content": text}]
