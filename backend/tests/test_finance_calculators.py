"""Unit tests for the deterministic tax/EPF/SOCSO calculators.

No LLM involved anywhere in this file - these are pure-Python arithmetic
checks against hand-verified expected values, which is exactly the point:
financial accuracy is guaranteed by code, not by trusting a model's output.
"""
from __future__ import annotations

import pytest

from app.finance.epf_socso_calculator import suggest_epf_contribution, suggest_socso_contribution
from app.finance.tax_calculator import calculate_tax


# --- Tax calculator ------------------------------------------------------------


def test_low_income_gig_worker_gets_rebate_and_low_tax():
    # RM4,000/month gross, RM500/month allowable expenses -> RM48,000/RM6,000 annually.
    result = calculate_tax(gross_income=48_000, allowable_expenses=6_000)

    assert result.adjusted_income == 42_000
    assert result.chargeable_income == 33_000.0  # 42,000 - 9,000 automatic relief
    assert result.tax_before_rebate == 540.0
    assert result.rebate_applied == 400.0  # chargeable income <= RM35,000
    assert result.tax_owed == 140.0
    assert result.monthly_set_aside == pytest.approx(11.67, abs=0.01)
    assert result.cp500_instalment_amount == pytest.approx(23.33, abs=0.01)


def test_mid_income_earner_no_rebate_multiple_brackets():
    result = calculate_tax(gross_income=120_000, allowable_expenses=20_000)

    assert result.chargeable_income == 91_000.0
    assert result.rebate_applied == 0.0  # chargeable income above RM35,000 threshold
    assert result.tax_owed == 7_690.0
    assert result.effective_rate == pytest.approx(0.0641, abs=0.0001)


def test_zero_income_produces_zero_tax_not_an_error():
    result = calculate_tax(gross_income=0, allowable_expenses=0)
    assert result.tax_owed == 0.0
    assert result.chargeable_income == 0.0
    assert result.bracket_breakdown == []


def test_top_bracket_is_applied_for_very_high_income():
    result = calculate_tax(gross_income=2_500_000, allowable_expenses=0)
    assert result.chargeable_income == 2_491_000.0
    assert result.tax_owed == 675_700.0
    top_band = result.bracket_breakdown[-1]
    assert top_band.band_label == "Above RM2,000,000"
    assert top_band.rate == 0.30


def test_expenses_exceeding_income_floor_at_zero_not_negative():
    result = calculate_tax(gross_income=10_000, allowable_expenses=50_000)
    assert result.adjusted_income == 0.0
    assert result.chargeable_income == 0.0
    assert result.tax_owed == 0.0


@pytest.mark.parametrize("bad_kwargs", [{"gross_income": -1}, {"gross_income": 1, "allowable_expenses": -1}])
def test_negative_inputs_are_rejected(bad_kwargs):
    with pytest.raises(ValueError):
        calculate_tax(**bad_kwargs)


def test_unsupported_assessment_year_is_rejected():
    with pytest.raises(ValueError):
        calculate_tax(gross_income=50_000, assessment_year=2019)


# --- EPF i-Saraan / i-Saraan Plus -----------------------------------------------


def test_isaraan_suggests_contribution_that_maxes_the_incentive():
    result = suggest_epf_contribution(is_ehailing_or_phailing_driver=False)
    assert result.scheme == "i-Saraan"
    assert result.suggested_annual_contribution == 2_500.0  # 20% of 2,500 = 500 (the cap)
    assert result.expected_annual_incentive == 500.0
    assert result.lifetime_incentive_cap == 5_000.0


def test_isaraan_plus_suggests_higher_contribution_for_higher_cap():
    result = suggest_epf_contribution(is_ehailing_or_phailing_driver=True)
    assert result.scheme == "i-Saraan Plus"
    assert result.suggested_annual_contribution == 3_000.0  # 20% of 3,000 = 600 (the cap)
    assert result.expected_annual_incentive == 600.0
    assert result.lifetime_incentive_cap == 6_000.0


def test_isaraan_ineligible_for_members_60_and_over():
    result = suggest_epf_contribution(is_ehailing_or_phailing_driver=False, age=61)
    assert result.eligible is False
    assert result.suggested_annual_contribution == 0.0
    assert "60" in result.note


def test_isaraan_eligible_just_under_60():
    result = suggest_epf_contribution(is_ehailing_or_phailing_driver=False, age=59)
    assert result.eligible is True
    assert result.suggested_annual_contribution == 2_500.0


# --- SOCSO SKSPS -----------------------------------------------------------------


def test_socso_matches_earning_between_tiers_to_lower_tier():
    result = suggest_socso_contribution(estimated_monthly_earning=2_000)
    assert result.matched_insured_monthly_earning == 1_550.0
    assert result.monthly_contribution == 19.40


def test_socso_below_lowest_tier_uses_lowest_tier():
    result = suggest_socso_contribution(estimated_monthly_earning=500)
    assert result.matched_insured_monthly_earning == 1_050.0
    assert "below the lowest" in result.note.lower()


def test_socso_above_highest_tier_uses_highest_tier():
    result = suggest_socso_contribution(estimated_monthly_earning=10_000)
    assert result.matched_insured_monthly_earning == 3_950.0
    assert result.monthly_contribution == 49.40


def test_socso_rejects_negative_earning():
    with pytest.raises(ValueError):
        suggest_socso_contribution(-100)
