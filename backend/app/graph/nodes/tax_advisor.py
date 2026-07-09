"""RAG-grounded answers to LHDN/EPF/SOCSO questions, always cited to a source."""
from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.graph.llm import get_llm
from app.graph.prompts.tax_advisor_prompts import (
    TAX_ADVISOR_SYSTEM_PROMPT,
    format_chunks_for_prompt,
    format_citations_footer,
)
from app.graph.state import CopilotState, RetrievedChunk
from app.graph.utils import append_draft, latest_user_message, make_trace
from app.rag.retriever import RagIndexNotBuiltError, TaxKnowledgeRetriever

logger = logging.getLogger(__name__)

_FALLBACK_MESSAGE = (
    "I'm having trouble reaching my tax knowledge base right now, so I don't want to guess at an "
    "answer that could be wrong. Please try again shortly, or check hasil.gov.my directly."
)

_retriever: TaxKnowledgeRetriever | None = None


def _get_retriever() -> TaxKnowledgeRetriever:
    global _retriever
    if _retriever is None:
        _retriever = TaxKnowledgeRetriever()
    return _retriever


def _already_logged_expense_note(state: CopilotState) -> str:
    """A "multi" turn can run expense_tracker before tax_advisor in the same
    turn; without this, the Tax Advisor has no way to know a receipt was
    already logged and will confusingly claim it "can't log receipts" even
    though the Expense Tracker's summary is already sitting right above it in
    the same reply.
    """
    records = state.get("expense_records")
    if not records:
        return ""
    latest = records[-1]
    return (
        f"(Context: earlier in this same turn, an expense was already logged - "
        f"category={latest.get('category')}, amount=RM{latest.get('amount')}, "
        f"tax_deductible={latest.get('tax_deductible')}. Do not say you can't log receipts; "
        f"that already happened. Just answer the tax question below.)\n\n"
    )


def tax_advisor_node(state: CopilotState) -> dict:
    query = latest_user_message(state)

    try:
        retriever = _get_retriever()
        chunks = retriever.retrieve(query, top_k=5)
    except RagIndexNotBuiltError:
        logger.error("Tax Advisor called before the RAG index was built")
        return {
            "draft_answer": append_draft(state, _FALLBACK_MESSAGE),
            "trace": make_trace("tax_advisor", "Checking LHDN guidelines..."),
        }
    except Exception:
        logger.exception("Retrieval failed in tax_advisor_node")
        return {
            "draft_answer": append_draft(state, _FALLBACK_MESSAGE),
            "trace": make_trace("tax_advisor", "Checking LHDN guidelines..."),
        }

    context = format_chunks_for_prompt(chunks)
    system_prompt = TAX_ADVISOR_SYSTEM_PROMPT.format(context=context)

    try:
        llm = get_llm(temperature=0.1)
        human_content = _already_logged_expense_note(state) + query
        response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=human_content)])
        answer_text = response.content if isinstance(response.content, str) else str(response.content)
    except Exception:
        logger.exception("LLM call failed in tax_advisor_node")
        return {
            "draft_answer": append_draft(state, _FALLBACK_MESSAGE),
            "retrieved_chunks": (state.get("retrieved_chunks") or []) + [
                RetrievedChunk(
                    content=c.content,
                    source_document=c.source_document,
                    section=c.section,
                    source_url=c.source_url,
                    score=c.score,
                )
                for c in chunks
            ],
            "trace": make_trace("tax_advisor", "Checking LHDN guidelines..."),
        }

    footer = format_citations_footer(chunks)
    answer_with_footer = f"{answer_text}\n{footer}" if footer else answer_text

    return {
        "draft_answer": append_draft(state, answer_with_footer),
        "retrieved_chunks": (state.get("retrieved_chunks") or []) + [
            RetrievedChunk(
                content=c.content,
                source_document=c.source_document,
                section=c.section,
                source_url=c.source_url,
                score=c.score,
            )
            for c in chunks
        ],
        "trace": make_trace("tax_advisor", "Checking LHDN guidelines..."),
    }
