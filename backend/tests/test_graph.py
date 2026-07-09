"""Integration tests for the compiled LangGraph copilot graph.

These call the real Groq API (no LLM mocking) because the point of this
suite is to verify the orchestrator's routing and the Tax Advisor's grounding
actually work against a real model, not that our Python glue code is
internally consistent. They're skipped automatically if no GROQ_API_KEY is
configured, so the rest of the suite still runs in an environment without one.
"""
from __future__ import annotations

import pytest

from app.config import get_settings
from app.graph.graph import get_compiled_graph
from app.graph.state import initial_state

pytestmark = pytest.mark.skipif(
    not get_settings().groq_api_key, reason="GROQ_API_KEY not configured - skipping live LLM integration tests"
)


@pytest.fixture(scope="module")
def graph():
    return get_compiled_graph()


def _run(graph, message: str) -> dict:
    state = initial_state(user_id="test-user", session_id="test-session", user_message=message)
    return graph.invoke(state)


def _trace_nodes(result: dict) -> list[str]:
    return [t["node"] for t in result["trace"]]


def test_general_greeting_does_not_invoke_specialist_agents(graph):
    result = _run(graph, "Hi, what can you help me with?")
    assert result["intent"] == "general"
    assert "tax_advisor" not in _trace_nodes(result)
    assert result["final_answer"]


def test_tax_question_routes_to_tax_advisor_and_cites_a_source(graph):
    result = _run(graph, "Do I need to file taxes as an e-hailing driver earning RM4000 a month?")
    assert result["intent"] == "tax_question"
    assert "tax_advisor" in _trace_nodes(result)
    assert result["retrieved_chunks"], "tax_advisor should have retrieved at least one source chunk"
    assert "[Source:" in result["final_answer"], "answer should cite at least one source inline"


def test_expense_deduction_question_grounds_in_allowable_expenses_doc(graph):
    result = _run(graph, "Can I claim my phone bill as a business expense?")
    assert result["intent"] == "tax_question"
    source_docs = [c["source_document"] for c in result["retrieved_chunks"]]
    assert any("Allowable" in doc or "Form B" in doc for doc in source_docs)


def test_isaraan_plus_question_grounds_in_correct_document(graph):
    result = _run(graph, "How does i-Saraan Plus work for e-hailing drivers?")
    source_docs = [c["source_document"] for c in result["retrieved_chunks"]]
    assert any("i-Saraan Plus" in doc for doc in source_docs)


def test_unimplemented_agent_degrades_gracefully_instead_of_crashing(graph):
    # financial_planning isn't built yet (Task 6); expense_entry is (Task 5) and, since no
    # receipt image is actually attached to this text-only message, correctly asks for one
    # rather than fabricating a logged expense.
    result = _run(
        graph, "How much should I set aside every month for tax? Also log a RM50 fuel receipt for me."
    )
    assert result["intent"] == "multi"
    assert result["final_answer"]
    assert "Financial Planner" in result["final_answer"]
    assert "available yet" in result["final_answer"]
    assert "upload a photo" in result["final_answer"].lower()
