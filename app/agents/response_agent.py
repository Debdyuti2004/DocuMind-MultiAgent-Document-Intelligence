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

        from app.services.translation_service import translation_service
        from app.utils.logging import logger

        # Enrich sources with original and translated snippets
        updated_sources = []
        for src in state.sources:
            chunk_match = next((c for c in state.retrieved_chunks if c.document_id == src.document_id and c.page == src.page), None)
            lang = chunk_match.language if chunk_match else "en"
            orig_snip = src.snippet
            trans_snip = None
            if lang != "en":
                trans_snip = translation_service.translate(orig_snip, source_lang=lang, target_lang="en")
                state.translation_applied = state.translation_applied or trans_snip != orig_snip
            src.original_snippet = orig_snip
            src.translated_snippet = trans_snip
            src.language = lang
            updated_sources.append(src)
        state.sources = updated_sources

        # Check if final answer needs translation to requested non-English output language
        target_lang = state.output_language or "en"
        if target_lang not in ("en", "original"):
            answer_text = "\n".join(lines)
            try:
                translated_ans = translation_service.translate(answer_text, source_lang="en", target_lang=target_lang)
                state.final_answer = translated_ans
                state.translation_applied = state.translation_applied or translated_ans != answer_text
            except Exception as e:
                logger.warning(f"Translation to {target_lang} failed: {e}")
                state.final_answer = answer_text
        else:
            state.final_answer = "\n".join(lines)

        state.add_log(
            agent_name=self.name,
            action="Response Formatting",
            detail=f"Formatted {len(state.explicit_facts)} extracted passage(s) and {len(state.sources)} source reference(s) (Output language: {target_lang}).",
            status="completed",
        )
        return state


response_agent = ResponseAgent()
