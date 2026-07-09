"""Small helpers shared across graph nodes."""
from __future__ import annotations

from datetime import datetime, timezone

from langchain_core.messages import HumanMessage

from app.graph.state import AgentTrace, CopilotState


def latest_user_message(state: CopilotState) -> str:
    for message in reversed(state["messages"]):
        if isinstance(message, HumanMessage):
            content = message.content
            return content if isinstance(content, str) else str(content)
    return ""


def make_trace(node: str, message: str) -> list[AgentTrace]:
    return [
        AgentTrace(
            node=node,
            message=message,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    ]


def append_draft(state: CopilotState, new_text: str) -> str:
    """Combines a specialist agent's output with any prior draft from the same turn.

    A "multi" intent turn runs several agents back-to-back before the
    responder ever sees the state, so a node must never blindly overwrite
    `draft_answer` - doing so silently discards an earlier agent's (already
    correct) answer instead of adding to it.
    """
    existing = state.get("draft_answer")
    return f"{existing}\n\n{new_text}" if existing else new_text
