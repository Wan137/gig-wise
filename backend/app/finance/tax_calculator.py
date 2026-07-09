"""Deterministic progressive tax calculation - no LLM involved.

Every number here is produced by plain arithmetic against the sourced
constants in app/finance/constants.py, so the result is reproducible and
independently checkable, unlike an LLM-generated figure.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.finance.constants import (
    AUTOMATIC_PERSONAL_RELIEF,
    CP500_INSTALMENTS_PER_YEAR,
    REBATE_AMOUNT,
    REBATE_CHARGEABLE_INCOME_THRESHOLD,
    SUPPORTED_ASSESSMENT_YEAR,
    TAX_BRACKETS,
)


@dataclass
class BracketContribution:
    band_label: str
    rate: float
    amount_in_band: float
    tax_for_band: float


@dataclass
class TaxCalculation:
    assessment_year: int
    gross_income: float
    allowable_expenses: float
    adjusted_income: float
    reliefs_applied: float
    chargeable_income: float
    tax_before_rebate: float
    rebate_applied: float
    tax_owed: float
    effective_rate: float
    monthly_set_aside: float
    cp500_instalment_amount: float
    bracket_breakdown: list[BracketContribution] = field(default_factory=list)


def _format_band_label(lower: float, upper: float) -> str:
    if upper == float("inf"):
        return f"Above RM{lower:,.0f}"
    return f"RM{lower:,.0f} - RM{upper:,.0f}"


def calculate_progressive_tax(chargeable_income: float) -> tuple[float, list[BracketContribution]]:
    if chargeable_income < 0:
        raise ValueError("chargeable_income cannot be negative")

    total_tax = 0.0
    breakdown: list[BracketContribution] = []

    for lower, upper, rate in TAX_BRACKETS:
        if chargeable_income <= lower:
            break
        amount_in_band = min(chargeable_income, upper) - lower
        if amount_in_band <= 0:
            continue
        tax_for_band = amount_in_band * rate
        total_tax += tax_for_band
        if tax_for_band > 0 or rate > 0:
            breakdown.append(
                BracketContribution(
                    band_label=_format_band_label(lower, upper),
                    rate=rate,
                    amount_in_band=round(amount_in_band, 2),
                    tax_for_band=round(tax_for_band, 2),
                )
            )

    return round(total_tax, 2), breakdown


def calculate_tax(
    gross_income: float,
    allowable_expenses: float = 0.0,
    additional_reliefs: float = 0.0,
    assessment_year: int = SUPPORTED_ASSESSMENT_YEAR,
) -> TaxCalculation:
    """Computes tax owed for a self-employed individual's business income.

    `gross_income` and `allowable_expenses` are annual figures. Personal
    relief (RM9,000) is applied automatically for every resident individual,
    on top of any `additional_reliefs` the caller supplies (e.g. EPF/SOCSO
    relief, medical relief) - see lhdn_tax_relief_ya2025.pdf for the full list
    of what a user may be entitled to claim beyond the automatic relief.
    """
    if gross_income < 0:
        raise ValueError("gross_income cannot be negative")
    if allowable_expenses < 0:
        raise ValueError("allowable_expenses cannot be negative")
    if additional_reliefs < 0:
        raise ValueError("additional_reliefs cannot be negative")
    if assessment_year != SUPPORTED_ASSESSMENT_YEAR:
        raise ValueError(
            f"Only YA{SUPPORTED_ASSESSMENT_YEAR} rates are currently loaded; "
            f"YA{assessment_year} is not supported yet."
        )

    adjusted_income = max(0.0, gross_income - allowable_expenses)
    reliefs_applied = AUTOMATIC_PERSONAL_RELIEF + additional_reliefs
    chargeable_income = max(0.0, adjusted_income - reliefs_applied)

    tax_before_rebate, breakdown = calculate_progressive_tax(chargeable_income)

    rebate_applied = REBATE_AMOUNT if chargeable_income <= REBATE_CHARGEABLE_INCOME_THRESHOLD else 0.0
    rebate_applied = min(rebate_applied, tax_before_rebate)  # never rebate below zero
    tax_owed = round(tax_before_rebate - rebate_applied, 2)

    effective_rate = round(tax_owed / gross_income, 4) if gross_income > 0 else 0.0

    return TaxCalculation(
        assessment_year=assessment_year,
        gross_income=round(gross_income, 2),
        allowable_expenses=round(allowable_expenses, 2),
        adjusted_income=round(adjusted_income, 2),
        reliefs_applied=round(reliefs_applied, 2),
        chargeable_income=round(chargeable_income, 2),
        tax_before_rebate=tax_before_rebate,
        rebate_applied=round(rebate_applied, 2),
        tax_owed=tax_owed,
        effective_rate=effective_rate,
        monthly_set_aside=round(tax_owed / 12, 2),
        cp500_instalment_amount=round(tax_owed / CP500_INSTALMENTS_PER_YEAR, 2),
        bracket_breakdown=breakdown,
    )
