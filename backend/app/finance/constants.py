"""Sourced tax/EPF/SOCSO figures - every constant here traces to a specific
document in backend/app/rag/documents/ (see SOURCES.md there for origin URLs
and retrieval dates). Nothing in this file is estimated or LLM-derived.
"""
from __future__ import annotations

# --- LHDN resident individual progressive tax rate schedule ---
# Source: backend/app/rag/documents/lhdn_tax_rate_schedule.txt
# Stated by LHDN to apply to YA2023, YA2024, and YA2025.
SUPPORTED_ASSESSMENT_YEAR = 2025

# (lower_bound_exclusive, upper_bound_inclusive, marginal_rate)
TAX_BRACKETS: list[tuple[float, float, float]] = [
    (0, 5_000, 0.00),
    (5_000, 20_000, 0.01),
    (20_000, 35_000, 0.03),
    (35_000, 50_000, 0.06),
    (50_000, 70_000, 0.11),
    (70_000, 100_000, 0.19),
    (100_000, 400_000, 0.25),
    (400_000, 600_000, 0.26),
    (600_000, 2_000_000, 0.28),
    (2_000_000, float("inf"), 0.30),
]

# Automatic relief every resident individual receives regardless of marital
# status or income (source: lhdn_tax_relief_ya2025.pdf, "Individual & Dependent
# Relatives").
AUTOMATIC_PERSONAL_RELIEF = 9_000.0

# A resident individual whose chargeable income does not exceed this receives
# a rebate applied directly against computed tax, not against income.
REBATE_CHARGEABLE_INCOME_THRESHOLD = 35_000.0
REBATE_AMOUNT = 400.0

# --- LHDN self-employed advance tax instalment scheme (CP500) ---
# Source: research summarized in docs/ARCHITECTURE.md / project notes - LHDN
# splits a self-employed individual's estimated annual tax into 6 bi-monthly
# instalments (not quarterly - Malaysia's CP500 mechanism is bi-monthly).
CP500_INSTALMENTS_PER_YEAR = 6

# --- KWSP EPF i-Saraan / i-Saraan Plus ---
# Source: backend/app/rag/documents/kwsp_i_saraan.txt, kwsp_i_saraan_plus.txt
EPF_ISARAAN_INCENTIVE_RATE = 0.20
EPF_ISARAAN_MAX_ANNUAL_INCENTIVE = 500.0
EPF_ISARAAN_LIFETIME_INCENTIVE_CAP = 5_000.0

EPF_ISARAAN_PLUS_MAX_ANNUAL_INCENTIVE = 600.0
EPF_ISARAAN_PLUS_LIFETIME_INCENTIVE_CAP = 6_000.0

# --- PERKESO SOCSO Self-Employment Social Security Scheme (SKSPS, Act 789) ---
# Source: backend/app/rag/documents/perkeso_sksps_self_employed.txt
# There are exactly four fixed insured-earning tiers - a contributor selects
# the tier closest to (not exceeding, ideally) their actual monthly earning;
# the contribution is a fixed amount per tier, not a percentage of income.
SKSPS_TIERS: list[dict[str, float]] = [
    {"insured_monthly_earning": 1_050.0, "monthly_contribution": 13.10, "annual_contribution": 157.20},
    {"insured_monthly_earning": 1_550.0, "monthly_contribution": 19.40, "annual_contribution": 232.80},
    {"insured_monthly_earning": 2_950.0, "monthly_contribution": 36.90, "annual_contribution": 442.80},
    {"insured_monthly_earning": 3_950.0, "monthly_contribution": 49.40, "annual_contribution": 592.80},
]
