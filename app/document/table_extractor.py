"""Table extraction from documents and conversion to structured DataFrames."""

import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
import pymupdf

from app.models.schemas import ExtractedTable
from app.utils.logging import logger


class TableExtractor:
    """Extracts tables from PDF pages, CSVs, and Excel files into structured schemas."""

    @staticmethod
    def extract_from_pdf_page(page: pymupdf.Page, doc_id: str, filename: str, page_num: int) -> List[ExtractedTable]:
        """Extracts tables from a single PyMuPDF PDF page."""
        extracted: List[ExtractedTable] = []
        try:
            tabs = page.find_tables()
            for idx, tab in enumerate(tabs):
                raw_table = tab.extract()
                if not raw_table or len(raw_table) < 2:
                    continue

                # Header is first row, remaining are data rows
                raw_headers = raw_table[0]
                headers = [str(h).strip() if h is not None else f"Col_{i}" for i, h in enumerate(raw_headers)]
                
                rows: List[List[str]] = []
                for r in raw_table[1:]:
                    cleaned_row = [str(cell).strip() if cell is not None else "" for cell in r]
                    # Filter out completely empty rows
                    if any(cleaned_row):
                        rows.append(cleaned_row)

                if not rows:
                    continue

                # Convert to structured list of dicts via pandas
                structured_data: List[Dict[str, Any]] = []
                try:
                    df = pd.DataFrame(rows, columns=headers)
                    structured_data = df.to_dict(orient="records")
                except Exception:
                    pass

                table_obj = ExtractedTable(
                    table_id=f"tab_{doc_id}_{page_num}_{idx+1}",
                    document_id=doc_id,
                    filename=filename,
                    page=page_num,
                    title=f"Table on Page {page_num} (#{idx+1})",
                    headers=headers,
                    rows=rows,
                    structured_data=structured_data,
                )
                extracted.append(table_obj)
        except Exception as e:
            logger.debug(f"Table extraction on page {page_num} of {filename}: {e}")

        return extracted

    @staticmethod
    def extract_from_csv(file_path: Path, doc_id: str) -> List[ExtractedTable]:
        """Extracts table from CSV file."""
        try:
            df = pd.read_csv(file_path)
            headers = [str(c) for c in df.columns]
            rows = df.astype(str).values.tolist()
            return [
                ExtractedTable(
                    table_id=f"tab_{doc_id}_1_1",
                    document_id=doc_id,
                    filename=file_path.name,
                    page=1,
                    title=f"Spreadsheet Data ({file_path.name})",
                    headers=headers,
                    rows=rows,
                    structured_data=df.to_dict(orient="records"),
                )
            ]
        except Exception as e:
            logger.error(f"Error parsing CSV {file_path.name}: {e}")
            return []

    @staticmethod
    def extract_from_excel(file_path: Path, doc_id: str) -> List[ExtractedTable]:
        """Extracts tables from Excel sheets."""
        try:
            tables = []
            with pd.ExcelFile(file_path) as xls:
                for sheet_idx, sheet_name in enumerate(xls.sheet_names):
                    df = pd.read_excel(xls, sheet_name=sheet_name)
                    headers = [str(c) for c in df.columns]
                    rows = df.astype(str).values.tolist()
                    tables.append(
                        ExtractedTable(
                            table_id=f"tab_{doc_id}_{sheet_idx+1}_1",
                            document_id=doc_id,
                            filename=file_path.name,
                            page=sheet_idx + 1,
                            title=f"Sheet: {sheet_name}",
                            headers=headers,
                            rows=rows,
                            structured_data=df.to_dict(orient="records"),
                        )
                    )
            return tables
        except Exception as e:
            logger.error(f"Error parsing Excel {file_path.name}: {e}")
            return []
