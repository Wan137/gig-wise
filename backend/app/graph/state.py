"""Shared state schema threaded through every node in the copilot graph.

This is the in-memory shape used while a single turn is being processed by
the graph - it is not what's persisted between turns (see app/db/models.py
for that). `messages` and `trace` use LangGraph reducers (`add_messages`,
`operator.add`) so that nodes only need to return the *new* items for that
key, not the full accumulated list - LangGraph merges them into state itself.
"""
from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

Intent = Literal["tax_question", "expense_entry", "financial_planning", "general", "multi"]
SubtaskType = Literal["tax_question", "expense_entry", "financial_planning"]


class AgentTrace(TypedDict):
    node: str
    message: str
    timestamp: str


class RetrievedChunk(TypedDict):
    content: str
    source_document: str
    section: str
    source_url: str
    score: float


class TaxCalculationResult(TypedDict, total=False):
    assessment_year: int
    gross_income: float
    allowable_expenses: float
    chargeable_income: float
    tax_owed: float
    bracket_breakdown: list[dict]


class EPFSocsoResult(TypedDict, total=False):
    epf_suggested_monthly: float
    socso_scheme: str
    socso_monthly: float
    notes: list[str]


class ExpenseRecordState(TypedDict, total=False):
    id: str
    raw_ocr_text: str
    vendor: str | None
    amount: float | None
    date: str | None
    category: str
    tax_deductible: bool
    ocr_confidence: float


class VerificationResult(TypedDict, total=False):
    passed: bool
    checks: list[dict]
    corrected_answer: str | None
    flagged_for_review: bool


class CopilotState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    session_id: str

    # Set by the orchestrator, consumed by the dispatcher.
    intent: Intent | None
    subtask_queue: list[SubtaskType]
    active_agent: str | None

    # Working data populated by specialist agents for the current turn.
    retrieved_chunks: list[RetrievedChunk]
    tax_calc: TaxCalculationResult | None
    epf_socso: EPFSocsoResult | None
    expense_records: list[ExpenseRecordState]
    pending_receipt: str | None

    # The guardrails pipeline.
    draft_answer: str | None
    verification: VerificationResult | None
    final_answer: str | None

    # Observability - streamed to the frontend over SSE as each node runs.
    trace: Annotated[list[AgentTrace], operator.add]
    error: str | None
    retry_count: int


def initial_state(user_id: str, session_id: str, user_message: str) -> CopilotState:
    """Builds a fresh state for a single incoming user turn."""
    from langchain_core.messages import HumanMessage

    return CopilotState(
        messages=[HumanMessage(content=user_message)],
        user_id=user_id,
        session_id=session_id,
        intent=None,
        subtask_queue=[],
        active_agent=None,
        retrieved_chunks=[],
        tax_calc=None,
        epf_socso=None,
        expense_records=[],
        pending_receipt=None,
        draft_answer=None,
        verification=None,
        final_answer=None,
        trace=[],
        error=None,
        retry_count=0,
    )
