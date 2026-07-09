# RAG Knowledge Base — Document Sourcing Log

Every document in this folder is public information published by LHDN (Inland
Revenue Board of Malaysia), KWSP (EPF), or PERKESO (SOCSO). All were retrieved
on **2026-07-09**. Government agencies revise rates, reliefs, and scheme terms
via annual Budget announcements — if a figure in the Tax Advisor's answer looks
out of date, re-check it against the live page/PDF linked below before trusting
it, and re-run the ingestion pipeline with an updated document.

| File | Source | Type | Origin URL |
|---|---|---|---|
| `lhdn_individual_business_income_guide.pdf` | LHDN | Official leaflet | https://phl.hasil.gov.my/pdf/pdfam/003a.pdf |
| `lhdn_allowable_disallowed_expenses.pdf` | LHDN | Official slide deck (19 pp, updated 06/06/2021) | https://phl.hasil.gov.my/pdf/pdfam/Allowable_And_Disallowed_Expenses_Slide.pdf |
| `lhdn_form_b_explanatory_notes_2024.pdf` | LHDN | Official Form B (business income) explanatory notes, YA2024 | https://www.hasil.gov.my/media/eaglbe10/explanatory_notes_b2024_2.pdf |
| `lhdn_taxation_individual_business_income_article.pdf` | LHDN (co-published, The Star, 19 Jun 2023) | Plain-language explainer article | https://www.hasil.gov.my/media/i3pfxazp/taxation-on-individual-business-income_the-star_19062023.pdf |
| `lhdn_tax_relief_ya2025.pdf` | LHDN | Official tax relief table, YA2025 | https://www.hasil.gov.my/media/muob0jyz/tax-relief-ya-2025.pdf |
| `lhdn_tax_rate_schedule.txt` | LHDN | Curated extract of the official tax rate page (YA2023-YA2025 progressive schedule + rebate) | https://www.hasil.gov.my/en/individual/individual-life-cycle/income-declaration/tax-rate/ |
| `kwsp_i_saraan.txt` | KWSP/EPF | Curated extract of the official i-Saraan page | https://www.kwsp.gov.my/en/member/savings/i-saraan |
| `kwsp_i_saraan_plus.txt` | KWSP/EPF | Curated extract of the official i-Saraan Plus page (new 2026 scheme for e-hailing/p-hailing drivers) | https://www.kwsp.gov.my/en/member/savings/i-saraan-plus |
| `perkeso_sksps_self_employed.txt` | PERKESO/SOCSO | Curated extract of the official Self-Employment Social Security Scheme pages | https://www.perkeso.gov.my/en/our-services/protection/self-employed.html, https://www.perkeso.gov.my/en/rate-of-contribution.html |
| `socso_sksps_flyer_2022.pdf` | PERKESO/SOCSO | Official SKSPS flyer PDF (2022) | https://www.perkeso.gov.my/images/sps/risalah/FLYERS_SKSPS_2022_EN_compressed.pdf |

## Why some documents are `.txt` extracts rather than the original PDF/HTML

`lhdn_tax_rate_schedule.txt`, `kwsp_i_saraan.txt`, `kwsp_i_saraan_plus.txt`, and
`perkeso_sksps_self_employed.txt` come from live HTML pages, not downloadable
PDFs. Each was fetched directly, stripped of site navigation/menu boilerplate,
and saved with zero paraphrasing of the substantive content — only removing
repeated nav text — so every number and eligibility rule is a direct quote of
the source page, not a summary. The origin URL and retrieval date are recorded
at the top of each file, and if a fact needs re-verification, follow the URL
back to the live page.

## Known gaps / things to revisit

- **No Form B explanatory notes for YA2025 were publicly indexed yet as of the
  retrieval date** — LHDN had published the YA2025 notes for Form BE
  (employment income, no business) but not yet for Form B (business income)
  at the time of writing. The YA2024 Form B notes are used instead; the
  underlying tax rate schedule and reliefs are separately confirmed current
  for YA2025 via `lhdn_tax_rate_schedule.txt` and `lhdn_tax_relief_ya2025.pdf`.
  Re-check `hasil.gov.my` forms download page periodically and swap in the
  YA2025 Form B notes once published.
- **No LHDN public ruling specifically named for "gig economy" or platform
  workers exists.** LHDN's own published guidance (see
  `lhdn_taxation_individual_business_income_article.pdf`) treats gig/digital
  economy income as ordinary business income under the Income Tax Act 1967,
  taxed and assessed the same way as any other sole-proprietor business income
  under Form B. The Tax Advisor agent should reflect this — there is no
  special "gig worker tax code," just the general self-employed rules applied
  to gig income.
- **PERKESO's "SPS Padanan Caruman" matching-grant programme** (see the note
  at the end of `perkeso_sksps_self_employed.txt`) is a targeted, budget-funded
  subsidy for specific vulnerable groups, not a standing entitlement for every
  SKSPS contributor. The Financial Planner should not assume it applies by
  default when estimating a user's SOCSO cost.
