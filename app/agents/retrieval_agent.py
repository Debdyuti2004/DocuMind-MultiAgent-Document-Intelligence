"""Information Retrieval Agent managing multi-source hybrid document search."""

from typing import List
from app.agents.base_agent import BaseAgent
from app.models.schemas import SourceCitation
from app.models.state import AgentState
from app.rag.retriever import retriever
from app.utils.logging import logger


class RetrievalAgent(BaseAgent):
    """Retrieves the most relevant document chunks across active documents with hybrid scoring."""

    def __init__(self):
        super().__init__(
            name="Retrieval Agent",
            description="Executes hybrid semantic and keyword searches across vector database and populates evidence."
        )

    def run(self, state: AgentState) -> AgentState:
        state.current_agent = self.name

        doc_ids = state.document_ids if state.document_ids else None
        logger.info(f"Retrieval Agent searching for '{state.query}' across doc_ids={doc_ids}")

        chunks = retriever.retrieve(query=state.query, document_ids=doc_ids, top_k=6)
        state.retrieved_chunks = chunks

        # Build initial candidate source citations
        citations: List[SourceCitation] = []
        for c in chunks:
            snippet = c.text[:140].replace("\n", " ") + "..."
            citations.append(
                SourceCitation(
                    document_name=c.filename,
                    document_id=c.document_id,
                    page=c.page,
                    section=c.section,
                    snippet=snippet
                )
            )
        state.sources = citations

        pages_found = sorted(list({c.page for c in chunks}))
        docs_found = list({c.filename for c in chunks})

        state.add_log(
            agent_name=self.name,
            action="Evidence Retrieval",
            detail=f"Retrieved {len(chunks)} relevant chunks from {len(docs_found)} document(s) on page(s) {pages_found}."
        )
        return state


retrieval_agent = RetrievalAgent()
