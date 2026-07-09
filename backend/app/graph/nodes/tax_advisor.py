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
from app.graph.utils import latest_user_message, make_trace
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


def tax_advisor_node(state: CopilotState) -> dict:
    query = latest_user_message(state)

    try:
        retriever = _get_retriever()
        chunks = retriever.retrieve(query, top_k=5)
    except RagIndexNotBuiltError:
        logger.error("Tax Advisor called before the RAG index was built")
        return {
            "draft_answer": _FALLBACK_MESSAGE,
            "retrieved_chunks": [],
            "trace": make_trace("tax_advisor", "Checking LHDN guidelines..."),
        }
    except Exception:
        logger.exception("Retrieval failed in tax_advisor_node")
        return {
            "draft_answer": _FALLBACK_MESSAGE,
            "retrieved_chunks": [],
            "trace": make_trace("tax_advisor", "Checking LHDN guidelines..."),
        }

    context = format_chunks_for_prompt(chunks)
    system_prompt = TAX_ADVISOR_SYSTEM_PROMPT.format(context=context)

    try:
        llm = get_llm(temperature=0.1)
        response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=query)])
        answer_text = response.content if isinstance(response.content, str) else str(response.content)
    except Exception:
        logger.exception("LLM call failed in tax_advisor_node")
        return {
            "draft_answer": _FALLBACK_MESSAGE,
            "retrieved_chunks": [RetrievedChunk(**c.__dict__) for c in chunks],
            "trace": make_trace("tax_advisor", "Checking LHDN guidelines..."),
        }

    footer = format_citations_footer(chunks)
    draft_answer = f"{answer_text}\n{footer}" if footer else answer_text

    return {
        "draft_answer": draft_answer,
        "retrieved_chunks": [
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
