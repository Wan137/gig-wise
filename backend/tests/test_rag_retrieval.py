"""Regression test for RAG retrieval quality against the built Chroma index.

This does not rebuild the index - it exercises the same persisted index the
app will query at runtime (built via `python scripts/ingest_documents.py`),
because embedding a full corpus on every test run is a build-time cost, not a
unit-test cost. If the index hasn't been built yet, these tests skip with a
clear message rather than failing.
"""
from __future__ import annotations

import pytest

from app.rag.ingest import DOCUMENTS_DIR
from app.rag.retriever import RagIndexNotBuiltError, TaxKnowledgeRetriever

pytestmark = pytest.mark.skipif(
    not (DOCUMENTS_DIR.parent.parent.parent / "chroma_db").exists(),
    reason="Chroma index not built - run `python scripts/ingest_documents.py` first",
)


@pytest.fixture(scope="module")
def retriever() -> TaxKnowledgeRetriever:
    try:
        return TaxKnowledgeRetriever()
    except RagIndexNotBuiltError as exc:
        pytest.skip(str(exc))


@pytest.mark.parametrize(
    "query,expected_source_substring",
    [
        ("How much tax do I pay on RM60,000 chargeable income?", "Tax Rate Schedule"),
        ("Can I claim fuel expenses as a business deduction?", "Allowable & Disallowed Expenses"),
        ("How does i-Saraan Plus work for e-hailing drivers?", "i-Saraan Plus"),
        ("What is the SOCSO contribution for self-employed workers?", "SKSPS"),
    ],
)
def test_retrieval_returns_relevant_source(retriever, query, expected_source_substring):
    results = retriever.retrieve(query, top_k=3)
    assert results, f"No results returned for query: {query!r}"
    top_sources = [r.source_document for r in results]
    assert any(expected_source_substring in src for src in top_sources), (
        f"Expected a result mentioning {expected_source_substring!r} in top-3 for "
        f"query {query!r}, got sources: {top_sources}"
    )


def test_every_result_has_a_traceable_citation(retriever):
    results = retriever.retrieve("What expenses can a gig worker deduct?", top_k=5)
    assert results
    for r in results:
        assert r.source_document and r.source_document != "Unknown source"
        assert r.section, "every chunk must carry a page number or section heading"
        assert r.source_url.startswith("http"), "every chunk must trace back to a public URL"


def test_empty_query_returns_no_results(retriever):
    assert retriever.retrieve("", top_k=3) == []
    assert retriever.retrieve("   ", top_k=3) == []
