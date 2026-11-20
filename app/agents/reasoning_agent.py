"""Extractive reasoning over retrieved document evidence."""

import re
from typing import List, Set

from app.agents.base_agent import BaseAgent
from app.models.state import AgentState


STOPWORDS = {
    "what", "when", "where", "which", "who", "whom", "whose", "why", "how", "this", "that",
    "these", "those", "does", "have", "with", "from", "about", "show", "tell", "for", "and",
    "the", "are", "was", "were", "been", "being", "has", "had", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "into", "onto", "then", "than", "more",
    "most", "some", "any", "all", "both", "each", "other", "such", "only", "same", "also",
    "document", "documents", "please", "explain", "tell", "describe", "mention", "mentioned",
}


class ReasoningAgent(BaseAgent):
    """Selects source sentences relevant to a query without adding unsupported statements."""

    def __init__(self):
        super().__init__(name="Reasoning Agent", description="Selects query-relevant statements from retrieved source chunks.")

    def run(self, state: AgentState) -> AgentState:
        state.current_agent = self.name
        if not state.retrieved_chunks:
            state.reasoning_summary = "INSUFFICIENT_EVIDENCE"
            state.explicit_facts = []
            state.interpretations = []
            state.add_log(agent_name=self.name, action="Evidence Selection", detail="No source chunks were retrieved.", status="warning")
            return state

        from app.services.language_service import language_detector
        from app.services.translation_service import translation_service

        q_clean = state.query.lower()
        words = [w for w in re.findall(r"[\wÀ-ÿ\u0900-\u097F\u0980-\u09FF\u0600-\u06FF\u4E00-\u9FFF]{3,}", q_clean) if w not in STOPWORDS]

        # Expand words with translated query terms if query is non-English
        q_det = language_detector.detect(state.query)
        if q_det.language_code != "en":
            trans_q = translation_service.translate(state.query, source_lang=q_det.language_code, target_lang="en")
            trans_words = [w for w in re.findall(r"[a-zA-Z0-9]{3,}", trans_q.lower()) if w not in STOPWORDS]
            words = list(dict.fromkeys(words + trans_words))

        selected: List[str] = []
        any_match = False

        for chunk in state.retrieved_chunks:
            chunk_lang = chunk.language or language_detector.detect(chunk.text[:200]).language_code
            for part in re.split(r"(?<=[.!?।\n])\s+|\n+", chunk.text):
                sentence = re.sub(r"\s+", " ", part).strip(" •\t")
                if len(sentence) < 14:
                    continue

                trans_sentence = sentence
                if chunk_lang != "en":
                    trans_sentence = translation_service.translate(sentence, source_lang=chunk_lang, target_lang="en")

                # Match against either original sentence or aligned English translation
                s_lower = sentence.lower()
                ts_lower = trans_sentence.lower()
                matches = [word for word in words if word in s_lower or word in ts_lower]

                if matches:
                    any_match = True
                    # Store fact according to configured output language
                    if state.output_language == "en" and chunk_lang != "en":
                        fact_display = f"{trans_sentence} [{sentence}]" if trans_sentence != sentence else sentence
                        selected.append(fact_display)
                        state.translations[fact_display] = sentence
                    else:
                        selected.append(sentence)
                        if trans_sentence != sentence:
                            state.translations[sentence] = trans_sentence

        selected = list(dict.fromkeys(selected))[:10]

        if words and not any_match:
            state.reasoning_summary = "INSUFFICIENT_EVIDENCE"
            state.explicit_facts = []
            state.interpretations = []
            state.add_log(agent_name=self.name, action="Evidence Relevance Check", detail="No query terms matched the retrieved source text.", status="warning")
            return state

        state.reasoning_summary = "EXTRACTIVE_EVIDENCE"
        state.explicit_facts = selected
        state.interpretations = []
        state.add_log(
            agent_name=self.name,
            action="Evidence Selection",
            detail=f"Selected {len(selected)} source sentence(s) matching the query across languages; no unsupported interpretation was added.",
            status="completed" if selected else "warning",
        )
        return state


reasoning_agent = ReasoningAgent()
