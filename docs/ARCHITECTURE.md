# Architecture

## Why a supervisor/worker graph

Some turns need exactly one agent ("what tax form do I file?" -> Tax Advisor only).
Others need a chain ("how much should I set aside this month?" needs the Expense
Tracker's aggregated deductions before the Financial Planner can compute chargeable
income). A linear chain wastes calls on simple turns; a fully-connected mesh is hard
to reason about or extend. Instead, the Orchestrator classifies intent and emits an
ordered `subtask_queue`; a `dispatcher` node pops one subtask at a time and routes to
the matching agent until the queue is empty, then always funnels through the
`verifier` before the `responder`. Adding a future agent means adding one node and one
subtask type, not rewriting control flow.

## State schema

See `backend/app/graph/state.py` for the authoritative `TypedDict` definitions. Summary:

- `messages` - conversation history (LangGraph `add_messages` reducer)
- `intent` / `subtask_queue` / `active_agent` - routing state set by the orchestrator,
  consumed by the dispatcher
- `retrieved_chunks` - RAG hits for the current turn, each tagged with source document
  and section so every tax claim is traceable
- `tax_calc` / `epf_socso` - structured output of the deterministic finance calculators
  (never LLM-generated numbers)
- `expense_records` - OCR + classification output for uploaded receipts
- `draft_answer` / `verification` / `final_answer` - the guardrails pipeline
- `trace` - append-only list of human-readable status strings (`operator.add`
  reducer), streamed to the frontend over SSE as each node runs

## Nodes and edges

```
START
  -> orchestrator          (Groq, JSON-mode intent + entity extraction, builds subtask_queue)
  -> dispatcher              (conditional edge: pops next subtask, routes to the matching
                               agent, or -> verifier once the queue is empty)
      -> tax_advisor          (embed query -> Chroma retrieve -> Groq answer grounded in chunks) -> dispatcher
      -> expense_tracker      (Tesseract OCR -> preprocess -> Groq category classification) -> dispatcher
      -> financial_planner    (pure-Python tax/EPF/SOCSO calculators; Groq only phrases
                                the explanation) -> dispatcher
  -> verifier                 (guardrails, see below)
      -> dispatcher            (conditional edge: verification failed and retry_count < 2
                                 -> loop back to active_agent with corrective feedback)
      -> responder              (verification passed, or retries exhausted -> ships with
                                  a flagged_for_review marker instead of failing silently)
  -> END
```

## Verification layer

This is deliberately not "ask the LLM if it's sure" - it is two mechanical checks with
a real ground truth to check against.

**Tax Advisor answers.** Every claim in `draft_answer` must trace back to a chunk in
`retrieved_chunks`. A second Groq call acts as an NLI-style judge - given
`(claim, source_chunk)` it returns `supported` / `unsupported` / `partial` per
sentence, in strict JSON. Any `unsupported` claim is stripped or the answer is
regenerated once with the offending claim flagged in the prompt. If it still fails,
the response ships with an explicit "confirm with LHDN/a tax agent" flag rather than
presenting an unverified fact as settled.

**Financial Planner answers.** `tax_calc` / `epf_socso` are computed once by
deterministic Python (`backend/app/finance/`) and treated as ground truth. The
verifier regex-extracts every RM figure in the LLM's explanation and diffs each
against the calculator's own dict (tolerance: rounding only). Any mismatch means the
LLM mis-stated a number - in that case the LLM's prose is discarded and the
explanation is re-rendered from a template that injects the verified numbers
directly. The LLM is never the source of a number that reaches the user.

## Streaming reasoning steps

Built on `graph.astream_events(version="v2")`. Each node appends a small trace entry
to `state["trace"]` on entry; the FastAPI SSE endpoint (`backend/app/routers/chat.py`)
reads events off that stream and forwards a mapped human-readable string per node
(`orchestrator` -> "Understanding your question...", `tax_advisor` -> "Checking LHDN
guidelines...", `financial_planner` -> "Calculating your estimate...", `verifier` ->
"Double-checking the numbers..."). This rides the same graph execution the backend
already performs - no separate polling/status infrastructure.

## Data sources

RAG knowledge base is built from public LHDN guides for self-employed individuals /
gig workers, plus public EPF i-Saraan and SOCSO SKSPS (self-employment scheme)
contribution information. Source documents live in `backend/app/rag/documents/` with
their origin URL and retrieval date recorded in `backend/app/rag/documents/SOURCES.md`
so every fact in the knowledge base is auditable back to an official document.
