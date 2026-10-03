"""Extractive document summaries and evidence-backed comparisons."""

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.document.metadata import registry
from app.models.schemas import (
    ComparisonMetric,
    CompareResponse,
    DocumentSummary,
    SourceCitation,
)
from app.rag.vector_store import vector_store


def _sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [re.sub(r"\s+", " ", part).strip(" •\t") for part in parts if len(part.strip()) > 30]


def summarize_document(doc_id: str, filename: str, doc_type: str, pages: list, tables: list) -> DocumentSummary:
    """Builds an extractive summary from parsed text without generating document claims."""
    full_text = "\n".join(getattr(page, "text", "") or "" for page in pages)
    sentences = _sentences(full_text)
    key_facts = list(dict.fromkeys(sentences))[:6]
    executive_summary = " ".join(key_facts[:3]) if key_facts else "No readable text was extracted from this document."

    organizations = list(dict.fromkeys(re.findall(
        r"\b[A-Z][A-Za-z0-9&.-]*(?:\s+[A-Z][A-Za-z0-9&.-]*){0,3}\s+(?:Inc\.?|LLC|Ltd\.?|Limited|Corporation|Corp\.?|University|Institute)\b",
        full_text,
    )))[:8]
    amounts = list(dict.fromkeys(re.findall(
        r"(?:INR|USD|EUR|GBP|₹|\$|€|£)\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:Cr|Crore|Lakh|M|B|million|billion))?",
        full_text,
        flags=re.IGNORECASE,
    )))[:10]
    dates = list(dict.fromkeys(re.findall(
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}|\bFY\s?\d{4}\b",
        full_text,
        flags=re.IGNORECASE,
    )))[:8]
    topics = list(dict.fromkeys(
        section.get("heading", "").strip()
        for page in pages for section in getattr(page, "sections", [])
        if section.get("heading", "").strip() and section.get("heading", "").strip().lower() != "general"
    ))[:10]
    risk_terms = re.compile(r"\b(risk|threat|liabilit\w*|penalt\w*|vulnerabilit\w*|exposure|uncertain\w*|may result|subject to)\b", re.I)
    risks = list(dict.fromkeys(sentence for sentence in sentences if risk_terms.search(sentence)))[:8]
    questions = [
        "What are the main points in this document?",
        "Which figures, dates, or named entities does it contain?",
        "What risks or limitations are explicitly mentioned?",
    ] if full_text.strip() else []

    return DocumentSummary(
        document_id=doc_id,
        filename=filename,
        document_type=doc_type,
        executive_summary=executive_summary,
        key_facts=key_facts,
        key_entities={"Organizations": organizations, "Amounts": amounts, "Dates / Periods": dates},
        key_topics=topics,
        important_findings=key_facts[3:6],
        potential_risks=risks,
        suggested_questions=questions,
    )


METRIC_LABELS = {
    "Revenue": ("total revenue", "revenue", "turnover", "net sales"),
    "Operating expenses": ("operating expenses", "total expenses", "expenses"),
    "Net profit": ("net profit", "profit after tax", "pat", "net income"),
    "EBITDA": ("ebitda",),
    "Total debt": ("total debt", "debt"),
    "Total assets": ("total assets", "assets"),
    "Total liabilities": ("total liabilities", "liabilities"),
    "Employees": ("employees", "headcount", "staff count"),
}


def _metric_evidence(chunks: Iterable[Dict[str, Any]]) -> Dict[str, Tuple[float, str, Dict[str, Any]]]:
    found: Dict[str, Tuple[float, str, Dict[str, Any]]] = {}
    amount_pattern = re.compile(
        r"(?<![A-Za-z])(?:₹|\$|€|£|INR\s*|USD\s*)?\s*(-?\d[\d,]*(?:\.\d+)?)\s*(%|Cr\b|Crore\b|Lakh\b|million\b|billion\b)?",
        re.I,
    )
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for chunk in chunks:
        grouped.setdefault(str(chunk.get("document_id", "")), []).append(chunk)

    for document_chunks in grouped.values():
        for chunk in document_chunks:
            text = str(chunk.get("text", ""))
            sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip()]
            for label, aliases in METRIC_LABELS.items():
                if label in found:
                    continue
                for sentence in sentences:
                    match = next((re.search(rf"\b{re.escape(alias)}\b", sentence, re.I) for alias in aliases if re.search(rf"\b{re.escape(alias)}\b", sentence, re.I)), None)
                    if not match:
                        continue
                    window = sentence[match.end():]
                    window = re.sub(r"\b(?:FY\s?)?(?:19|20)\d{2}\b", " ", window, flags=re.I)
                    numbers = [item.group(1) for item in amount_pattern.finditer(window) if item.group(2) != "%"]
                    if not numbers:
                        continue
                    try:
                        # Keep the later amount only when the source explicitly
                        # states a change from one value to another.
                        use_second = len(numbers) > 1 and re.search(r"\bfrom\b.+\bto\b", window, re.I | re.S)
                        value = float(numbers[1 if use_second else 0].replace(",", ""))
                    except ValueError:
                        continue
                    found[label] = (value, sentence[:1000], chunk)
                    break
    return found


def compare_documents(doc1_id: str, doc2_id: str) -> CompareResponse:
    """Compares only matched values actually extracted from each document's indexed text."""
    first = registry.get(doc1_id)
    second = registry.get(doc2_id)
    if not first or not second:
        raise ValueError("One or both document IDs were not found.")
    chunks1 = vector_store.get_document_chunks(doc1_id)
    chunks2 = vector_store.get_document_chunks(doc2_id)
    values1, values2 = _metric_evidence(chunks1), _metric_evidence(chunks2)
    metrics: List[ComparisonMetric] = []
    citations: List[SourceCitation] = []
    differences: List[str] = []

    for label in METRIC_LABELS:
        item1, item2 = values1.get(label), values2.get(label)
        if not item1 or not item2:
            continue
        val1, evidence1, chunk1 = item1
        val2, evidence2, chunk2 = item2
        delta = round(val2 - val1, 4)
        pct = round(delta / abs(val1) * 100, 2) if val1 else None
        metrics.append(ComparisonMetric(
            metric=label,
            doc1_name=first.filename,
            doc1_value=val1,
            doc1_text=evidence1,
            doc2_name=second.filename,
            doc2_value=val2,
            doc2_text=evidence2,
            change_absolute=delta,
            change_percent=pct,
            interpretation="Calculated from the extracted values shown above." if val1 != val2 else "The extracted values match.",
        ))
        differences.append(f"{label}: {first.filename} — {evidence1}; {second.filename} — {evidence2}.")
        for filename, did, chunk, evidence in (
            (first.filename, doc1_id, chunk1, evidence1),
            (second.filename, doc2_id, chunk2, evidence2),
        ):
            citations.append(SourceCitation(
                document_name=filename,
                document_id=did,
                page=int(chunk.get("page", 1)),
                section=str(chunk.get("section", "Content")),
                snippet=evidence,
            ))

    if metrics:
        summary = f"Compared {len(metrics)} metric(s) present in both indexed documents. Numeric changes are calculated from the extracted source lines."
    else:
        summary = "No matching numeric metrics could be extracted from both documents. Compare their source text and tables to review the available content."

    return CompareResponse(
        doc1_id=doc1_id,
        doc1_name=first.filename,
        doc2_id=doc2_id,
        doc2_name=second.filename,
        comparison_summary=summary,
        metrics=metrics,
        key_differences=differences,
        citations=citations,
        agent_logs=[],
    )
