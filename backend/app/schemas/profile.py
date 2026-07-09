from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TaxProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date_of_birth: datetime | None
    occupation_sector: str | None
    is_epf_member: bool
    estimated_annual_income: float | None


class TaxProfileUpdate(BaseModel):
    date_of_birth: datetime | None = None
    occupation_sector: str | None = None
    is_epf_member: bool | None = None
    estimated_annual_income: float | None = None
