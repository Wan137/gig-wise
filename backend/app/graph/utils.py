"""Small helpers shared across graph nodes."""
from __future__ import annotations

from datetime import datetime, timezone

from langchain_core.messages import HumanMessage

from app.graph.state import AgentTrace, CopilotState, DraftSegment


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


def make_segment(agent: str, text: str) -> list[DraftSegment]:
    """A specialist agent's contribution for this turn, to be merged via the
    `draft_segments` reducer. Kept separate per-agent (rather than
    concatenated into one string) so the Verifier can check each segment
    against the right ground truth for its own agent - see DraftSegment's
    docstring in state.py for why.
    """
    return [DraftSegment(agent=agent, text=text)]
