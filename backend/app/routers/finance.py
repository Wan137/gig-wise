"""Deterministic tax/EPF/SOCSO estimate for the dashboard - pure Python, no
LLM call at all.

The chat-based Financial Planner agent (app/graph/nodes/financial_planner.py)
uses these exact same calculators (app/finance/) to answer conversational
questions; this endpoint exists so the dashboard can show a real, instant,
zero-cost number from whatever the user has already told us (their tax
profile) and already logged (their expenses), without needing a chat turn or
an LLM round-trip at all.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.models import ExpenseRecord, TaxProfile, User
from app.db.session import get_db
from app.finance.planner import build_financial_plan
from app.schemas.finance import FinanceEstimate

router = APIRouter(prefix="/finance", tags=["finance"])

# Occupation sectors eligible for i-Saraan Plus rather than standard i-Saraan
# (see backend/app/rag/documents/kwsp_i_saraan_plus.txt).
_EHAILING_SECTORS = {"e_hailing", "delivery_rider", "p_hailing"}


def _age_from_dob(date_of_birth: datetime | None) -> int | None:
    if date_of_birth is None:
        return None
    today = datetime.now(timezone.utc).date()
    dob: date = date_of_birth.date() if isinstance(date_of_birth, datetime) else date_of_birth
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


@router.get("/estimate", response_model=FinanceEstimate)
def get_finance_estimate(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> FinanceEstimate:
    profile = db.query(TaxProfile).filter(TaxProfile.user_id == current_user.id).first()
    if profile is None or not profile.estimated_annual_income:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Set your estimated annual income in your tax profile first.",
        )

    deductible_records = (
        db.query(ExpenseRecord)
        .filter(ExpenseRecord.user_id == current_user.id, ExpenseRecord.tax_deductible.is_(True))
        .all()
    )
    annual_expenses = float(sum(float(r.amount) for r in deductible_records if r.amount is not None))

    plan = build_financial_plan(
        annual_income=float(profile.estimated_annual_income),
        annual_expenses=annual_expenses,
        is_ehailing_or_phailing_driver=profile.occupation_sector in _EHAILING_SECTORS,
        age=_age_from_dob(profile.date_of_birth),
    )

    return FinanceEstimate(
        assessment_year=plan.tax.assessment_year,
        gross_income=plan.tax.gross_income,
        allowable_expenses=plan.tax.allowable_expenses,
        chargeable_income=plan.tax.chargeable_income,
        tax_owed=plan.tax.tax_owed,
        effective_rate=plan.tax.effective_rate,
        monthly_set_aside=plan.tax.monthly_set_aside,
        cp500_instalment_amount=plan.tax.cp500_instalment_amount,
        epf_scheme=plan.epf.scheme,
        epf_eligible=plan.epf.eligible,
        epf_suggested_monthly_contribution=plan.epf.suggested_monthly_contribution,
        epf_expected_annual_incentive=plan.epf.expected_annual_incentive,
        socso_monthly_contribution=plan.socso.monthly_contribution,
        socso_annual_contribution=plan.socso.annual_contribution,
    )
