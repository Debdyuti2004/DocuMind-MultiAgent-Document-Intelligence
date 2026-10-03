"""Session-level conversational memory service tracking context, active documents, and query history."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ConversationTurn(BaseModel):
    """A single turn in the conversational dialogue."""
    query: str
    resolved_query: str
    answer: str
    document_ids: List[str]
    intent: str


class SessionContext(BaseModel):
    """Holds active memory state for a user session."""
    session_id: str
    active_document_ids: List[str] = Field(default_factory=list)
    history: List[ConversationTurn] = Field(default_factory=list)
    last_entities: List[str] = Field(default_factory=list)
    last_topic: Optional[str] = None


class MemoryService:
    """Provides conversational session persistence and ellipsis/anaphora query resolution."""

    def __init__(self):
        self.sessions: Dict[str, SessionContext] = {}

    def get_or_create_session(self, session_id: str) -> SessionContext:
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionContext(session_id=session_id)
        return self.sessions[session_id]

    def set_active_documents(self, session_id: str, document_ids: List[str]) -> None:
        session = self.get_or_create_session(session_id)
        session.active_document_ids = document_ids

    def resolve_query(self, session_id: str, current_query: str) -> str:
        """Resolves conversational ellipsis (e.g. 'And profit?' -> 'ApexCorp FY2025 profit')."""
        session = self.get_or_create_session(session_id)
        if not session.history:
            return current_query

        q_clean = current_query.strip().lower()
        last_turn = session.history[-1]

        # Check for brief follow-up patterns
        is_follow_up = False
        if len(q_clean.split()) <= 4:
            if any(q_clean.startswith(prefix) for prefix in ["and ", "what about ", "how about ", "also ", "why "]):
                is_follow_up = True
            elif q_clean in ["profit?", "revenue?", "risks?", "ebitda?", "expenses?", "accuracy?", "sla?"]:
                is_follow_up = True

        if is_follow_up:
            # Anchor to subject of the previous query
            prev_q = last_turn.resolved_query
            resolved = f"{prev_q} (Follow-up inquiry: {current_query})"
            return resolved

        return current_query

    def add_turn(
        self,
        session_id: str,
        query: str,
        resolved_query: str,
        answer: str,
        document_ids: List[str],
        intent: str
    ) -> None:
        """Records a completed turn in session memory."""
        session = self.get_or_create_session(session_id)
        turn = ConversationTurn(
            query=query,
            resolved_query=resolved_query,
            answer=answer,
            document_ids=document_ids,
            intent=intent
        )
        session.history.append(turn)
        if len(session.history) > 20:
            session.history.pop(0)

    def clear_session(self, session_id: str) -> None:
        if session_id in self.sessions:
            del self.sessions[session_id]


memory_service = MemoryService()
