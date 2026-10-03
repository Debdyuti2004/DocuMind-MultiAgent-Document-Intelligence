"""End-to-end integration tests for multi-agent orchestrator, comparison, and guardrails."""

from pathlib import Path
import pytest
from app.agents.orchestrator import orchestrator
from app.document.metadata import registry
from app.rag.vector_store import vector_store
from app.services.document_service import document_service

SAMPLE_DIR = Path("data/sample_docs")


@pytest.fixture(scope="module")
def ingested_documents():
    pdf1 = SAMPLE_DIR / "ApexCorp_Annual_Report_FY2024.pdf"
    pdf2 = SAMPLE_DIR / "ApexCorp_Annual_Report_FY2025.pdf"
    
    meta1, summary1 = document_service.ingest_document(pdf1)
    meta2, summary2 = document_service.ingest_document(pdf2)
    
    yield {
        "doc1": meta1,
        "doc2": meta2,
        "summary1": summary1,
        "summary2": summary2
    }
    for meta in (meta1, meta2):
        vector_store.delete_document(meta.document_id)
        registry.delete(meta.document_id)
        (Path("data/processed") / f"{meta.document_id}_summary.json").unlink(missing_ok=True)


def test_automatic_summary_generation(ingested_documents):
    s1 = ingested_documents["summary1"]
    assert s1.document_type == "Annual Report"
    assert len(s1.key_facts) >= 2
    assert len(s1.suggested_questions) >= 3
    assert "Organizations" in s1.key_entities


def test_orchestrator_financial_query(ingested_documents):
    doc1_id = ingested_documents["doc1"].document_id
    doc2_id = ingested_documents["doc2"].document_id

    state = orchestrator.process_query(
        query="Why did net profit decline in FY2025?",
        document_ids=[doc1_id, doc2_id],
        session_id="test_integ_01"
    )

    # 1. Intent & Planning
    assert state.intent in ("financial_analysis", "document_comparison")
    assert len(state.plan) >= 4

    # 2. Retrieval
    assert len(state.retrieved_chunks) > 0

    # 3. Financial calculations
    assert len(state.derived_calculations) > 0
    metric_names = [c.get("metric", "") for c in state.derived_calculations]
    assert any("Revenue" in m or "Operating Expense" in m or "Profit" in m or "Driver" in m for m in metric_names)
    revenue = next(item for item in state.derived_calculations if item["metric"].startswith("Revenue"))
    assert [item["value"] for item in revenue["sources"]] == [100.0, 112.0]

    # 4. Verification
    assert len(state.verification_results) > 0
    assert any(v.supported for v in state.verification_results)
    # Confidence is the exact evidence-match share, so a Medium score can be
    # valid when some extracted excerpts or comparisons are not exact matches.
    assert state.confidence_score >= 0.50
    assert state.confidence_level in ("High", "Medium")

    # 5. Final Answer & Citations
    assert state.final_answer is not None
    assert "Source excerpts" in state.final_answer
    assert "Sources" in state.final_answer

    # 6. Observability & Agent Logs
    agent_names_logged = {log.agent_name for log in state.agent_logs}
    assert "Planner Agent" in agent_names_logged
    assert "Retrieval Agent" in agent_names_logged
    assert "Financial Analysis Agent" in agent_names_logged
    assert "Reasoning Agent" in agent_names_logged
    assert "Verification Agent" in agent_names_logged
    assert "Response Generation Agent" in agent_names_logged


def test_multi_document_comparison(ingested_documents):
    doc1_id = ingested_documents["doc1"].document_id
    doc2_id = ingested_documents["doc2"].document_id

    comp = document_service.compare_documents(doc1_id, doc2_id)
    assert [item.metric for item in comp.metrics] == ["Revenue"]
    assert [comp.metrics[0].doc1_value, comp.metrics[0].doc2_value] == [100.0, 112.0]
    assert len(comp.citations) >= 2
    assert "Revenue" in comp.key_differences[0]
    assert comp.metrics[0].change_percent == 12.0


def test_anti_hallucination_guardrail(ingested_documents):
    doc1_id = ingested_documents["doc1"].document_id

    state = orchestrator.process_query(
        query="What is the secret recipe for Martian space fuel and alien propulsion?",
        document_ids=[doc1_id],
        session_id="test_guardrail_01"
    )

    # Must invoke guardrail response rather than making up answers
    assert "Insufficient Evidence" in state.final_answer or "insufficient evidence" in state.final_answer.lower()
