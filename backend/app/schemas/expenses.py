from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ExpenseRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    vendor: str | None
    amount: float | None
    expense_date: datetime | None
    category: str
    tax_deductible: bool
    ocr_confidence: float | None
    created_at: datetime


class CategoryTotal(BaseModel):
    category: str
    total_amount: float
    count: int
    tax_deductible: bool


class ExpenseSummary(BaseModel):
    total_expenses: float
    total_deductible: float
    by_category: list[CategoryTotal]
