"""Base Tool abstraction and Tool Registry for DocuMind agents."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Result returned by tool execution."""
    success: bool
    data: Any
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class BaseTool(ABC):
    """Abstract base class for all agent-callable tools."""
    name: str
    description: str
    parameters: Dict[str, Any]

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Executes tool logic and returns structured ToolResult."""
        pass


class ToolRegistry:
    """Central registry for discovering and executing agent tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters
            }
            for t in self._tools.values()
        ]

    def execute(self, name: str, **kwargs) -> ToolResult:
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(success=False, data=None, error=f"Tool '{name}' not found.")
        try:
            return tool.execute(**kwargs)
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))


tool_registry = ToolRegistry()
