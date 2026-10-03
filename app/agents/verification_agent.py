"""Strict text-match verification for extracted claims and arithmetic calculations."""

import re
from typing import List

from app.agents.base_agent import BaseAgent
from app.models.schemas import ClaimVerification
from app.models.state import AgentState


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


class VerificationAgent(BaseAgent):
    """Marks claims supported only by a matching source excerpt or reproducible arithmetic."""

    def __init__(self):
        super().__init__(name="Verification Agent", description="Checks extracted claims against source text and arithmetic inputs.")

    def run(self, state: AgentState) -> AgentState:
        state.current_agent = self.name
        chunks = state.retrieved_chunks
        state.verification_results = []
        if not chunks:
            state.confidence_score = 0.0
            state.confidence_level = "Low (No Evidence)"
            state.add_log(agent_name=self.name, action="Claim Verification", detail="Verification skipped because no source chunks were retrieved.", status="warning")
            return state

        checks = []
        for claim in state.explicit_facts:
            normalized_claim = normalize(claim)
            support = [chunk for chunk in chunks if normalized_claim and normalized_claim in normalize(chunk.text)]
            checks.append((claim, support, "Exact normalized text match in retrieved source." if support else "No exact text match was found in retrieved sources."))

        for calculation in state.derived_calculations:
            sources = calculation.get("sources", [])
            details = calculation.get("details", {})
            support = []
            arithmetic_ok = False
            if len(sources) >= 2:
                for item in sources[:2]:
                    filename = item.get("filename")
                    evidence = normalize(str(item.get("evidence", "")))
                    matches = [chunk for chunk in chunks if chunk.filename == filename and evidence and evidence in normalize(chunk.text)]
                    if not matches:
                        support = []
                        break
                    support.extend(matches)
                if len(support) >= 2:
                    first, second = sources[0], sources[1]
                    delta = float(second["value"]) - float(first["value"])
                    pct = delta / abs(float(first["value"])) * 100 if first["value"] else None
                    arithmetic_ok = (
                        round(delta, 2) == round(float(details.get("absolute_change", float("nan"))), 2)
                        and pct is not None
                        and round(pct, 2) == round(float(details.get("percentage_change", float("nan"))), 2)
                    )
            checks.append((calculation.get("explanation", calculation.get("metric", "Calculation")), support if arithmetic_ok else [], "Recomputed from two matched source values." if arithmetic_ok else "Source inputs or calculated delta could not be independently matched."))

        for claim, support, reasoning in checks:
            supported = bool(support)
            state.verification_results.append(ClaimVerification(
                claim=claim,
                supported=supported,
                confidence=1.0 if supported else 0.0,
                source_pages=sorted({chunk.page for chunk in support}),
                source_filenames=sorted({chunk.filename for chunk in support}),
                evidence_text="\n".join(dict.fromkeys(chunk.text[:500] for chunk in support)) or None,
                reasoning=reasoning,
            ))

        total = len(state.verification_results)
        supported_count = sum(item.supported for item in state.verification_results)
        state.confidence_score = round(supported_count / total, 2) if total else 0.0
        state.confidence_level = "High" if state.confidence_score >= .85 else "Medium" if state.confidence_score >= .5 else "Low"
        state.add_log(
            agent_name=self.name,
            action="Evidence Match Audit",
            detail=f"Matched {supported_count}/{total} extracted claims/calculations against source text and arithmetic inputs.",
            status="completed",
        )
        return state


verification_agent = VerificationAgent()
