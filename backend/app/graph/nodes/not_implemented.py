"""Graceful placeholder for subtasks whose specialist agent isn't built yet.

Loops back to the dispatcher rather than dead-ending, so a "multi" intent
turn that needs both an implemented and an unimplemented agent still
completes the parts it can.
"""
from __future__ import annotations

from app.graph.state import CopilotState
from app.graph.utils import make_trace

_FRIENDLY_MESSAGE_BY_AGENT = {
    "expense_entry": (
        "Expense tracking (receipt upload and categorization) isn't available yet - it's still being built. "
        "Check back soon!"
    ),
    "financial_planning": (
        "Tax/EPF/SOCSO calculations aren't available yet - the Financial Planner is still being built. "
        "Check back soon!"
    ),
}


def not_implemented_node(state: CopilotState) -> dict:
    agent = state.get("active_agent") or "that feature"
    message = _FRIENDLY_MESSAGE_BY_AGENT.get(agent, f"{agent} isn't available yet - check back soon!")
    existing_draft = state.get("draft_answer")
    combined = f"{existing_draft}\n\n{message}" if existing_draft else message
    return {
        "draft_answer": combined,
        "trace": make_trace("not_implemented", f"({agent} not available yet)"),
    }
