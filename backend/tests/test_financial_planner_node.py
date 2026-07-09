"""Integration tests for the financial_planner graph node.

Input extraction and narration call the real Groq API (skipped without a
key, matching the rest of the suite); the numbers themselves are produced by
the same deterministic calculators already covered by
test_finance_calculators.py, so these tests focus on the extraction ->
calculation -> narration wiring, not re-deriving the arithmetic.
"""
from __future__ import annotations

import pytest

from app.config import get_settings
from app.graph.graph import get_compiled_graph
from app.graph.nodes.financial_planner import financial_planner_node
from app.graph.state import initial_state

pytestmark = pytest.mark.skipif(
    not get_settings().groq_api_key, reason="GROQ_API_KEY not configured - skipping live LLM tests"
)


def test_extracts_income_and_computes_correct_tax():
    state = initial_state(
        user_id="u1",
        session_id="s1",
        user_message="I earn about RM4000 a month as an e-hailing driver, with RM500 a month in expenses.",
    )
    result = financial_planner_node(state)

    tax_calc = result["tax_calc"]
    assert tax_calc["gross_income"] == 48_000.0
    assert tax_calc["allowable_expenses"] == 6_000.0
    assert tax_calc["tax_owed"] == 140.0  # matches test_finance_calculators.py's hand-verified case

    epf_socso = result["epf_socso"]
    assert epf_socso["epf_scheme"] == "i-Saraan Plus"  # correctly detected as an e-hailing driver

    assert "RM140.00" in result["draft_answer"]  # deterministic breakdown block is always present


def test_asks_for_income_when_none_mentioned():
    state = initial_state(user_id="u1", session_id="s1", user_message="How much should I save for tax?")
    result = financial_planner_node(state)

    assert result.get("tax_calc") is None
    assert "income" in result["draft_answer"].lower()


def test_uses_logged_expenses_from_same_turn_when_not_restated():
    state = initial_state(user_id="u1", session_id="s1", user_message="I make RM5000 a month, what's my tax?")
    state["expense_records"] = [
        {"id": "1", "category": "fuel", "amount": 200.0, "tax_deductible": True},
        {"id": "2", "category": "personal_non_deductible", "amount": 300.0, "tax_deductible": False},
    ]
    result = financial_planner_node(state)

    # Only the deductible expense record should count, and it's a monthly amount that
    # should NOT be silently annualized (it came from expense_records, not the message).
    assert result["tax_calc"]["allowable_expenses"] == 200.0


def test_full_graph_routes_financial_planning_question_correctly():
    graph = get_compiled_graph()
    state = initial_state(
        user_id="u1",
        session_id="s1",
        user_message="I make RM10000 a month as a freelance designer with no expenses. What's my tax?",
    )
    result = graph.invoke(state)

    assert "financial_planner" in [t["node"] for t in result["trace"]]
    assert result["tax_calc"]["tax_owed"] == 12_150.0  # hand-verified in test_finance_calculators.py
    assert "RM12,150.00" in result["final_answer"]
