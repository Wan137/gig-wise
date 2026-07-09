"""Bridges LangGraph's in-memory turn state and the persisted database rows.

Kept separate from the routers so the routers stay focused on HTTP concerns
(request/response shaping, status codes) and the graph nodes stay unaware
that a database exists at all - only this module and the routers know both
worlds.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from sqlalchemy.orm import Session

from app.db.models import ChatSession, ExpenseRecord, Message
from app.graph.state import AgentTrace, ExpenseRecordState


def get_session_or_404(db: Session, session_id: str, user_id: str) -> ChatSession | None:
    return (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
        .first()
    )


def create_chat_session(db: Session, user_id: str, title: str = "New conversation") -> ChatSession:
    session = ChatSession(user_id=user_id, title=title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def load_recent_messages(db: Session, session_id: str, limit: int) -> list[BaseMessage]:
    """Loads the most recent `limit` messages, oldest-first, as LangChain messages."""
    rows = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )
    rows.reverse()

    messages: list[BaseMessage] = []
    for row in rows:
        if row.role == "user":
            messages.append(HumanMessage(content=row.content))
        elif row.role == "assistant":
            messages.append(AIMessage(content=row.content))
    return messages


def persist_turn(
    db: Session,
    session_id: str,
    user_message: str,
    assistant_message: str,
    trace: list[AgentTrace],
) -> None:
    db.add(Message(session_id=session_id, role="user", content=user_message))
    db.add(
        Message(
            session_id=session_id,
            role="assistant",
            content=assistant_message,
            trace_json=json.dumps(trace),
        )
    )
    db.commit()


def load_user_expense_records(db: Session, user_id: str) -> list[ExpenseRecordState]:
    """All of a user's previously logged expenses, for the Financial Planner to
    see spending from earlier turns/sessions - not just the current turn.
    """
    rows = db.query(ExpenseRecord).filter(ExpenseRecord.user_id == user_id).all()
    return [
        ExpenseRecordState(
            id=row.id,
            raw_ocr_text=row.raw_ocr_text or "",
            vendor=row.vendor,
            amount=float(row.amount) if row.amount is not None else None,
            date=row.expense_date.isoformat() if row.expense_date else None,
            category=row.category,
            tax_deductible=row.tax_deductible,
            ocr_confidence=float(row.ocr_confidence) if row.ocr_confidence is not None else 0.0,
        )
        for row in rows
    ]


def persist_new_expense_records(
    db: Session, user_id: str, records: list[ExpenseRecordState], image_path: str | None = None
) -> list[ExpenseRecord]:
    """Persists expense records that don't already exist in the DB (matched by id)."""
    if not records:
        return []

    existing_ids = {
        row.id for row in db.query(ExpenseRecord.id).filter(ExpenseRecord.id.in_([r["id"] for r in records]))
    }

    created: list[ExpenseRecord] = []
    for record in records:
        if record["id"] in existing_ids:
            continue
        expense_date = None
        if record.get("date"):
            try:
                expense_date = datetime.fromisoformat(record["date"]).replace(tzinfo=timezone.utc)
            except ValueError:
                expense_date = None

        row = ExpenseRecord(
            id=record["id"],
            user_id=user_id,
            image_path=image_path,
            raw_ocr_text=record.get("raw_ocr_text"),
            vendor=record.get("vendor"),
            amount=record.get("amount"),
            expense_date=expense_date,
            category=record.get("category", "other"),
            tax_deductible=bool(record.get("tax_deductible", False)),
            ocr_confidence=record.get("ocr_confidence"),
        )
        db.add(row)
        created.append(row)

    if created:
        db.commit()
    return created
