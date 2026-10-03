"""Evidence-only financial extraction and deterministic calculations."""

import re
from typing import Any, Dict, List

from app.agents.base_agent import BaseAgent
from app.models.state import AgentState
from app.rag.vector_store import vector_store
from app.tools.calculation_tools import calc_tool


class FinancialAgent(BaseAgent):
    """Extracts figures from retrieved table/text lines and calculates only sourced deltas."""

    LABELS = {
        "Revenue": ("total revenue", "revenue", "net sales", "turnover"),
        "Operating expenses": ("operating expenses", "total expenses", "expenses"),
        "Net profit": ("net profit", "profit after tax", "pat", "net income"),
        "EBITDA": ("ebitda",),
        "Total debt": ("total debt",),
        "Total assets": ("total assets",),
        "Total liabilities": ("total liabilities",),
        "Employees": ("employees", "headcount"),
    }
    NUMBER = re.compile(r"(?<![A-Za-z])(?:₹|\$|€|£|INR\s*|USD\s*)?\s*(-?\d[\d,]*(?:\.\d+)?)\s*(?:%|Cr\b|Crore\b|Lakh\b|million\b|billion\b)?", re.I)

    def __init__(self):
        super().__init__(name="Financial Analysis Agent", description="Extracts values from retrieved financial evidence and computes deterministic changes.")

    @classmethod
    def _labeled_value(cls, text: str, aliases: tuple[str, ...]):
        """Return a nearby numeric value after a metric label.

        This handles both line-oriented table output and PDF parsers that put
        a whole table row on one long line. Earlier occurrences often state the
        headline amount in prose; later risk text can mention unrelated figures.
        """
        matches = []
        for alias in aliases:
            matches.extend(re.finditer(rf"\b{re.escape(alias)}\b", text, re.I))
        for match in sorted(matches, key=lambda item: item.start()):
            window = text[match.end():match.end() + 240]
            window = re.split(r"(?<=[.!?])\s+|\n+", window, maxsplit=1)[0]
            window = re.sub(r"\b(?:FY\s?)?(?:19|20)\d{2}\b", " ", window, flags=re.I)
            numbers = [
                item.group(1)
                for item in cls.NUMBER.finditer(window)
                if not item.group(0).strip().endswith("%")
            ]
            if numbers:
                try:
                    selected = numbers[1] if len(numbers) > 1 and re.search(r"\bfrom\b.+\bto\b", window, re.I | re.S) else numbers[0]
                    return float(selected.replace(",", "")), text[match.start():match.end() + 180].strip()
                except ValueError:
                    continue
        return None

    @classmethod
    def _extract_metrics(cls, text: str) -> Dict[str, float]:
        """Extract values adjacent to the first relevant occurrence of each label."""
        metrics: Dict[str, float] = {}
        for label, aliases in cls.LABELS.items():
            result = cls._labeled_value(text, aliases)
            if result:
                metrics[label] = result[0]
        return metrics

    def run(self, state: AgentState) -> AgentState:
        state.current_agent = self.name
        found: Dict[str, Dict[str, Dict[str, Any]]] = {}
        # Specialist calculations need values from every selected report. The
        # retrieval agent intentionally returns only a few relevant chunks, so
        # inspect the selected documents' indexed chunks as additional evidence.
        selected_ids = state.document_ids or list(dict.fromkeys(c.document_id for c in state.retrieved_chunks))
        indexed_chunks = [
            item for document_id in selected_ids
            for item in vector_store.get_document_chunks(document_id)
        ]
        for document_id in selected_ids:
            document_chunks = [chunk for chunk in indexed_chunks if str(chunk.get("document_id")) == document_id]
            text = "\n".join(str(chunk.get("text", "")) for chunk in document_chunks)
            for label, aliases in self.LABELS.items():
                result = self._labeled_value(text, aliases)
                if not result:
                    continue
                value, evidence = result
                matched_chunk = next((chunk for chunk in document_chunks if evidence[:50] in str(chunk.get("text", ""))), None)
                source_chunk = matched_chunk or (document_chunks[0] if document_chunks else {})
                found.setdefault(label, {})[document_id] = {
                    "value": value,
                    "evidence": evidence[:500],
                    "filename": source_chunk.get("filename", "Unknown"),
                    "page": source_chunk.get("page", 1),
                }

        state.financial_metrics = found
        calculations: List[Dict[str, Any]] = []
        comparative_query = bool(re.search(
            r"\b(compare|comparison|versus|vs\.?|across|between|increase|decrease|change|growth|decline|trend|difference)\b",
            state.query,
            re.I,
        ))
        if not comparative_query or len(selected_ids) != 2:
            state.derived_calculations = calculations
            state.add_log(
                agent_name=self.name,
                action="Evidence-based Financial Extraction",
                detail=f"Extracted {sum(len(v) for v in found.values())} value(s); cross-document calculations require a comparative question and exactly two selected documents.",
            )
            return state
        for label, per_document in found.items():
            records = list(per_document.values())
            if len(records) < 2:
                continue
            previous, current = records[0], records[1]
            result = calc_tool.execute(operation="yoy_growth", current=current["value"], previous=previous["value"])
            if result.success:
                calculations.append({
                    "metric": f"{label} change across selected documents",
                    "details": result.data,
                    "sources": [previous, current],
                    "explanation": (
                        f"{label} changed from {previous['value']:g} ({previous['filename']}) to "
                        f"{current['value']:g} ({current['filename']}), "
                        f"a {result.data['formatted_string']} change."
                    ),
                })
        state.derived_calculations = calculations
        state.add_log(
            agent_name=self.name,
            action="Evidence-based Financial Extraction",
            detail=f"Extracted {sum(len(v) for v in found.values())} value(s) from selected indexed documents; calculated {len(calculations)} cross-document change(s).",
        )
        return state


financial_agent = FinancialAgent()
