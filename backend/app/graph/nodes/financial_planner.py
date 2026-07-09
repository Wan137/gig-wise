"""Extracts numeric inputs via LLM, computes the plan via deterministic Python,
and has the LLM narrate (never invent) the already-computed numbers.
"""
from __future__ import annotations

import logging
from dataclasses import asdict

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.finance.planner import build_financial_plan, render_plan_breakdown
from app.graph.llm import get_llm
from app.graph.prompts.financial_planner_prompts import EXTRACTION_SYSTEM_PROMPT, NARRATION_SYSTEM_PROMPT
from app.graph.state import CopilotState, EPFSocsoResult, TaxCalculationResult
from app.graph.utils import append_draft, latest_user_message, make_trace

logger = logging.getLogger(__name__)

_CLARIFY_INCOME_MESSAGE = (
    "To estimate your tax and contributions accurately, I need to know your income - could you tell me "
    "roughly how much you earn per month or per year?"
)
_CALCULATION_FAILED_MESSAGE = (
    "I couldn't calculate an estimate from those figures - please double check the income/expense "
    "amounts and try again."
)
_FALLBACK_NARRATION = "Here's your estimate based on the figures you gave me:"


class FinancialPlanningRequest(BaseModel):
    monthly_income: float | None = None
    annual_income: float | None = None
    monthly_expenses: float | None = None
    annual_expenses: float | None = None
    is_ehailing_or_phailing_driver: bool = Field(default=False)
    age: int | None = None


def _tax_calc_to_state(tax) -> TaxCalculationResult:
    data = asdict(tax)
    return TaxCalculationResult(**data)


def _epf_socso_to_state(epf, socso) -> EPFSocsoResult:
    return EPFSocsoResult(
        epf_scheme=epf.scheme,
        epf_suggested_annual_contribution=epf.suggested_annual_contribution,
        epf_suggested_monthly_contribution=epf.suggested_monthly_contribution,
        epf_expected_annual_incentive=epf.expected_annual_incentive,
        epf_lifetime_incentive_cap=epf.lifetime_incentive_cap,
        socso_matched_insured_monthly_earning=socso.matched_insured_monthly_earning,
        socso_monthly_contribution=socso.monthly_contribution,
        socso_annual_contribution=socso.annual_contribution,
        socso_note=socso.note,
    )


def _sum_deductible_expenses(state: CopilotState) -> float:
    records = state.get("expense_records") or []
    amounts = [r["amount"] for r in records if r.get("tax_deductible") and r.get("amount")]
    return float(sum(amounts))


def financial_planner_node(state: CopilotState) -> dict:
    trace = make_trace("financial_planner", "Calculating your estimate...")

    try:
        extractor = get_llm(temperature=0.0).with_structured_output(FinancialPlanningRequest)
        request = extractor.invoke([SystemMessage(content=EXTRACTION_SYSTEM_PROMPT), *state["messages"]])
    except Exception:
        logger.exception("Input extraction LLM call failed in financial_planner_node")
        return {"draft_answer": append_draft(state, _CLARIFY_INCOME_MESSAGE), "trace": trace}

    annual_income = request.annual_income or (
        request.monthly_income * 12 if request.monthly_income else None
    )
    if not annual_income or annual_income <= 0:
        return {"draft_answer": append_draft(state, _CLARIFY_INCOME_MESSAGE), "trace": trace}

    annual_expenses = request.annual_expenses or (
        request.monthly_expenses * 12 if request.monthly_expenses else None
    )
    if annual_expenses is None:
        annual_expenses = _sum_deductible_expenses(state)

    try:
        plan = build_financial_plan(
            annual_income=annual_income,
            annual_expenses=annual_expenses,
            is_ehailing_or_phailing_driver=request.is_ehailing_or_phailing_driver,
            age=request.age,
        )
    except ValueError:
        logger.exception("Financial plan calculation failed in financial_planner_node")
        return {"draft_answer": append_draft(state, _CALCULATION_FAILED_MESSAGE), "trace": trace}

    breakdown = render_plan_breakdown(plan)

    try:
        narrator = get_llm(temperature=0.3)
        response = narrator.invoke(
            [
                SystemMessage(content=NARRATION_SYSTEM_PROMPT.format(breakdown=breakdown)),
                HumanMessage(content=latest_user_message(state)),
            ]
        )
        narration = response.content if isinstance(response.content, str) else str(response.content)
    except Exception:
        logger.exception("Narration LLM call failed in financial_planner_node")
        narration = _FALLBACK_NARRATION

    combined_text = f"{narration}\n\n{breakdown}"

    return {
        "tax_calc": _tax_calc_to_state(plan.tax),
        "epf_socso": _epf_socso_to_state(plan.epf, plan.socso),
        "draft_answer": append_draft(state, combined_text),
        "trace": trace,
    }
