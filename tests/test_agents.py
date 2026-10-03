"""Test suite for specialized agents: Classifier, Planner, Financial, Verification, and Memory."""

import pytest
from app.agents.classifier_agent import classifier_agent
from app.agents.planner_agent import planner_agent
from app.agents.financial_agent import financial_agent
from app.agents.risk_agent import risk_agent
from app.agents.verification_agent import verification_agent
from app.models.schemas import DocumentChunk
from app.models.state import AgentState
from app.services.memory_service import memory_service
from app.tools.calculation_tools import calc_tool


def test_classifier_agent():
    # Test Financial
    res1 = classifier_agent.classify_document(
        "ApexCorp Solutions Limited. Total Revenue of INR 100 Cr, EBITDA 35 Cr, Net Profit 30 Cr.",
        "ApexCorp_Annual_Report_FY2024.pdf"
    )
    assert res1["document_type"] == "Annual Report"
    assert res1["domain"] == "Finance"
    assert res1["confidence"] >= 0.85

    # Test Invoice
    res2 = classifier_agent.classify_document(
        "Commercial Tax Invoice INV-9823. GSTIN: 27AABCA1234F1Z9. Grand Total: INR 45,31,200.",
        "Invoice_9823.pdf"
    )
    assert res2["document_type"] == "Commercial Invoice"

    # Test Research Paper
    res3 = classifier_agent.classify_document(
        "NeuralVision: Dynamic Multi-Scale Visual Reasoning with Sparse Transformers. Abstract: On ImageNet-1K, achieves 84.6% Top-1 accuracy with 34% lower FLOPs.",
        "paper.pdf"
    )
    assert res3["document_type"] == "Research Paper"


def test_planner_agent_intents():
    # Financial intent
    intent1, tasks1, agents1 = planner_agent.analyze_intent("Why did profit decrease in FY2025?")
    assert intent1 == "financial_analysis"
    assert "financial_agent" in agents1
    assert any("profit" in t for t in tasks1)

    # Comparison intent
    intent2, tasks2, agents2 = planner_agent.analyze_intent("What changed between 2024 and 2025?", active_doc_count=2)
    assert intent2 == "document_comparison"

    # Risk intent
    intent3, tasks3, agents3 = planner_agent.analyze_intent("What are the major risk factors?")
    assert intent3 == "risk_assessment"
    assert "risk_agent" in agents3

    # External research intent
    intent4, tasks4, agents4 = planner_agent.analyze_intent("How does revenue growth compare with the industry average?")
    assert intent4 == "external_research"
    assert "research_agent" in agents4


def test_calculation_tool():
    # YoY growth: 100 to 112
    res = calc_tool.execute(operation="yoy_growth", current=112.0, previous=100.0)
    assert res.success is True
    assert res.data["percentage_change"] == 12.0
    assert res.data["absolute_change"] == 12.0

    # Profit decline: 30 to 26
    res_decline = calc_tool.execute(operation="yoy_growth", current=26.0, previous=30.0)
    assert res_decline.success is True
    assert round(res_decline.data["percentage_change"], 2) == -13.33

    # Margin: 30 on 100
    res_margin = calc_tool.execute(operation="profit_margin", current=30.0, previous=100.0)
    assert res_margin.success is True
    assert res_margin.data["margin_percentage"] == 30.0


def test_verification_agent():
    chunk = DocumentChunk(
        chunk_id="c1",
        document_id="d1",
        filename="report.pdf",
        page=1,
        section="Finance",
        text="Total Revenue grew from 100.0 Cr to 112.0 Cr (+12.0%). Operating Expenses were 86.0 Cr."
    )
    state = AgentState(
        query="Verify revenue",
        retrieved_chunks=[chunk],
        explicit_facts=["Total Revenue grew from 100.0 Cr to 112.0 Cr", "Unicorns discovered on moon"]
    )
    res_state = verification_agent.run(state)
    assert len(res_state.verification_results) == 2
    
    # First claim should be verified
    assert res_state.verification_results[0].supported is True
    assert res_state.verification_results[0].confidence >= 0.85
    assert 1 in res_state.verification_results[0].source_pages

    # Second claim should be unsupported
    assert res_state.verification_results[1].supported is False
    assert res_state.verification_results[1].confidence < 0.50


def test_memory_service():
    session_id = "test_sess_01"
    memory_service.add_turn(
        session_id=session_id,
        query="What was ApexCorp FY2025 revenue?",
        resolved_query="What was ApexCorp FY2025 revenue?",
        answer="₹112 Crore",
        document_ids=["doc_001"],
        intent="financial_analysis"
    )

    # Follow up query
    resolved = memory_service.resolve_query(session_id, "And profit?")
    assert "ApexCorp FY2025 revenue" in resolved
    assert "And profit?" in resolved


if __name__ == "__main__":
    test_classifier_agent()
    test_planner_agent_intents()
    test_calculation_tool()
    test_verification_agent()
    test_memory_service()
    print("ALL AGENT UNIT TESTS PASSED!")
