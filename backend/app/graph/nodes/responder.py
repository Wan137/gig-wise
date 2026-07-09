"""Finalizes the turn: either passes through a specialist's (verified) draft, or
replies directly for general chit-chat that never needed a specialist agent.
"""
from __future__ import annotations

import logging

from langchain_core.messages import AIMessage, SystemMessage

from app.graph.llm import get_llm
from app.graph.prompts.responder_prompts import GENERAL_CHAT_SYSTEM_PROMPT
from app.graph.state import CopilotState
from app.graph.utils import make_trace

logger = logging.getLogger(__name__)

_FALLBACK_MESSAGE = "Sorry, I couldn't put together a reply just now. Please try asking again."


def responder_node(state: CopilotState) -> dict:
    draft = state.get("draft_answer")

    if draft:
        final_answer = draft
    else:
        try:
            llm = get_llm(temperature=0.4)
            response = llm.invoke([SystemMessage(content=GENERAL_CHAT_SYSTEM_PROMPT), *state["messages"]])
            final_answer = response.content if isinstance(response.content, str) else str(response.content)
        except Exception:
            logger.exception("LLM call failed in responder_node (general chat path)")
            final_answer = _FALLBACK_MESSAGE

    return {
        "final_answer": final_answer,
        "messages": [AIMessage(content=final_answer)],
        "trace": make_trace("responder", "Preparing your answer..."),
    }
