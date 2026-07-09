"""Extracts structured fields from raw OCR text and classifies the expense.

The category rules embedded in the prompt below are taken directly from
backend/app/rag/documents/lhdn_allowable_disallowed_expenses.pdf (fuel/mileage,
repair & maintenance, and electricity/water/telephone/internet charges are
listed there as common allowable business expenses; domestic/private/capital
expenditure is listed as disallowed). This is a single deterministic
classification call rather than a RAG lookup - the Tax Advisor agent is the
one that does source-grounded retrieval for open-ended tax questions: this
classifier's job is narrow enough (sort a receipt into one of a fixed list of
categories) that embedding the relevant rule directly in the prompt is simpler
and faster than a retrieval round-trip, without sacrificing accuracy.
"""
from __future__ import annotations

import logging
import re
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.graph.llm import get_llm

logger = logging.getLogger(__name__)

ExpenseCategory = Literal[
    "fuel",
    "vehicle_maintenance",
    "phone_internet",
    "tolls_parking",
    "vehicle_insurance",
    "equipment_supplies",
    "personal_non_deductible",
    "other",
]

_CLASSIFIER_SYSTEM_PROMPT = """You extract structured data from OCR'd receipt/invoice text for a \
Malaysian gig economy worker (e-hailing driver, delivery rider, or freelancer) tracking business \
expenses.

The OCR text may contain recognition errors (garbled characters, misread digits) - use context to \
recover the most likely vendor name and amount despite noise.

Categories (pick exactly one):
- "fuel": petrol/diesel/EV charging for the work vehicle.
- "vehicle_maintenance": servicing, repairs, tyres, spare parts for the work vehicle.
- "phone_internet": phone bill, mobile data, or internet subscription used for work (e.g. running the \
  driver/delivery app).
- "tolls_parking": toll payments, parking fees incurred while working.
- "vehicle_insurance": motor insurance/road tax for the work vehicle.
- "equipment_supplies": delivery bags, phone mounts, dashcams, safety gear, and similar work equipment.
- "personal_non_deductible": clearly personal spending with no business connection (groceries, \
  personal clothing, entertainment, etc).
- "other": a plausible business expense that doesn't fit the categories above.

Tax deductibility guidance (from LHDN's published allowable/disallowed business expense rules):
- Fuel/mileage claims, repair and maintenance, and electricity/water/telephone/internet charges are \
  commonly ALLOWABLE business expenses when incurred wholly and exclusively in the production of \
  income (Income Tax Act 1967, Section 33).
- Domestic, private, or capital expenditure is NOT allowable (Section 39). A personal grocery run, a \
  purely personal phone data plan, or a car purchase itself (as opposed to fuel/repairs) does not \
  qualify.
- A phone/internet bill used for both work and personal purposes is only deductible for its business-use \
  portion - note this in `reasoning` rather than assuming the full amount is deductible.

Extract:
- vendor: the merchant/company name, or null if illegible.
- amount: the total amount paid, as a plain number (no currency symbol), or null if illegible.
- expense_date: the transaction date in YYYY-MM-DD format if determinable, else null.
- category: one of the categories above.
- tax_deductible: your best-effort judgement of whether this expense is likely deductible for a gig \
  worker's business income, based on the guidance above.
- reasoning: one short sentence explaining the category/deductibility call, flagging apportionment if \
  relevant.
"""

_AMOUNT_PATTERN = re.compile(r"RM\s*([\d,]+\.\d{2})", re.IGNORECASE)


class ExpenseClassification(BaseModel):
    vendor: str | None = None
    amount: float | None = None
    expense_date: str | None = None
    category: ExpenseCategory
    tax_deductible: bool
    reasoning: str = Field(description="One short sentence explaining the category/deductibility call.")


def _regex_fallback(raw_text: str) -> ExpenseClassification:
    """Used only if the LLM call itself fails - keeps the pipeline from crashing."""
    amounts = [float(m.replace(",", "")) for m in _AMOUNT_PATTERN.findall(raw_text)]
    amount = amounts[-1] if amounts else None  # the total is conventionally the last RM figure printed
    return ExpenseClassification(
        vendor=None,
        amount=amount,
        expense_date=None,
        category="other",
        tax_deductible=False,
        reasoning="Automatic classification was unavailable; please review and re-categorize manually.",
    )


def classify_expense(raw_text: str) -> ExpenseClassification:
    if not raw_text or not raw_text.strip():
        return ExpenseClassification(
            category="other",
            tax_deductible=False,
            reasoning="No text could be read from the receipt image.",
        )

    try:
        llm = get_llm(temperature=0.0).with_structured_output(ExpenseClassification)
        result = llm.invoke(
            [SystemMessage(content=_CLASSIFIER_SYSTEM_PROMPT), HumanMessage(content=raw_text)]
        )
        return result
    except Exception:
        logger.exception("Expense classification LLM call failed; falling back to regex extraction")
        return _regex_fallback(raw_text)
