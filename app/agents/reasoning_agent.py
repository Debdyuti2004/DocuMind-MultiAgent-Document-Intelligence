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

        words = [w for w in re.findall(r"[a-zA-Z0-9]{3,}", state.query.lower()) if w not in STOPWORDS]
        selected: List[str] = []
        any_match = False
        for chunk in state.retrieved_chunks:
            for part in re.split(r"(?<=[.!?])\s+|\n+", chunk.text):
                sentence = re.sub(r"\s+", " ", part).strip(" •\t")
                if len(sentence) < 18:
                    continue
                matches = [word for word in words if word in sentence.lower()]
                if matches:
                    any_match = True
                    selected.append(sentence)
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
            detail=f"Selected {len(selected)} source sentence(s) matching the query; no unsupported interpretation was added.",
            status="completed" if selected else "warning",
        )
        return state


reasoning_agent = ReasoningAgent()
