"""Optional external research integration placeholder.

This project does not currently have a configured search provider. Returning an
explicit unavailable result is safer than presenting an unverified benchmark as
live research.
"""

import time
from app.tools.base_tool import BaseTool, ToolResult, tool_registry


class SearchExternalWebTool(BaseTool):
    name = "search_external_web"
    description = "External web research (unavailable until a search provider is configured)."
    parameters = {"query": "External search query phrase (str)"}

    def execute(self, query: str, **kwargs) -> ToolResult:
        start = time.perf_counter()
        return ToolResult(
            success=False,
            data=None,
            error="External web research is not configured. No external results were used.",
            execution_time_ms=(time.perf_counter() - start) * 1000,
        )


web_tool = SearchExternalWebTool()
tool_registry.register(web_tool)
