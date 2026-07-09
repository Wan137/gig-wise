"""Reads a receipt image referenced in state, extracts text, and classifies it."""
from __future__ import annotations

import logging
import uuid

from app.graph.state import CopilotState, ExpenseRecordState
from app.graph.utils import append_draft, make_trace
from app.ocr.expense_classifier import classify_expense
from app.ocr.receipt_ocr import OcrError, run_ocr

logger = logging.getLogger(__name__)

_NO_RECEIPT_MESSAGE = (
    "I don't see a receipt attached to log. Please upload a photo of the receipt and I'll read and "
    "categorize it for you."
)
_OCR_FAILED_MESSAGE = (
    "I couldn't read that receipt image - it may be corrupted or in an unsupported format. Please try "
    "uploading it again, ideally in good lighting with the receipt flat and in frame."
)


def _format_summary(record: ExpenseRecordState, reasoning: str) -> str:
    vendor = record.get("vendor") or "this expense"
    amount = record.get("amount")
    amount_str = f"RM{amount:.2f}" if amount is not None else "an amount I couldn't quite read"
    category_label = record["category"].replace("_", " ")
    deductible = "likely tax-deductible" if record.get("tax_deductible") else "likely NOT tax-deductible"
    return f"Logged {amount_str} at {vendor} as **{category_label}** ({deductible}). {reasoning}".strip()


def expense_tracker_node(state: CopilotState) -> dict:
    receipt_path = state.get("pending_receipt")
    if not receipt_path:
        return {
            "draft_answer": append_draft(state, _NO_RECEIPT_MESSAGE),
            "trace": make_trace("expense_tracker", "Looking for a receipt to read..."),
        }

    try:
        ocr_result = run_ocr(receipt_path)
    except OcrError:
        logger.exception("OCR failed for receipt at %s", receipt_path)
        return {
            "draft_answer": append_draft(state, _OCR_FAILED_MESSAGE),
            "trace": make_trace("expense_tracker", "Reading your receipt..."),
        }

    classification = classify_expense(ocr_result.raw_text)

    record = ExpenseRecordState(
        id=str(uuid.uuid4()),
        raw_ocr_text=ocr_result.raw_text,
        vendor=classification.vendor,
        amount=classification.amount,
        date=classification.expense_date,
        category=classification.category,
        tax_deductible=classification.tax_deductible,
        ocr_confidence=ocr_result.confidence,
    )

    summary = _format_summary(record, classification.reasoning)

    return {
        "expense_records": (state.get("expense_records") or []) + [record],
        "draft_answer": append_draft(state, summary),
        "trace": make_trace("expense_tracker", "Reading your receipt..."),
    }
