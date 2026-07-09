"""Guardrails layer: checks each specialist's segment against its own ground
truth before anything reaches the user.

Two independent, mechanical checks - not "ask the LLM if it's sure":

- tax_advisor segments are checked for groundedness: a second LLM call acts
  as a fact-checking judge, comparing each claim in the segment against the
  actual retrieved source chunks. Any unsupported claim gets a visible
  disclaimer rather than being silently presented as settled fact.
- financial_planner segments are checked numerically: every RM figure
  mentioned in the narration is cross-checked against the deterministic
  tax_calc/epf_socso values (plus their legitimate monthly/annual
  restatements). Any figure that doesn't match is a fabrication, and the
  narration is discarded in favor of the always-correct breakdown block -
  the LLM is never the source of a number that reaches the user.

Other segment types (expense_tracker, not_implemented) pass through
unchanged - their content isn't open-ended generated prose, so there's
nothing here to check.
"""
from __future__ import annotations

import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.graph.llm import get_llm
from app.graph.nodes.financial_planner import BREAKDOWN_DELIMITER
from app.graph.prompts.verifier_prompts import GROUNDEDNESS_JUDGE_SYSTEM_PROMPT
from app.graph.state import CopilotState, EPFSocsoResult, TaxCalculationResult
from app.graph.utils import make_trace

logger = logging.getLogger(__name__)

_RM_PATTERN = re.compile(r"RM\s*([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)
_NUMERIC_TOLERANCE = 0.5  # RM - covers rounding differences only, not real discrepancies

_UNVERIFIED_TAX_DISCLAIMER = (
    "\n\n⚠️ **Please double-check before relying on this**: I couldn't fully verify the following "
    "statement(s) against my official sources - confirm with LHDN (hasil.gov.my), KWSP, PERKESO, or a "
    "licensed tax agent:\n"
)


class ClaimAssessment(BaseModel):
    claim: str
    verdict: str  # "supported" | "unsupported" | "partially_supported"


class GroundednessJudgment(BaseModel):
    claims: list[ClaimAssessment]


def _verify_groundedness(text: str, retrieved_chunks: list[dict]) -> tuple[str, dict, bool]:
    chunks_block = "\n\n".join(
        f"[{i + 1}] {c['source_document']} ({c['section']}): {c['content']}"
        for i, c in enumerate(retrieved_chunks)
    )

    try:
        judge = get_llm(temperature=0.0).with_structured_output(GroundednessJudgment)
        judgment = judge.invoke(
            [
                SystemMessage(
                    content=GROUNDEDNESS_JUDGE_SYSTEM_PROMPT.format(chunks=chunks_block, answer=text)
                ),
                HumanMessage(content="Assess the answer above against the source chunks."),
            ]
        )
    except Exception:
        # Fail closed: if the checker itself is unavailable, don't silently
        # ship an unchecked tax answer - flag it rather than assume it's fine.
        logger.exception("Groundedness judge call failed")
        check = {
            "check": "tax_groundedness",
            "passed": False,
            "detail": "Automatic verification was unavailable for this answer.",
        }
        disclaimer = _UNVERIFIED_TAX_DISCLAIMER + "- (automatic verification could not run)"
        return text + disclaimer, check, False

    unsupported = [c.claim for c in judgment.claims if c.verdict == "unsupported"]
    check = {
        "check": "tax_groundedness",
        "passed": not unsupported,
        "detail": f"{len(judgment.claims)} claim(s) checked; unsupported: {unsupported}",
    }

    if not unsupported:
        return text, check, True

    disclaimer = _UNVERIFIED_TAX_DISCLAIMER + "\n".join(f"- {claim}" for claim in unsupported)
    return text + disclaimer, check, False


def _numeric_ground_truth(tax_calc: TaxCalculationResult | None, epf_socso: EPFSocsoResult | None) -> set[float]:
    values: set[float] = set()

    if tax_calc:
        money_fields = (
            "gross_income",
            "allowable_expenses",
            "adjusted_income",
            "reliefs_applied",
            "chargeable_income",
            "tax_before_rebate",
            "rebate_applied",
            "tax_owed",
            "monthly_set_aside",
            "cp500_instalment_amount",
        )
        for field in money_fields:
            value = tax_calc.get(field)
            if value is not None:
                values.add(round(float(value), 2))
                values.add(round(float(value) / 12, 2))  # a legitimate monthly restatement of an annual figure
                values.add(round(float(value) * 12, 2))  # or an annual restatement of a monthly one
        for band in tax_calc.get("bracket_breakdown") or []:
            for key in ("amount_in_band", "tax_for_band"):
                if band.get(key) is not None:
                    values.add(round(float(band[key]), 2))

    if epf_socso:
        for field in (
            "epf_suggested_annual_contribution",
            "epf_suggested_monthly_contribution",
            "epf_expected_annual_incentive",
            "epf_lifetime_incentive_cap",
            "socso_matched_insured_monthly_earning",
            "socso_monthly_contribution",
            "socso_annual_contribution",
        ):
            value = epf_socso.get(field)
            if value is not None:
                values.add(round(float(value), 2))

    return values


def _verify_and_fix_financial_numbers(
    text: str, tax_calc: TaxCalculationResult | None, epf_socso: EPFSocsoResult | None
) -> tuple[str, dict]:
    if BREAKDOWN_DELIMITER in text:
        narration, breakdown = text.split(BREAKDOWN_DELIMITER, 1)
    else:
        narration, breakdown = text, ""

    ground_truth = _numeric_ground_truth(tax_calc, epf_socso)
    mentioned = [float(m.replace(",", "")) for m in _RM_PATTERN.findall(narration)]
    mismatches = [
        value for value in mentioned if not any(abs(value - truth) <= _NUMERIC_TOLERANCE for truth in ground_truth)
    ]

    if not mismatches:
        check = {
            "check": "financial_numeric_grounding",
            "passed": True,
            "detail": f"{len(mentioned)} figure(s) in the narration all match the computed plan.",
        }
        return f"{narration}\n\n{breakdown}".strip(), check

    check = {
        "check": "financial_numeric_grounding",
        "passed": False,
        "detail": f"Discarded narration - it mentioned RM figures not found in the computed plan: {mismatches}",
    }
    safe_text = "Here's your computed financial plan:\n\n" + breakdown if breakdown else narration
    return safe_text, check


def verifier_node(state: CopilotState) -> dict:
    trace = make_trace("verifier", "Double-checking the numbers...")
    segments = state.get("draft_segments") or []

    if not segments:
        # Nothing ran this turn (pure general chit-chat) - leave draft_answer
        # unset so the responder's direct-reply fallback path triggers.
        return {
            "verification": {"passed": True, "checks": [], "flagged_for_review": False},
            "trace": trace,
        }

    checks: list[dict] = []
    flagged = False
    final_texts: list[str] = []

    for segment in segments:
        agent = segment["agent"]
        text = segment["text"]

        if agent == "tax_advisor" and state.get("retrieved_chunks"):
            text, check, grounded = _verify_groundedness(text, state["retrieved_chunks"])
            checks.append(check)
            if not grounded:
                flagged = True

        elif agent == "financial_planner" and (state.get("tax_calc") or state.get("epf_socso")):
            text, check = _verify_and_fix_financial_numbers(text, state.get("tax_calc"), state.get("epf_socso"))
            checks.append(check)
            # Numeric mismatches are auto-corrected by construction (we fall
            # back to the always-correct breakdown), so this doesn't need to
            # flag_for_review the way an unresolved groundedness issue does.

        final_texts.append(text)

    return {
        "draft_answer": "\n\n".join(final_texts),
        "verification": {"passed": not flagged, "checks": checks, "flagged_for_review": flagged},
        "trace": trace,
    }
