"""Hybrid Retriever combining dense vector search, sparse keyword matching, and query expansion."""

import re
from typing import Any, Dict, List, Optional
from app.models.schemas import DocumentChunk
from app.rag.vector_store import vector_store
from app.utils.config import settings
from app.utils.logging import logger


from app.document.metadata import registry
from app.services.language_service import language_detector
from app.services.translation_service import translation_service


class HybridRetriever:
    """Orchestrates hybrid semantic + keyword retrieval with cross-language rank fusion."""

    def __init__(self, semantic_weight: float = 0.75, top_k: int = settings.TOP_K):
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
        expanded_queries = self._expand_query(query, document_ids)
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

        # Compute keyword scores (term overlap & frequency) with cross-lingual alignment
        query_terms = self._tokenize(query)
        query_language = language_detector.detect(query).language_code
        translated_query_terms = (
            self._tokenize(translation_service.translate(
                query, source_lang=query_language, target_lang="en"
            ))
            if query_language != "en" else query_terms
        )
        for cid, cand in candidate_dict.items():
            text = cand["text"]
            text_tokens = self._tokenize(text)
            kw_score = self._compute_keyword_score(query_terms, text_tokens)

            # If lexical overlap is 0 (typical for cross-language queries), check English translation
            cand_lang = cand.get("language")
            if not cand_lang or cand_lang == "en":
                # Quick check if text is actually non-English
                det = language_detector.detect(text[:400])
                cand_lang = det.language_code
                cand["language"] = cand_lang

            if cand_lang != "en" and kw_score < 0.2:
                translated_snippet = translation_service.translate(text[:600], source_lang=cand_lang, target_lang="en")
                trans_tokens = self._tokenize(translated_snippet)
                trans_kw_score = self._compute_keyword_score(translated_query_terms, trans_tokens)
                kw_score = max(kw_score, trans_kw_score)

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

        # Convert back into DocumentChunk objects with translation alignment
        chunks: List[DocumentChunk] = []
        for c in top_candidates:
            c_lang = c.get("language", "en")
            # Prepare English translation alongside original text for non-English passages
            translated_text = None
            if c_lang != "en":
                translated_text = translation_service.translate(c["text"], source_lang=c_lang, target_lang="en")

            chunks.append(
                DocumentChunk(
                    chunk_id=c["chunk_id"],
                    document_id=c["document_id"],
                    filename=c["filename"],
                    page=c["page"],
                    section=c["section"],
                    text=c["text"],
                    chunk_index=c.get("chunk_index", 0),
                    token_count=len(c["text"].split()),
                    language=c_lang,
                    translated_text=translated_text
                )
            )

        logger.info(f"Hybrid retrieval returned {len(chunks)} chunks for query: '{query}'")
        return chunks

    def _expand_query(self, query: str, document_ids: Optional[List[str]] = None) -> List[str]:
        """Expands queries using domain keyword synonyms and cross-language translations."""
        queries = [query]
        q_lower = query.lower()

        # Include aligned English terms for languages where the offline
        # embedding fallback cannot reliably match the query's script.
        query_language = language_detector.detect(query).language_code
        if query_language != "en":
            translated_query = translation_service.translate(
                query, source_lang=query_language, target_lang="en"
            )
            if translated_query and translated_query != query:
                queries.append(translated_query)
                q_lower = f"{q_lower} {translated_query.lower()}"

        # Target language inspection from selected documents
        doc_langs = set()
        if document_ids:
            for did in document_ids:
                meta = registry.get(did)
                if meta and meta.language_code:
                    doc_langs.add(meta.language_code)

        # Financial expansions
        if "profit" in q_lower or "loss" in q_lower or "margin" in q_lower:
            queries.append("net income operating profit EBITDA margins expenses")
            if "hi" in doc_langs or not doc_langs:
                queries.append("शुद्ध लाभ लाभ मार्जिन")
            if "es" in doc_langs or not doc_langs:
                queries.append("beneficio neto ganancia neta")
            if "bn" in doc_langs:
                queries.append("নীট লাভ মুনাফা")
        if "revenue" in q_lower or "sales" in q_lower:
            queries.append("total revenue turnover segment sales growth")
            if "hi" in doc_langs or not doc_langs:
                queries.append("कुल राजस्व बिक्री")
            if "es" in doc_langs or not doc_langs:
                queries.append("ingresos totales ventas")
            if "bn" in doc_langs:
                queries.append("মোট রাজস্ব বিক্রয়")
        if "expense" in q_lower or "cost" in q_lower:
            queries.append("operating expenses expenditure procurement personnel")
            if "hi" in doc_langs:
                queries.append("संचालन व्यय खर्च")
            if "es" in doc_langs:
                queries.append("gastos operativos costos")
        if "risk" in q_lower or "threat" in q_lower:
            queries.append("risk factors compliance regulatory challenges volatility")
            if "hi" in doc_langs or not doc_langs:
                queries.append("जोखिम खतरा दायित्व")
            if "es" in doc_langs or not doc_langs:
                queries.append("riesgos amenazas responsabilidad")
            if "bn" in doc_langs:
                queries.append("ঝুঁকি বিপদ দায়")
        if "compare" in q_lower or "difference" in q_lower:
            queries.append(re.sub(r"(compare|difference between|versus|vs)", "", query, flags=re.IGNORECASE).strip())

        # Return unique non-empty queries
        return list(dict.fromkeys([q.strip() for q in queries if q.strip()]))

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenizer handling Latin and Unicode script characters."""
        return [w.lower() for w in re.findall(r"\b[\wÀ-ÿ\u0900-\u097F\u0980-\u09FF\u0600-\u06FF\u4E00-\u9FFF]{2,}\b", text)]

    def _compute_keyword_score(self, query_tokens: List[str], doc_tokens: List[str]) -> float:
        """Calculates normalized token overlap score."""
        if not query_tokens or not doc_tokens:
            return 0.0

        query_set = set(query_tokens)
        doc_set = set(doc_tokens)
        overlap = query_set.intersection(doc_set)
        
        return len(overlap) / len(query_set)


retriever = HybridRetriever()
