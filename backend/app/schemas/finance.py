from __future__ import annotations

from pydantic import BaseModel


class FinanceEstimate(BaseModel):
    assessment_year: int
    gross_income: float
    allowable_expenses: float
    chargeable_income: float
    tax_owed: float
    effective_rate: float
    monthly_set_aside: float
    cp500_instalment_amount: float

    epf_scheme: str
    epf_eligible: bool
    epf_suggested_monthly_contribution: float
    epf_expected_annual_incentive: float

    socso_monthly_contribution: float
    socso_annual_contribution: float
