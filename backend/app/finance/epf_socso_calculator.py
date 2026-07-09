"""Deterministic EPF (i-Saraan/i-Saraan Plus) and SOCSO (SKSPS) suggestions.

Like tax_calculator.py, this is plain arithmetic against sourced constants -
no LLM involved in producing a number.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.finance.constants import (
    EPF_ISARAAN_INCENTIVE_RATE,
    EPF_ISARAAN_LIFETIME_INCENTIVE_CAP,
    EPF_ISARAAN_MAX_ANNUAL_INCENTIVE,
    EPF_ISARAAN_PLUS_LIFETIME_INCENTIVE_CAP,
    EPF_ISARAAN_PLUS_MAX_ANNUAL_INCENTIVE,
    SKSPS_TIERS,
)


@dataclass
class EpfSuggestion:
    scheme: str  # "i-Saraan" or "i-Saraan Plus"
    eligible: bool
    suggested_annual_contribution: float
    suggested_monthly_contribution: float
    expected_annual_incentive: float
    lifetime_incentive_cap: float
    note: str = ""


@dataclass
class SocsoSuggestion:
    scheme: str  # "SKSPS"
    matched_insured_monthly_earning: float
    monthly_contribution: float
    annual_contribution: float
    note: str


def suggest_epf_contribution(is_ehailing_or_phailing_driver: bool = False, age: int | None = None) -> EpfSuggestion:
    """Suggests the annual voluntary contribution that maximizes the government
    matching incentive (20% of contributions, up to a scheme-specific cap).

    Both schemes are only open to members below 60 (source: kwsp_i_saraan.txt,
    kwsp_i_saraan_plus.txt "Below 60 years of age" eligibility rule) - if the
    caller supplies an age of 60+, this returns eligible=False rather than a
    contribution figure the user can't actually act on.
    """
    if is_ehailing_or_phailing_driver:
        scheme = "i-Saraan Plus"
        max_incentive = EPF_ISARAAN_PLUS_MAX_ANNUAL_INCENTIVE
        lifetime_cap = EPF_ISARAAN_PLUS_LIFETIME_INCENTIVE_CAP
    else:
        scheme = "i-Saraan"
        max_incentive = EPF_ISARAAN_MAX_ANNUAL_INCENTIVE
        lifetime_cap = EPF_ISARAAN_LIFETIME_INCENTIVE_CAP

    if age is not None and age >= 60:
        return EpfSuggestion(
            scheme=scheme,
            eligible=False,
            suggested_annual_contribution=0.0,
            suggested_monthly_contribution=0.0,
            expected_annual_incentive=0.0,
            lifetime_incentive_cap=lifetime_cap,
            note=f"{scheme} is only open to members below 60 years of age, so this isn't available.",
        )

    contribution_for_max_incentive = max_incentive / EPF_ISARAAN_INCENTIVE_RATE

    return EpfSuggestion(
        scheme=scheme,
        eligible=True,
        suggested_annual_contribution=round(contribution_for_max_incentive, 2),
        suggested_monthly_contribution=round(contribution_for_max_incentive / 12, 2),
        expected_annual_incentive=max_incentive,
        lifetime_incentive_cap=lifetime_cap,
        note="Suggested amount maximizes the government matching incentive.",
    )


def suggest_socso_contribution(estimated_monthly_earning: float) -> SocsoSuggestion:
    """Matches the user's estimated monthly earning to the closest SKSPS tier.

    SKSPS has exactly four fixed tiers (not a continuous percentage), so this
    picks the highest tier at or below the user's earning; if their earning
    exceeds every tier, the top tier is used since there is no higher one.
    """
    if estimated_monthly_earning < 0:
        raise ValueError("estimated_monthly_earning cannot be negative")

    sorted_tiers = sorted(SKSPS_TIERS, key=lambda t: t["insured_monthly_earning"])
    chosen = sorted_tiers[0]
    for tier in sorted_tiers:
        if estimated_monthly_earning >= tier["insured_monthly_earning"]:
            chosen = tier
        else:
            break

    note = (
        "Matched to the closest available SKSPS tier at or below your estimated earning."
        if estimated_monthly_earning >= sorted_tiers[0]["insured_monthly_earning"]
        else "Your estimated earning is below the lowest SKSPS tier; the lowest tier is shown."
    )

    return SocsoSuggestion(
        scheme="SKSPS",
        matched_insured_monthly_earning=chosen["insured_monthly_earning"],
        monthly_contribution=chosen["monthly_contribution"],
        annual_contribution=chosen["annual_contribution"],
        note=note,
    )
