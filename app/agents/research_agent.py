"""Research Agent for external web benchmarking and comparative context."""

from typing import Any, Dict, List
from app.agents.base_agent import BaseAgent
from app.models.state import AgentState
from app.tools.web_tools import web_tool
from app.utils.logging import logger


class ResearchAgent(BaseAgent):
    """Executes external market and industry research, strictly segregating external data from document facts."""

    def __init__(self):
        super().__init__(
            name="Research Agent",
            description="Queries external benchmarks and industry data when questions require information outside uploaded documents."
        )

    def run(self, state: AgentState) -> AgentState:
        state.current_agent = self.name
        tool_res = web_tool.execute(query=state.query)
        
        if tool_res.success and tool_res.data:
            state.external_research.append(tool_res.data)
            findings_count = len(tool_res.data.get("findings", []))
            state.add_log(
                agent_name=self.name,
                action="External Web Research",
                detail=f"Executed external query '{state.query}'. Retrieved {findings_count} industry benchmark categories."
            )
        else:
            state.add_log(
                agent_name=self.name,
                action="External Web Research",
                detail="No external research results retrieved.",
                status="warning"
            )

        return state


research_agent = ResearchAgent()
