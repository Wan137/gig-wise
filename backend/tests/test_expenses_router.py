"""Tests for the receipt upload, listing, and summary endpoints.

Upload calls the real OCR pipeline and the real Groq classifier (no
mocking) - the classification portion is skipped without a configured Groq
key, but OCR itself needs no API and always runs.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.config import get_settings

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "receipts"

requires_groq = pytest.mark.skipif(
    not get_settings().groq_api_key, reason="GROQ_API_KEY not configured - skipping live LLM tests"
)


def test_upload_requires_authentication(client):
    with open(FIXTURES_DIR / "petronas_fuel.png", "rb") as f:
        response = client.post("/expenses/upload", files={"file": ("receipt.png", f, "image/png")})
    assert response.status_code == 401


def test_upload_rejects_unsupported_file_type(client, auth_headers):
    response = client.post(
        "/expenses/upload",
        headers=auth_headers,
        files={"file": ("notes.txt", b"just some text", "text/plain")},
    )
    assert response.status_code == 415


def test_upload_rejects_empty_file(client, auth_headers):
    response = client.post(
        "/expenses/upload",
        headers=auth_headers,
        files={"file": ("empty.png", b"", "image/png")},
    )
    assert response.status_code == 422


@requires_groq
def test_upload_ocr_and_classify_then_list_and_summarize(client, auth_headers):
    with open(FIXTURES_DIR / "petronas_fuel.png", "rb") as f:
        upload_resp = client.post(
            "/expenses/upload", headers=auth_headers, files={"file": ("receipt.png", f, "image/png")}
        )

    assert upload_resp.status_code == 201
    body = upload_resp.json()
    assert body["category"] == "fuel"
    assert body["tax_deductible"] is True
    assert body["amount"] == pytest.approx(84.50, abs=0.01)

    list_resp = client.get("/expenses", headers=auth_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    summary_resp = client.get("/expenses/summary", headers=auth_headers)
    summary = summary_resp.json()
    assert summary["total_expenses"] == pytest.approx(84.50, abs=0.01)
    assert summary["total_deductible"] == pytest.approx(84.50, abs=0.01)
    assert summary["by_category"][0]["category"] == "fuel"


def test_summary_is_zero_for_a_user_with_no_expenses(client, auth_headers):
    response = client.get("/expenses/summary", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"total_expenses": 0.0, "total_deductible": 0.0, "by_category": []}
