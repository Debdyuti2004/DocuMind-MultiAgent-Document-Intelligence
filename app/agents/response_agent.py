"""Response formatting that preserves a clear boundary between evidence and calculations."""

from app.agents.base_agent import BaseAgent
from app.models.state import AgentState


class ResponseAgent(BaseAgent):
    """Formats extracted evidence, computed metrics, and exact citation metadata."""

    def __init__(self):
        super().__init__(name="Response Generation Agent", description="Formats retrieved evidence and source references for display.")

    def run(self, state: AgentState) -> AgentState:
        state.current_agent = self.name
        if not state.retrieved_chunks or state.reasoning_summary == "INSUFFICIENT_EVIDENCE":
            state.final_answer = (
                "Insufficient evidence: the retrieved document text did not provide a relevant source passage. "
                "No document-specific result was generated."
            )
            state.add_log(agent_name=self.name, action="Evidence-limited response", detail="Returned without unsupported document claims.", status="warning")
            return state

        lines = []
        if state.explicit_facts:
            lines.extend(["Source excerpts", *[f"- {fact}" for fact in state.explicit_facts]])
        else:
            lines.append("Relevant retrieved text is available, but no concise excerpt matched the question.")

        if state.derived_calculations:
            lines.extend(["", "Calculated from extracted values"])
            for calculation in state.derived_calculations:
                lines.append(f"- {calculation.get('metric', 'Calculation')}: {calculation.get('explanation', '')}")

        if state.risk_indicators:
            lines.extend(["", "Risk-related source text"])
            for item in state.risk_indicators:
                lines.append(f"- [{item.get('severity', 'Unrated')}] {item['evidence']}")

        if state.sources:
            lines.extend(["", "Sources"])
            seen = set()
            for source in state.sources:
                key = (source.document_id, source.page, source.section)
                if key in seen:
                    continue
                seen.add(key)
                lines.append(f"- {source.document_name} — page {source.page} · {source.section}")
        else:
            lines.extend(["", "Source evidence metadata is unavailable for this response."])

        if state.verification_results:
            verified = sum(1 for item in state.verification_results if item.supported)
            lines.append(f"\nClaim checks: {verified}/{len(state.verification_results)} supported by the verification agent.")

        state.final_answer = "\n".join(lines)
        state.add_log(
            agent_name=self.name,
            action="Response Formatting",
            detail=f"Formatted {len(state.explicit_facts)} extracted passage(s) and {len(state.sources)} source reference(s).",
            status="completed",
        )
        return state


response_agent = ResponseAgent()
