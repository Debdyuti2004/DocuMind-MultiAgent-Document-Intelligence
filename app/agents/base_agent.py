"""Base Agent interface for DocuMind multi-agent system."""

from abc import ABC, abstractmethod
from app.models.state import AgentState
from app.utils.logging import logger


class BaseAgent(ABC):
    """Abstract base class for all DocuMind agents."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def run(self, state: AgentState) -> AgentState:
        """Executes agent-specific tasks on the shared AgentState and returns updated state."""
        pass
