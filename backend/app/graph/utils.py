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
