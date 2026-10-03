"""Extractive risk indicator detection grounded in retrieved evidence."""

import re
from app.agents.base_agent import BaseAgent
from app.models.state import AgentState


RISK_PATTERN = re.compile(
    r"\b(risk|threat|challenge|vulnerabilit\w*|liabilit\w*|penalt\w*|exposure|uncertain\w*|"
    r"may result|subject to|termination|breach|non-compliance|noncompliance)\b",
    re.I,
)


class RiskDetectionAgent(BaseAgent):
    """Surfaces source sentences that contain explicit risk-related wording."""

    def __init__(self):
        super().__init__(name="Risk Detection Agent", description="Finds explicit risk-related statements in retrieved source text.")

    def run(self, state: AgentState) -> AgentState:
        state.current_agent = self.name
        indicators = []
        seen = set()
        for chunk in state.retrieved_chunks:
            for part in re.split(r"(?<=[.!?])\s+|\n+", chunk.text):
                sentence = re.sub(r"\s+", " ", part).strip(" •\t")
                if not sentence or not RISK_PATTERN.search(sentence) or sentence.lower() in seen:
                    continue
                seen.add(sentence.lower())
                match = RISK_PATTERN.search(sentence)
                severity = "Unrated"
                # Only use a severity when the source itself labels it.
                surrounding = sentence[max(0, match.start() - 18):match.end() + 18].lower()
                if re.search(r"\b(high|critical|severe)\b", surrounding):
                    severity = "High"
                elif re.search(r"\b(medium|moderate)\b", surrounding):
                    severity = "Medium"
                elif re.search(r"\blow\b", surrounding):
                    severity = "Low"
                indicators.append({
                    "category": "Source disclosure",
                    "label": "Explicit risk-related text",
                    "finding": sentence,
                    "evidence": sentence,
                    "severity": severity,
                    "document_name": chunk.filename,
                    "document_id": chunk.document_id,
                    "page": chunk.page,
                })

        state.risk_indicators = indicators
        state.add_log(
            agent_name=self.name,
            action="Risk Text Extraction",
            detail=f"Found {len(indicators)} risk-related source sentence(s); severity is shown only when stated in evidence.",
            status="completed" if indicators else "warning",
        )
        return state


risk_agent = RiskDetectionAgent()
