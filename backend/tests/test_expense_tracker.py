"""Tests for the Expense Tracker agent: OCR, classification, and the graph node.

OCR tests run unconditionally (no external API needed - Tesseract is a local
binary). Classification/node tests call the real Groq API (no mocking) and
are skipped if no GROQ_API_KEY is configured, matching test_graph.py.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.config import get_settings
from app.graph.nodes.expense_tracker import expense_tracker_node
from app.graph.state import initial_state
from app.ocr.expense_classifier import classify_expense
from app.ocr.receipt_ocr import OcrError, run_ocr

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "receipts"

requires_groq = pytest.mark.skipif(
    not get_settings().groq_api_key, reason="GROQ_API_KEY not configured - skipping live LLM tests"
)


# --- OCR (no LLM involved) ---------------------------------------------------


@pytest.mark.parametrize(
    "filename,expected_substrings",
    [
        ("petronas_fuel.png", ["PETRONAS", "84.50"]),
        ("maxis_phone_bill.png", ["MAXIS", "98.00"]),
        ("auto_service_invoice.png", ["AUTO CARE", "250.00"]),
        ("personal_groceries.png", ["AEON", "58.80"]),
    ],
)
def test_run_ocr_extracts_expected_text(filename, expected_substrings):
    result = run_ocr(str(FIXTURES_DIR / filename))
    for substring in expected_substrings:
        assert substring in result.raw_text
    assert result.confidence > 0.8


def test_run_ocr_handles_degraded_image_without_crashing():
    result = run_ocr(str(FIXTURES_DIR / "degraded_fuel_receipt.png"))
    assert "PETRONAS" in result.raw_text
    assert result.confidence > 0.0


def test_run_ocr_raises_clear_error_for_missing_file():
    with pytest.raises(OcrError):
        run_ocr(str(FIXTURES_DIR / "does_not_exist.png"))


# --- Classification (real Groq calls) ----------------------------------------


@requires_groq
def test_classify_fuel_receipt_as_deductible():
    ocr_result = run_ocr(str(FIXTURES_DIR / "petronas_fuel.png"))
    classification = classify_expense(ocr_result.raw_text)
    assert classification.category == "fuel"
    assert classification.tax_deductible is True
    assert classification.amount == pytest.approx(84.50, abs=0.01)


@requires_groq
def test_classify_personal_groceries_as_non_deductible():
    ocr_result = run_ocr(str(FIXTURES_DIR / "personal_groceries.png"))
    classification = classify_expense(ocr_result.raw_text)
    assert classification.category == "personal_non_deductible"
    assert classification.tax_deductible is False


@requires_groq
def test_classify_vehicle_maintenance_invoice():
    ocr_result = run_ocr(str(FIXTURES_DIR / "auto_service_invoice.png"))
    classification = classify_expense(ocr_result.raw_text)
    assert classification.category == "vehicle_maintenance"
    assert classification.tax_deductible is True


def test_classify_expense_handles_empty_text_without_crashing():
    classification = classify_expense("")
    assert classification.category == "other"
    assert classification.tax_deductible is False


# --- Graph node ---------------------------------------------------------------


def test_expense_tracker_node_without_receipt_asks_for_one():
    state = initial_state(user_id="u1", session_id="s1", user_message="log my expense")
    result = expense_tracker_node(state)
    assert "upload a photo" in result["draft_answer"].lower()
    assert result["trace"][0]["node"] == "expense_tracker"


@requires_groq
def test_expense_tracker_node_full_pipeline():
    state = initial_state(user_id="u1", session_id="s1", user_message="log this fuel receipt")
    state["pending_receipt"] = str(FIXTURES_DIR / "petronas_fuel.png")

    result = expense_tracker_node(state)

    assert len(result["expense_records"]) == 1
    record = result["expense_records"][0]
    assert record["category"] == "fuel"
    assert record["tax_deductible"] is True
    assert record["amount"] == pytest.approx(84.50, abs=0.01)
    assert "PETRONAS" in result["draft_answer"]
