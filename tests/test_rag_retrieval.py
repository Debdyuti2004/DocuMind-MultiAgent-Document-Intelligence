"""Test suite for Phase 2: Embeddings, ChromaDB, and Hybrid Retrieval."""

from pathlib import Path
import pytest
from app.document.parser import DocumentParser
from app.document.chunker import HierarchicalChunker
from app.rag.embeddings import embedding_service
from app.rag.vector_store import VectorStore
from app.rag.retriever import HybridRetriever

SAMPLE_DIR = Path("data/sample_docs")


def test_embeddings_generation():
    texts = ["Revenue increased by 12% in FY2025.", "The model achieved 84.6% accuracy."]
    embeddings = embedding_service.embed_texts(texts)
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 384
    
    query_emb = embedding_service.embed_query("profit growth")
    assert len(query_emb) == 384


def test_vector_store_indexing_and_search():
    test_db_path = Path("data/chroma_test")
    vs = VectorStore(chroma_path=test_db_path, collection_name="test_collection")

    doc1_path = SAMPLE_DIR / "ApexCorp_Annual_Report_FY2024.pdf"
    pages1, tables1, meta1 = DocumentParser.parse(doc1_path, "doc_test_2024")
    chunker = HierarchicalChunker(chunk_size=400, chunk_overlap=50)
    chunks1 = chunker.chunk_document("doc_test_2024", doc1_path.name, pages1)

    doc2_path = SAMPLE_DIR / "ApexCorp_Annual_Report_FY2025.pdf"
    pages2, tables2, meta2 = DocumentParser.parse(doc2_path, "doc_test_2025")
    chunks2 = chunker.chunk_document("doc_test_2025", doc2_path.name, pages2)

    indexed1 = vs.add_chunks(chunks1)
    indexed2 = vs.add_chunks(chunks2)
    assert indexed1 == len(chunks1)
    assert indexed2 == len(chunks2)
    assert vs.count() == len(chunks1) + len(chunks2)

    # Search specifically in 2024
    results_2024 = vs.search(query="Revenue of FY2024", top_k=3, document_ids=["doc_test_2024"])
    assert len(results_2024) > 0
    assert all(r["document_id"] == "doc_test_2024" for r in results_2024)

    # Multi-document search (comparison query)
    multi_results = vs.search(query="Compare profit and expenses", top_k=5, document_ids=["doc_test_2024", "doc_test_2025"])
    assert len(multi_results) > 0


def test_hybrid_retriever():
    retriever = HybridRetriever(top_k=3)
    results = retriever.retrieve(query="Why did net profit decrease in FY2025?")
    assert isinstance(results, list)
    # Check that returned elements are DocumentChunk with page and section metadata
    for r in results:
        assert r.page in [1, 2]
        assert len(r.text) > 0
        assert r.filename != ""


if __name__ == "__main__":
    test_embeddings_generation()
    test_vector_store_indexing_and_search()
    test_hybrid_retriever()
    print("ALL PHASE 2 RAG TESTS PASSED!")
