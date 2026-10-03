"""Agent State definition for orchestrating multi-agent workflows."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.models.schemas import (
    AgentActionLog,
    ClaimVerification,
    DocumentChunk,
    SourceCitation,
)


class AgentState(BaseModel):
    """Central state object exchanged across all agents during query execution."""

    # Context & Inputs
    session_id: str = "default_session"
    query: str
    document_ids: List[str] = Field(default_factory=list)
    active_documents: Dict[str, str] = Field(default_factory=dict)  # id -> filename
    document_types: Dict[str, str] = Field(default_factory=dict)  # id -> doc_type

    # Planning & Orchestration
    intent: Optional[str] = None
    plan: List[str] = Field(default_factory=list)
    tasks_completed: List[str] = Field(default_factory=list)
    current_agent: Optional[str] = None

    # Intermediate Evidence & Agent Outputs
    retrieved_chunks: List[DocumentChunk] = Field(default_factory=list)
    extracted_data: Dict[str, Any] = Field(default_factory=dict)
    financial_metrics: Dict[str, Any] = Field(default_factory=dict)
    risk_indicators: List[Dict[str, Any]] = Field(default_factory=list)
    external_research: List[Dict[str, Any]] = Field(default_factory=list)

    # Reasoning Breakdown
    explicit_facts: List[str] = Field(default_factory=list)
    derived_calculations: List[Dict[str, Any]] = Field(default_factory=list)
    interpretations: List[str] = Field(default_factory=list)
    reasoning_summary: Optional[str] = None

    # Verification & Citations
    verification_results: List[ClaimVerification] = Field(default_factory=list)
    sources: List[SourceCitation] = Field(default_factory=list)
    confidence_score: float = 0.9
    confidence_level: str = "High"

    # Final Synthesis & Observability
    final_answer: Optional[str] = None
    agent_logs: List[AgentActionLog] = Field(default_factory=list)
    error_message: Optional[str] = None

    def add_log(self, agent_name: str, action: str, detail: str, status: str = "completed") -> None:
        """Helper to append a user-safe operational log entry."""
        self.agent_logs.append(
            AgentActionLog(agent_name=agent_name, action=action, detail=detail, status=status)
        )
