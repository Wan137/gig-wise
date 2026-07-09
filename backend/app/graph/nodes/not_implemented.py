"""Graceful placeholder for subtasks whose specialist agent isn't built yet.

Loops back to the dispatcher rather than dead-ending, so a "multi" intent
turn that needs both an implemented and an unimplemented agent still
completes the parts it can.
"""
from __future__ import annotations

from app.graph.state import CopilotState
from app.graph.utils import append_draft, make_trace

_FRIENDLY_MESSAGE_BY_AGENT = {
    "financial_planning": (
        "Tax/EPF/SOCSO calculations aren't available yet - the Financial Planner is still being built. "
        "Check back soon!"
    ),
}


def not_implemented_node(state: CopilotState) -> dict:
    agent = state.get("active_agent") or "that feature"
    message = _FRIENDLY_MESSAGE_BY_AGENT.get(agent, f"{agent} isn't available yet - check back soon!")
    return {
        "draft_answer": append_draft(state, message),
        "trace": make_trace("not_implemented", f"({agent} not available yet)"),
    }
