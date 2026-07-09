"""Graceful fallback for a subtask type the dispatcher doesn't recognize.

All three specialist agents (tax_question, expense_entry, financial_planning)
are implemented as of Task 6, so nothing in SubtaskType routes here today -
this stays in the graph as a safety net for the routing logic itself: if
`_IMPLEMENTED_AGENTS` in dispatcher.py and the orchestrator's SubtaskType enum
ever drift out of sync, a turn still degrades to a clear message instead of
LangGraph raising on an unmapped conditional-edge result.
"""
from __future__ import annotations

from app.graph.state import CopilotState
from app.graph.utils import append_draft, make_trace


def not_implemented_node(state: CopilotState) -> dict:
    agent = state.get("active_agent") or "that feature"
    message = f"{agent} isn't available yet - check back soon!"
    return {
        "draft_answer": append_draft(state, message),
        "trace": make_trace("not_implemented", f"({agent} not available yet)"),
    }
