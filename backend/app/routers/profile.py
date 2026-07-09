"""The handful of facts (age, sector, EPF status, income estimate) a user can
set once so future financial-planning turns don't need to re-ask for them.

Not yet wired into the graph itself (the Financial Planner currently reads
figures from the conversation each turn) - this persists the profile so a
future turn/session can pre-fill those fields; see the TODO in
financial_planner.py for wiring this in as a fallback when the message itself
doesn't mention an age or sector.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.models import TaxProfile, User
from app.db.session import get_db
from app.schemas.profile import TaxProfileRead, TaxProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])


def _get_or_create_profile(db: Session, user_id: str) -> TaxProfile:
    profile = db.query(TaxProfile).filter(TaxProfile.user_id == user_id).first()
    if profile is None:
        profile = TaxProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.get("/tax-profile", response_model=TaxProfileRead)
def get_tax_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> TaxProfile:
    return _get_or_create_profile(db, current_user.id)


@router.put("/tax-profile", response_model=TaxProfileRead)
def update_tax_profile(
    payload: TaxProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaxProfile:
    profile = _get_or_create_profile(db, current_user.id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile
