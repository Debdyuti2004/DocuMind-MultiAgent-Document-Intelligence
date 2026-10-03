"""Retrieval tools interfacing with the hybrid vector and keyword retriever."""

import time
from typing import Any, Dict, List, Optional
from app.rag.retriever import retriever
from app.tools.base_tool import BaseTool, ToolResult, tool_registry


class SearchDocumentsTool(BaseTool):
    """Searches indexed document chunks using hybrid semantic and keyword retrieval."""

    name = "search_documents"
    description = "Searches indexed document chunks with semantic similarity and keyword matching."
    parameters = {
        "query": "The search question or query phrase (str)",
        "document_ids": "Optional list of document IDs to restrict search to (List[str])",
        "top_k": "Number of top results to retrieve (int, default 5)"
    }

    def execute(self, query: str, document_ids: Optional[List[str]] = None, top_k: int = 5, **kwargs) -> ToolResult:
        start_t = time.perf_counter()
        try:
            chunks = retriever.retrieve(query=query, document_ids=document_ids, top_k=top_k)
            data = [c.model_dump() for c in chunks]
            return ToolResult(
                success=True,
                data=data,
                execution_time_ms=(time.perf_counter() - start_t) * 1000
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                execution_time_ms=(time.perf_counter() - start_t) * 1000
            )


search_tool = SearchDocumentsTool()
tool_registry.register(search_tool)
