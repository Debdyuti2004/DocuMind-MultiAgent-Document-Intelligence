"""Planner / Orchestrator Agent that analyzes user intent and synthesizes dynamic execution plans."""

import json
import re
from typing import Dict, List, Tuple
from app.agents.base_agent import BaseAgent
from app.models.state import AgentState
from app.utils.logging import logger


class PlannerAgent(BaseAgent):
    """Central planning agent that dynamically determines required tasks and agent delegations."""

    def __init__(self):
        super().__init__(
            name="Planner Agent",
            description="Analyzes user intent, selects required tools/agents, and constructs a dynamic task plan."
        )

    def analyze_intent(self, query: str, active_doc_count: int = 1) -> Tuple[str, List[str], List[str]]:
        """Determines intent, generates task list, and selects necessary agents dynamically."""
        q_lower = query.lower()

        # 1. External research intent (industry benchmarks, competitor averages, external context)
        if any(w in q_lower for w in ["industry", "competitor", "market average", "external", "benchmark", "global standard"]):
            intent = "external_research"
            tasks = [
                "retrieve_internal_evidence",
                "search_external_benchmarks",
                "contrast_internal_vs_external",
                "verify_internal_citations",
                "generate_grounded_response"
            ]
            agents = ["retrieval_agent", "research_agent", "reasoning_agent", "verification_agent", "response_agent"]

        # 2. Multi-document comparison intent
        elif any(w in q_lower for w in ["compare", "difference between", "versus", "vs", "changes between", "what changed"]):
            intent = "document_comparison"
            tasks = [
                "retrieve_multi_document_sections",
                "extract_parallel_metrics",
                "calculate_percentage_variances",
                "reason_comparative_shifts",
                "verify_dual_citations",
                "generate_grounded_response"
            ]
            agents = ["retrieval_agent", "financial_agent", "reasoning_agent", "verification_agent", "response_agent"]

        # 3. Financial analysis & profit/revenue drivers
        elif any(w in q_lower for w in ["profit", "revenue", "ebitda", "margin", "decline", "increase", "expense", "growth", "financial", "sales"]):
            intent = "financial_analysis"
            tasks = [
                "retrieve_profit_and_revenue_data",
                "retrieve_expense_breakdown",
                "retrieve_management_commentary",
                "extract_financial_tables",
                "calculate_growth_and_margins",
                "identify_underlying_drivers",
                "verify_factual_claims",
                "generate_grounded_response"
            ]
            agents = ["retrieval_agent", "financial_agent", "reasoning_agent", "verification_agent", "response_agent"]

        # 4. Risk detection intent
        elif any(w in q_lower for w in ["risk", "threat", "challenge", "vulnerability", "compliance", "regulatory", "headwind"]):
            intent = "risk_assessment"
            tasks = [
                "retrieve_risk_disclosures",
                "extract_threat_vectors",
                "evaluate_operational_and_financial_risks",
                "verify_risk_citations",
                "generate_grounded_response"
            ]
            agents = ["retrieval_agent", "risk_agent", "reasoning_agent", "verification_agent", "response_agent"]

        # 5. Summarization intent
        elif any(w in q_lower for w in ["summarize", "summary", "overview", "executive summary", "key points"]):
            intent = "document_summary"
            tasks = [
                "retrieve_executive_sections",
                "extract_key_entities_and_themes",
                "synthesize_core_findings",
                "verify_summary_facts",
                "generate_grounded_response"
            ]
            agents = ["retrieval_agent", "reasoning_agent", "verification_agent", "response_agent"]

        # 6. General Document Q&A
        else:
            intent = "document_qa"
            tasks = [
                "retrieve_relevant_chunks",
                "synthesize_direct_factual_evidence",
                "verify_claims_against_sources",
                "generate_grounded_response"
            ]
            agents = ["retrieval_agent", "reasoning_agent", "verification_agent", "response_agent"]

        return intent, tasks, agents

    def run(self, state: AgentState) -> AgentState:
        """Executes planning phase and annotates AgentState with intent and tasks."""
        state.current_agent = self.name
        intent, tasks, agents = self.analyze_intent(state.query, active_doc_count=len(state.document_ids))
        state.intent = intent
        state.plan = tasks

        logger.info(f"Planner Agent: Intent='{intent}' | Generated {len(tasks)} tasks | Agents required: {agents}")
        state.add_log(
            agent_name=self.name,
            action="Plan Generation",
            detail=f"Identified intent '{intent}'. Constructed {len(tasks)} tasks spanning {len(agents)} specialized agents."
        )
        return state


planner_agent = PlannerAgent()
