"""Tests for the Verifier (guardrails) node.

The financial numeric check is pure Python (regex + set arithmetic against
the deterministic calculators) and needs no LLM, so it's tested exhaustively
here regardless of API quota. The groundedness judge is a real LLM call
(no mocking) and is skipped without a configured key, matching the rest of
the suite.
"""
from __future__ import annotations

import pytest

from app.config import get_settings
from app.finance.tax_calculator import calculate_tax
from app.graph.nodes.financial_planner import BREAKDOWN_DELIMITER
from app.graph.nodes.verifier import (
    ClaimAssessment,
    GroundednessJudgment,
    _numeric_ground_truth,
    _verify_and_fix_financial_numbers,
    _verify_groundedness,
    verifier_node,
)
from app.graph.state import initial_state

requires_groq = pytest.mark.skipif(
    not get_settings().groq_api_key, reason="GROQ_API_KEY not configured - skipping live LLM tests"
)


def _sample_tax_calc() -> dict:
    from dataclasses import asdict

    return asdict(calculate_tax(gross_income=48_000, allowable_expenses=6_000))


# --- Financial numeric check (pure Python, no LLM) --------------------------------


def test_ground_truth_set_includes_derived_monthly_and_annual_values():
    tax_calc = _sample_tax_calc()
    truth = _numeric_ground_truth(tax_calc, None)

    assert tax_calc["tax_owed"] in truth  # 140.0
    assert round(tax_calc["tax_owed"] / 12, 2) in truth  # a legitimate monthly restatement
    assert tax_calc["gross_income"] in truth  # 48000.0


def test_narration_matching_computed_numbers_passes_unchanged():
    tax_calc = _sample_tax_calc()
    breakdown = "**Tax estimate**\n- Estimated tax owed: RM140.00"
    narration = "Your estimated tax owed is RM140.00 for the year."
    text = f"{narration}{BREAKDOWN_DELIMITER}{breakdown}"

    fixed_text, check = _verify_and_fix_financial_numbers(text, tax_calc, None)

    assert check["passed"] is True
    assert "RM140.00" in fixed_text
    assert narration in fixed_text  # narration was kept, not discarded


def test_narration_with_fabricated_number_is_discarded():
    tax_calc = _sample_tax_calc()  # tax_owed = 140.0
    breakdown = "**Tax estimate**\n- Estimated tax owed: RM140.00"
    narration = "Your total tax would be RM1,020.00 based on my calculation."  # fabricated, wrong
    text = f"{narration}{BREAKDOWN_DELIMITER}{breakdown}"

    fixed_text, check = _verify_and_fix_financial_numbers(text, tax_calc, None)

    assert check["passed"] is False
    assert "1,020" not in fixed_text  # the fabricated figure must not reach the user
    assert "RM140.00" in fixed_text  # the correct breakdown is still shown


def test_missing_delimiter_treats_whole_text_as_narration():
    tax_calc = _sample_tax_calc()
    text = "Your tax owed is RM140.00, nice and simple."  # no BREAKDOWN_DELIMITER at all

    fixed_text, check = _verify_and_fix_financial_numbers(text, tax_calc, None)

    assert check["passed"] is True
    assert "RM140.00" in fixed_text


def test_epf_socso_figures_are_also_checked():
    epf_socso = {
        "epf_scheme": "i-Saraan",
        "epf_suggested_annual_contribution": 2_500.0,
        "epf_suggested_monthly_contribution": 208.33,
    }
    narration = "You should contribute RM99,999.00 monthly to EPF."  # fabricated
    text = f"{narration}{BREAKDOWN_DELIMITER}(breakdown here)"

    _, check = _verify_and_fix_financial_numbers(text, None, epf_socso)
    assert check["passed"] is False


# --- verifier_node orchestration (pure Python paths) --------------------------------


def test_verifier_node_passes_through_when_no_segments_ran():
    state = initial_state(user_id="u1", session_id="s1", user_message="hi")
    result = verifier_node(state)

    assert result["verification"]["passed"] is True
    assert result["verification"]["checks"] == []
    assert "draft_answer" not in result  # leaves it unset so responder's direct-reply path fires


def test_verifier_node_skips_numeric_check_when_no_plan_computed():
    state = initial_state(user_id="u1", session_id="s1", user_message="hi")
    state["draft_segments"] = [{"agent": "financial_planner", "text": "some text, no plan attached"}]
    # tax_calc / epf_socso both left None - nothing to check against

    result = verifier_node(state)

    assert result["verification"]["checks"] == []
    assert result["draft_answer"] == "some text, no plan attached"


def test_verifier_node_passes_through_expense_tracker_segments_unchanged():
    state = initial_state(user_id="u1", session_id="s1", user_message="hi")
    state["draft_segments"] = [{"agent": "expense_tracker", "text": "Logged RM50.00 at Shell as fuel."}]

    result = verifier_node(state)

    assert result["draft_answer"] == "Logged RM50.00 at Shell as fuel."
    assert result["verification"]["passed"] is True


def test_verifier_node_fails_closed_when_tax_advisor_has_no_retrieved_chunks():
    # No retrieved_chunks were set on the state (e.g. RAG found no matches) -
    # there's nothing to check the claim against, so this must not silently
    # pass the segment through as if it were verified.
    state = initial_state(user_id="u1", session_id="s1", user_message="hi")
    state["draft_segments"] = [{"agent": "tax_advisor", "text": "Gig workers pay a flat 2% rate."}]
    assert not state.get("retrieved_chunks")

    result = verifier_node(state)

    assert result["verification"]["passed"] is False
    assert result["verification"]["flagged_for_review"] is True
    assert "double-check" in result["draft_answer"].lower()


# --- Groundedness bucketing (mocked judge, no LLM/API key required) ----------------


class _FakeStructuredJudge:
    def __init__(self, judgment: GroundednessJudgment) -> None:
        self._judgment = judgment

    def invoke(self, _messages):
        return self._judgment


class _FakeLLM:
    def __init__(self, judgment: GroundednessJudgment) -> None:
        self._judgment = judgment

    def with_structured_output(self, _schema):
        return _FakeStructuredJudge(self._judgment)


def test_partially_supported_claims_are_treated_as_unverified(monkeypatch):
    # partially_supported means the claim blends true information with an
    # unsupported inference (see verifier_prompts.py) - it must not be
    # bucketed with "supported" and passed through disclaimer-free.
    judgment = GroundednessJudgment(
        claims=[ClaimAssessment(claim="Gig income is taxed at your normal rate.", verdict="supported")],
    )
    judgment.claims.append(
        ClaimAssessment(claim="...and e-hailing drivers get an extra RM5,000 relief.", verdict="partially_supported")
    )
    monkeypatch.setattr("app.graph.nodes.verifier.get_llm", lambda **_: _FakeLLM(judgment))

    text = "Gig income is taxed at your normal rate, and e-hailing drivers get an extra RM5,000 relief."
    chunks = [{"source_document": "LHDN Guide", "section": "Overview", "content": "Gig income is taxed at your normal rate."}]

    fixed_text, check, grounded = _verify_groundedness(text, chunks)

    assert grounded is False
    assert check["passed"] is False
    assert "extra RM5,000 relief" in fixed_text  # the unverified claim is named in the disclaimer
    assert "double-check" in fixed_text.lower()


# --- Groundedness judge (real LLM call) ---------------------------------------------


@requires_groq
def test_groundedness_flags_a_claim_not_in_any_source_chunk():
    chunks = [
        {
            "source_document": "LHDN: Resident Individual Tax Rate Schedule",
            "section": "Overview",
            "content": "Resident individuals are taxed progressively from 0% to 30% depending on chargeable income.",
        }
    ]
    # A specific, invented rate/rule that doesn't appear in the chunk above.
    text = "Gig workers get a special flat 2% tax rate exclusive to e-hailing drivers [Source: test]."

    fixed_text, check, grounded = _verify_groundedness(text, chunks)

    assert grounded is False
    assert check["passed"] is False
    assert "double-check" in fixed_text.lower()


@requires_groq
def test_groundedness_passes_when_answer_only_restates_the_chunk():
    chunks = [
        {
            "source_document": "LHDN: Resident Individual Tax Rate Schedule",
            "section": "Overview",
            "content": "A resident individual whose chargeable income does not exceed RM35,000 receives a rebate of RM400.",
        }
    ]
    text = "If your chargeable income is RM35,000 or less, you receive a RM400 tax rebate."

    _, check, grounded = _verify_groundedness(text, chunks)

    assert grounded is True
    assert check["passed"] is True
