"""Pops one subtask at a time off the queue and routes to the matching agent.

Split into two halves because LangGraph conditional-edge functions are pure
routing functions - they can inspect state but cannot mutate it. Popping the
queue is therefore a real node (dispatcher_node); deciding where to go next
based on the result is the paired routing function (route_from_dispatcher).
"""
from __future__ import annotations

from app.graph.state import CopilotState

# Agents not yet implemented route here instead of crashing the graph -
# replaced by real nodes as Tasks 5/6 land.
_IMPLEMENTED_AGENTS = {"tax_question": "tax_advisor"}


def dispatcher_node(state: CopilotState) -> dict:
    queue = list(state.get("subtask_queue") or [])
    if not queue:
        return {"active_agent": None}
    next_task = queue.pop(0)
    return {"subtask_queue": queue, "active_agent": next_task}


def route_from_dispatcher(state: CopilotState) -> str:
    active = state.get("active_agent")
    if active is None:
        return "responder"
    return _IMPLEMENTED_AGENTS.get(active, "not_implemented")
