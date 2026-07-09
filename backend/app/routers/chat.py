"""Chat session management and the SSE-streamed message endpoint.

The SSE stream is what makes the frontend's "live reasoning" panel possible:
each LangGraph node's trace entry is forwarded as soon as it's produced
(`stream_mode="values"` yields the full state snapshot after every node, so
we diff the trace list between snapshots to find what's new), rather than
making the user wait for the whole turn to finish before seeing anything.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.auth.dependencies import get_current_user
from app.config import get_settings
from app.db.models import ChatSession, User
from app.db.repository import (
    create_chat_session,
    get_session_or_404,
    load_recent_messages,
    load_user_expense_records,
    persist_new_expense_records,
    persist_turn,
)
from app.db.session import get_db
from app.graph.graph import get_compiled_graph
from app.graph.state import initial_state
from app.schemas.chat import ChatMessageCreate, ChatSessionRead, MessageRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

_GENERIC_ERROR_MESSAGE = "Something went wrong producing a response. Please try again in a moment."


@router.post("/sessions", response_model=ChatSessionRead, status_code=status.HTTP_201_CREATED)
def create_session(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ChatSession:
    return create_chat_session(db, current_user.id)


@router.get("/sessions", response_model=list[ChatSessionRead])
def list_sessions(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ChatSession]:
    return (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )


@router.get("/sessions/{session_id}/messages", response_model=list[MessageRead])
def get_messages(
    session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list:
    session = get_session_or_404(db, session_id, current_user.id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")
    return session.messages


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    payload: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EventSourceResponse:
    session = get_session_or_404(db, session_id, current_user.id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")

    if not payload.content or not payload.content.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Message content cannot be empty.")

    settings = get_settings()
    history = load_recent_messages(db, session_id, settings.chat_history_limit)
    preloaded_expenses = load_user_expense_records(db, current_user.id)
    preloaded_count = len(preloaded_expenses)
    is_first_message = len(history) == 0

    turn_state = initial_state(
        user_id=current_user.id,
        session_id=session_id,
        user_message=payload.content,
        history=history,
        expense_records=preloaded_expenses,
    )

    graph = get_compiled_graph()

    async def event_generator():
        seen_trace_count = 0
        final_state = None

        try:
            async for snapshot in graph.astream(turn_state, stream_mode="values"):
                final_state = snapshot
                trace = snapshot.get("trace") or []
                for entry in trace[seen_trace_count:]:
                    yield {
                        "event": "trace",
                        "data": json.dumps({"node": entry["node"], "message": entry["message"]}),
                    }
                seen_trace_count = len(trace)
        except Exception:
            logger.exception("Graph execution failed for session %s", session_id)
            yield {"event": "error", "data": json.dumps({"message": _GENERIC_ERROR_MESSAGE})}
            return

        final_answer = (final_state or {}).get("final_answer")
        if not final_answer:
            logger.error("Graph completed without a final_answer for session %s", session_id)
            yield {"event": "error", "data": json.dumps({"message": _GENERIC_ERROR_MESSAGE})}
            return

        try:
            persist_turn(db, session_id, payload.content, final_answer, final_state.get("trace") or [])
            new_records = (final_state.get("expense_records") or [])[preloaded_count:]
            persist_new_expense_records(db, current_user.id, new_records)
            if is_first_message:
                session.title = payload.content[:80]
                db.commit()
        except Exception:
            # The user's answer was already computed correctly - a persistence
            # failure here shouldn't become an error response for them, just a
            # logged issue for us (their next message will simply lack this
            # turn's history, which is a minor degradation, not data loss for
            # the user's current request).
            logger.exception("Failed to persist turn for session %s", session_id)

        yield {"event": "final", "data": json.dumps({"answer": final_answer})}

    return EventSourceResponse(event_generator())
