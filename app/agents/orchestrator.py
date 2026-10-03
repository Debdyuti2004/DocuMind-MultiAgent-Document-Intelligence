"""Central Agent Orchestrator that dynamically routes and coordinates specialized agents."""

import time
from typing import Dict, List, Optional
from app.document.metadata import registry
from app.models.schemas import AgentActionLog, QueryResponse, SourceCitation
from app.models.state import AgentState
from app.services.memory_service import memory_service
from app.utils.logging import logger

# Import all specialized agents
from app.agents.classifier_agent import classifier_agent
from app.agents.planner_agent import planner_agent
from app.agents.retrieval_agent import retrieval_agent
from app.agents.financial_agent import financial_agent
from app.agents.risk_agent import risk_agent
from app.agents.research_agent import research_agent
from app.agents.reasoning_agent import reasoning_agent
from app.agents.verification_agent import verification_agent
from app.agents.response_agent import response_agent


class AgentOrchestrator:
    """Dynamic multi-agent orchestrator executing intent-driven workflows."""

    def __init__(self):
        self.agents_map = {
            "classifier_agent": classifier_agent,
            "planner_agent": planner_agent,
            "retrieval_agent": retrieval_agent,
            "financial_agent": financial_agent,
            "risk_agent": risk_agent,
            "research_agent": research_agent,
            "reasoning_agent": reasoning_agent,
            "verification_agent": verification_agent,
            "response_agent": response_agent,
        }

    @staticmethod
    def _run_timed(agent, state: AgentState) -> AgentState:
        """Run one agent and attach measured elapsed time to the log it emitted."""
        start = time.perf_counter()
        state = agent.run(state)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        for log in reversed(state.agent_logs):
            if log.agent_name == agent.name and log.execution_time_ms is None:
                log.execution_time_ms = elapsed_ms
                break
        return state

    def process_query(
        self,
        query: str,
        document_ids: Optional[List[str]] = None,
        session_id: str = "default_session",
        enable_research: bool = False,
        enable_verification: bool = True
    ) -> AgentState:
        """Executes the dynamic multi-agent workflow based on user intent."""
        start_time = time.perf_counter()

        # Step 0: Resolve query context from memory
        resolved_query = memory_service.resolve_query(session_id, query)
        logger.info(f"Orchestrator received: '{query}' (Resolved: '{resolved_query}')")

        # Resolve active documents
        doc_ids = document_ids or []
        if not doc_ids:
            # Fall back to all registered documents if none explicitly chosen
            all_meta = registry.list_all()
            doc_ids = [m.document_id for m in all_meta]

        active_docs: Dict[str, str] = {}
        doc_types: Dict[str, str] = {}
        for did in doc_ids:
            meta = registry.get(did)
            if meta:
                active_docs[did] = meta.filename
                doc_types[did] = meta.document_type

        # Initialize Agent State
        state = AgentState(
            session_id=session_id,
            query=resolved_query,
            document_ids=doc_ids,
            active_documents=active_docs,
            document_types=doc_types
        )

        state.add_log(
            agent_name="Orchestrator",
            action="Workflow Initialization",
            detail=f"Received query. Active documents: {list(active_docs.values())}."
        )

        # Step 1: Planner Agent determines intent and dynamic task delegation
        state = self._run_timed(planner_agent, state)
        intent = state.intent or "document_qa"

        # Step 2: Retrieval Agent executes hybrid search
        state = self._run_timed(retrieval_agent, state)

        # Step 3: Conditional Domain & Research Agent Activations
        # A. Financial Analysis Agent
        is_financial = any(dt in ("Annual Report", "Finance", "Invoice") for dt in doc_types.values())
        if intent in ("financial_analysis", "document_comparison") or is_financial:
            state = self._run_timed(financial_agent, state)

        # B. Risk Detection Agent
        if intent == "risk_assessment" or "risk" in resolved_query.lower() or "threat" in resolved_query.lower():
            state = self._run_timed(risk_agent, state)

        # C. Research Agent (external web benchmarks)
        if intent == "external_research" or enable_research:
            state = self._run_timed(research_agent, state)

        # Step 4: Reasoning Agent synthesizes explicit facts, calculations, and interpretations
        state = self._run_timed(reasoning_agent, state)

        # Step 5: Verification Agent (guardrail against hallucinations)
        if enable_verification:
            state = self._run_timed(verification_agent, state)

        # Step 6: Response Agent formats final grounded answer and citations
        state = self._run_timed(response_agent, state)

        # Step 7: Record completed turn in memory
        elapsed = time.perf_counter() - start_time
        memory_service.add_turn(
            session_id=session_id,
            query=query,
            resolved_query=resolved_query,
            answer=state.final_answer or "",
            document_ids=doc_ids,
            intent=intent
        )

        state.add_log(
            agent_name="Orchestrator",
            action="Workflow Completed",
            detail=f"Successfully processed query across dynamic agent network in {elapsed:.2f}s."
        )
        return state


orchestrator = AgentOrchestrator()
