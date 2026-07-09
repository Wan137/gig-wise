"""Combines the tax and EPF/SOCSO calculators into a single financial plan,
and renders a deterministic breakdown block that is shown to the user
verbatim regardless of what an LLM says about it elsewhere in the reply -
this block is what the Verifier (Task 7) treats as ground truth.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.finance.epf_socso_calculator import (
    EpfSuggestion,
    SocsoSuggestion,
    suggest_epf_contribution,
    suggest_socso_contribution,
)
from app.finance.tax_calculator import TaxCalculation, calculate_tax


@dataclass
class FinancialPlan:
    tax: TaxCalculation
    epf: EpfSuggestion
    socso: SocsoSuggestion


def build_financial_plan(
    annual_income: float,
    annual_expenses: float = 0.0,
    is_ehailing_or_phailing_driver: bool = False,
    age: int | None = None,
) -> FinancialPlan:
    tax = calculate_tax(gross_income=annual_income, allowable_expenses=annual_expenses)
    epf = suggest_epf_contribution(is_ehailing_or_phailing_driver=is_ehailing_or_phailing_driver, age=age)
    socso = suggest_socso_contribution(estimated_monthly_earning=annual_income / 12)
    return FinancialPlan(tax=tax, epf=epf, socso=socso)


def render_plan_breakdown(plan: FinancialPlan) -> str:
    tax = plan.tax
    lines = [
        f"**Tax estimate (YA{tax.assessment_year})**",
        f"- Gross income: RM{tax.gross_income:,.2f}",
        f"- Allowable expenses: RM{tax.allowable_expenses:,.2f}",
        f"- Reliefs applied: RM{tax.reliefs_applied:,.2f}",
        f"- Chargeable income: RM{tax.chargeable_income:,.2f}",
    ]
    if tax.rebate_applied:
        lines.append(f"- Tax before rebate: RM{tax.tax_before_rebate:,.2f}")
        lines.append(f"- Rebate applied: -RM{tax.rebate_applied:,.2f}")
    lines.append(f"- **Estimated tax owed: RM{tax.tax_owed:,.2f}** (effective rate {tax.effective_rate * 100:.2f}%)")
    lines.append(f"- Suggested monthly set-aside: RM{tax.monthly_set_aside:,.2f}")
    lines.append(
        f"- CP500 bi-monthly instalment estimate: RM{tax.cp500_instalment_amount:,.2f} x 6 payments/year "
        "(LHDN's advance tax scheme for the self-employed is bi-monthly, not quarterly)"
    )

    epf = plan.epf
    lines.append("")
    lines.append(f"**EPF {epf.scheme}**")
    if epf.eligible:
        lines.append(
            f"- Suggested contribution: RM{epf.suggested_annual_contribution:,.2f}/year "
            f"(RM{epf.suggested_monthly_contribution:,.2f}/month) to earn the maximum "
            f"RM{epf.expected_annual_incentive:,.2f}/year government incentive"
        )
        lines.append(f"- Lifetime incentive cap: RM{epf.lifetime_incentive_cap:,.2f}")
    else:
        lines.append(f"- {epf.note}")

    socso = plan.socso
    lines.append("")
    lines.append("**SOCSO SKSPS**")
    lines.append(f"- Matched tier: RM{socso.matched_insured_monthly_earning:,.2f} insured monthly earning")
    lines.append(f"- Contribution: RM{socso.monthly_contribution:,.2f}/month (RM{socso.annual_contribution:,.2f}/year)")
    lines.append(f"- {socso.note}")

    return "\n".join(lines)
