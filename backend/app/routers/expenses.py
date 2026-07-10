"""Receipt upload (direct OCR + classification, bypassing the chat graph since
the intent is unambiguous here - a dedicated upload action, not a
conversational message) and expense listing/summary for the dashboard.
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.config import get_settings
from app.db.models import ExpenseRecord, User
from app.db.session import get_db
from app.ocr.expense_classifier import classify_expense
from app.ocr.receipt_ocr import OcrError, run_ocr
from app.schemas.expenses import CategoryTotal, ExpenseRecordRead, ExpenseSummary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/expenses", tags=["expenses"])

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/upload", response_model=ExpenseRecordRead, status_code=status.HTTP_201_CREATED)
async def upload_receipt(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExpenseRecord:
    settings = get_settings()

    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{file.content_type}'. Please upload a JPEG, PNG, or WebP image.",
        )

    contents = await file.read()
    if len(contents) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File is too large. Maximum size is {settings.max_upload_size_bytes // (1024 * 1024)}MB.",
        )
    if not contents:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Uploaded file is empty.")

    user_dir = Path(settings.upload_dir) / current_user.id
    user_dir.mkdir(parents=True, exist_ok=True)
    extension = Path(file.filename or "").suffix or ".jpg"
    image_path = user_dir / f"{uuid.uuid4()}{extension}"
    image_path.write_bytes(contents)

    try:
        # run_ocr (Tesseract subprocess + OpenCV preprocessing) and
        # classify_expense (a Groq call) are both blocking. Run them off the
        # event loop thread so a slow OCR/LLM call can't stall every other
        # request on this process - including Render's own health-check ping,
        # which otherwise gets starved long enough that the platform decides
        # the instance is dead and kills it mid-request.
        ocr_result = await run_in_threadpool(run_ocr, str(image_path))
    except OcrError as exc:
        logger.warning("OCR failed for uploaded receipt %s: %s", image_path, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Couldn't read that image - please try again with a clearer photo of the receipt.",
        ) from exc

    classification = await run_in_threadpool(classify_expense, ocr_result.raw_text)

    record = ExpenseRecord(
        user_id=current_user.id,
        image_path=str(image_path),
        raw_ocr_text=ocr_result.raw_text,
        vendor=classification.vendor,
        amount=classification.amount,
        category=classification.category,
        tax_deductible=classification.tax_deductible,
        ocr_confidence=ocr_result.confidence,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("", response_model=list[ExpenseRecordRead])
def list_expenses(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ExpenseRecord]:
    return (
        db.query(ExpenseRecord)
        .filter(ExpenseRecord.user_id == current_user.id)
        .order_by(ExpenseRecord.created_at.desc())
        .all()
    )


@router.get("/summary", response_model=ExpenseSummary)
def expense_summary(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ExpenseSummary:
    records = db.query(ExpenseRecord).filter(ExpenseRecord.user_id == current_user.id).all()

    totals: dict[tuple[str, bool], list] = {}
    total_expenses = 0.0
    total_deductible = 0.0

    for record in records:
        amount = float(record.amount) if record.amount is not None else 0.0
        total_expenses += amount
        if record.tax_deductible:
            total_deductible += amount

        key = (record.category, record.tax_deductible)
        if key not in totals:
            totals[key] = [0.0, 0]
        totals[key][0] += amount
        totals[key][1] += 1

    by_category = [
        CategoryTotal(category=category, total_amount=round(amount, 2), count=count, tax_deductible=deductible)
        for (category, deductible), (amount, count) in sorted(totals.items())
    ]

    return ExpenseSummary(
        total_expenses=round(total_expenses, 2),
        total_deductible=round(total_deductible, 2),
        by_category=by_category,
    )
