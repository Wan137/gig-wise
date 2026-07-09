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
- `draft_segments` - each specialist's raw, not-yet-verified output for this turn,
  tagged with which agent produced it (see "Verification layer" below for why this is
  a list of tagged segments rather than one shared string)
- `draft_answer` / `verification` / `final_answer` - the guardrails pipeline's output
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
  -> verifier                 (guardrails, see below) -> responder -> END
```

## Verification layer

This is deliberately not "ask the LLM if it's sure" - it is two mechanical checks with
a real ground truth to check against, applied per-agent-segment rather than to one
merged block of text.

**Why per-segment, not one shared string.** The first implementation had every agent
append straight into a single `draft_answer` string. That broke in a very instructive
way during testing: the Tax Advisor legitimately cites general LHDN figures (rates,
relief thresholds) that have nothing to do with a specific user's computed plan. A
numeric check run over the whole merged text flagged those legitimate citations as
"unverified" simply because they weren't the Financial Planner's numbers. The fix was
to have each agent contribute a tagged `DraftSegment {agent, text}` instead; the
Verifier then checks each segment against the *right* ground truth for its own agent -
retrieved chunks for a `tax_advisor` segment, `tax_calc`/`epf_socso` for a
`financial_planner` segment - and only then joins the (possibly corrected) segments
into `draft_answer`.

**Tax Advisor segments.** Every claim must trace back to a chunk in `retrieved_chunks`.
A second Groq call acts as a fact-checking judge - given the segment text and the
actual source chunks, it returns a `supported` / `unsupported` / `partially_supported`
verdict per distinct claim, in strict JSON. Any `unsupported` claim causes a visible
disclaimer to be appended, explicitly naming which statement(s) couldn't be verified
and pointing the user to LHDN/KWSP/PERKESO or a licensed tax agent - never silently
presenting an unverified claim as settled fact. If the judge call itself fails (e.g.
an API outage), the check fails *closed*: the segment still gets the disclaimer rather
than shipping unchecked. (Scope note: the original design also described a
regenerate-once-then-flag retry loop; the shipped v1 uses the simpler single-pass
check-and-disclose approach, which already fully prevents an unverified claim from
reaching the user - the retry loop is a natural next iteration, not a requirement for
correctness.)

**Financial Planner segments.** `tax_calc` / `epf_socso` are computed once by
deterministic Python (`backend/app/finance/`) and treated as ground truth. Each segment
stores the LLM's narration and the deterministic breakdown block separately (joined by
an internal delimiter), so the verifier can regex-extract every RM figure the LLM
mentioned in *just the narration* and diff each against the calculator's own values -
including their legitimate monthly/annual restatements - with a small tolerance for
rounding only. Any mismatch means the LLM fabricated or mis-stated a number: in that
case the narration is discarded entirely and replaced with the deterministic breakdown
alone. The LLM is never the source of a number that reaches the user. This isn't
theoretical - integration testing caught the Tax Advisor inventing a tax total in prose
(RM1,020, having silently skipped the RM9,000 personal relief) sitting right next to
the correct deterministic figure (RM140) in the same reply, before this layer existed.

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
