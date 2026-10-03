"""Hybrid Retriever combining dense vector search, sparse keyword matching, and query expansion."""

import re
from typing import Any, Dict, List, Optional
from app.models.schemas import DocumentChunk
from app.rag.vector_store import vector_store
from app.utils.config import settings
from app.utils.logging import logger


class HybridRetriever:
    """Orchestrates hybrid semantic + keyword retrieval with rank fusion."""

    def __init__(self, semantic_weight: float = 0.7, top_k: int = settings.TOP_K):
        self.semantic_weight = semantic_weight
        self.keyword_weight = 1.0 - semantic_weight
        self.top_k = top_k

    def retrieve(
        self,
        query: str,
        document_ids: Optional[List[str]] = None,
        top_k: Optional[int] = None
    ) -> List[DocumentChunk]:
        """Retrieves and re-ranks top chunks matching the query across specified documents."""
        k = top_k or self.top_k
        expanded_queries = self._expand_query(query)
        logger.info(f"Expanded queries: {expanded_queries}")

        # Gather semantic candidates across expanded queries
        candidate_dict: Dict[str, Dict[str, Any]] = {}

        for eq in expanded_queries:
            dense_results = vector_store.search(
                query=eq,
                top_k=k * 2,
                document_ids=document_ids
            )
            for res in dense_results:
                cid = res["chunk_id"]
                if cid not in candidate_dict:
                    candidate_dict[cid] = res
                else:
                    # Max pooling over semantic similarity
                    candidate_dict[cid]["similarity_score"] = max(
                        candidate_dict[cid]["similarity_score"],
                        res["similarity_score"]
                    )

        if not candidate_dict:
            return []

        # Compute keyword scores (term overlap & frequency)
        query_terms = self._tokenize(query)
        for cid, cand in candidate_dict.items():
            text_tokens = self._tokenize(cand["text"])
            kw_score = self._compute_keyword_score(query_terms, text_tokens)
            cand["keyword_score"] = kw_score
            # Combine dense and sparse scores
            cand["final_score"] = (
                self.semantic_weight * cand["similarity_score"]
                + self.keyword_weight * kw_score
            )

        # Filter candidates by minimum relevance threshold
        filtered_candidates = [
            c for c in candidate_dict.values()
            if not (c["keyword_score"] == 0.0 and c["similarity_score"] < settings.SIMILARITY_THRESHOLD)
        ]

        # Sort by final combined score descending
        ranked = sorted(filtered_candidates, key=lambda x: x["final_score"], reverse=True)
        top_candidates = ranked[:k]

        # Convert back into DocumentChunk objects
        chunks: List[DocumentChunk] = []
        for c in top_candidates:
            chunks.append(
                DocumentChunk(
                    chunk_id=c["chunk_id"],
                    document_id=c["document_id"],
                    filename=c["filename"],
                    page=c["page"],
                    section=c["section"],
                    text=c["text"],
                    chunk_index=c.get("chunk_index", 0),
                    token_count=len(c["text"].split())
                )
            )

        logger.info(f"Hybrid retrieval returned {len(chunks)} chunks for query: '{query}'")
        return chunks

    def _expand_query(self, query: str) -> List[str]:
        """Expands queries using domain keyword synonyms."""
        queries = [query]
        q_lower = query.lower()

        # Financial expansions
        if "profit" in q_lower or "loss" in q_lower:
            queries.append("net income operating profit EBITDA margins expenses")
        if "revenue" in q_lower or "sales" in q_lower:
            queries.append("total revenue turnover segment sales growth")
        if "expense" in q_lower or "cost" in q_lower:
            queries.append("operating expenses expenditure procurement personnel")
        if "risk" in q_lower or "threat" in q_lower:
            queries.append("risk factors compliance regulatory challenges volatility")
        if "compare" in q_lower or "difference" in q_lower:
            queries.append(re.sub(r"(compare|difference between|versus|vs)", "", query, flags=re.IGNORECASE).strip())

        # Return unique non-empty queries
        return list(dict.fromkeys([q.strip() for q in queries if q.strip()]))

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenizer removing non-alphanumeric characters."""
        return [w.lower() for w in re.findall(r"\b\w{2,}\b", text)]

    def _compute_keyword_score(self, query_tokens: List[str], doc_tokens: List[str]) -> float:
        """Calculates normalized token overlap score."""
        if not query_tokens or not doc_tokens:
            return 0.0

        query_set = set(query_tokens)
        doc_set = set(doc_tokens)
        overlap = query_set.intersection(doc_set)
        
        # Jaccard-like or recall score
        return len(overlap) / len(query_set)


retriever = HybridRetriever()
