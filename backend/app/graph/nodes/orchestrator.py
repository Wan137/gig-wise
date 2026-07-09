"""Classifies user intent and builds the subtask queue the dispatcher will work through."""
from __future__ import annotations

import logging

from langchain_core.messages import SystemMessage
from pydantic import BaseModel, Field

from app.graph.llm import get_llm
from app.graph.prompts.orchestrator_prompts import ORCHESTRATOR_SYSTEM_PROMPT
from app.graph.state import CopilotState, Intent, SubtaskType
from app.graph.utils import make_trace

logger = logging.getLogger(__name__)


class OrchestratorDecision(BaseModel):
    intent: Intent
    subtask_queue: list[SubtaskType] = Field(default_factory=list)
    reasoning: str = Field(description="One short sentence explaining the routing decision.")


def orchestrator_node(state: CopilotState) -> dict:
    llm = get_llm(temperature=0.0).with_structured_output(OrchestratorDecision)

    try:
        decision = llm.invoke([SystemMessage(content=ORCHESTRATOR_SYSTEM_PROMPT), *state["messages"]])
    except Exception:
        logger.exception("Orchestrator LLM call failed; falling back to tax_question routing")
        # A routing failure shouldn't take down the whole turn - fall back to
        # the single most common intent (tax_question) rather than dead-ending.
        return {
            "intent": "tax_question",
            "subtask_queue": ["tax_question"],
            "active_agent": None,
            "trace": make_trace("orchestrator", "Understanding your question..."),
        }

    subtask_queue = list(decision.subtask_queue)
    # Defensive backstop: if the model classifies a specialist intent but
    # forgets to populate subtask_queue (structured output isn't infallible),
    # default it to a single-item queue matching the intent instead of
    # silently dropping the request.
    if decision.intent in ("tax_question", "expense_entry", "financial_planning") and not subtask_queue:
        subtask_queue = [decision.intent]  # type: ignore[list-item]

    logger.info(
        "Orchestrator routed intent=%s subtask_queue=%s reasoning=%r",
        decision.intent,
        subtask_queue,
        decision.reasoning,
    )

    return {
        "intent": decision.intent,
        "subtask_queue": subtask_queue,
        "active_agent": None,
        "trace": make_trace("orchestrator", "Understanding your question..."),
    }
