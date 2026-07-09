# Gig-Wise: Gig Economy Financial Copilot

A multi-agent AI system that helps Malaysian gig economy workers (e-hailing
drivers, delivery riders, freelancers) understand their taxes, track deductible
expenses, and plan how much to set aside for LHDN filing, EPF, and SOCSO.

## Why this exists

Gig workers in Malaysia are self-employed for tax purposes. Most don't have
access to an accountant and don't know: how LHDN e-Filing works for business
income, whether voluntary EPF/SOCSO contributions make sense for them, how to
track deductible expenses properly, or how much to set aside each quarter.
Gig-Wise acts as an always-available, source-grounded financial copilot for
exactly that gap.

## Architecture

A LangGraph state graph with a supervisor/dispatcher pattern coordinates four
specialized agents:

- **Orchestrator** - classifies intent, builds a subtask queue for single or
  multi-agent turns
- **Tax Advisor** - RAG over real LHDN self-employed/gig-worker tax guides,
  always cites the source document and section
- **Expense Tracker** - OCR (Tesseract) + classification of uploaded receipts
  into gig-work-relevant deductible categories
- **Financial Planner** - deterministic Python tax/EPF/SOCSO calculators; the
  LLM only narrates results it did not compute
- **Verifier** - a guardrails layer that cross-checks every tax claim against
  retrieved source chunks and every number against the calculator's own
  output, before anything reaches the user

Full design rationale: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Tech stack

| Layer | Choice |
|---|---|
| LLM | Groq API (Llama 3.3 70B) |
| Agent orchestration | LangGraph |
| Embeddings / vector store | sentence-transformers (local) + ChromaDB |
| OCR | Tesseract |
| Backend | FastAPI + Server-Sent Events |
| Database | SQLite |
| Frontend | React + Tailwind CSS |

## Project layout

```
backend/    FastAPI app, LangGraph graph + nodes, RAG pipeline, finance
            calculators, OCR pipeline, tests
frontend/   React + Tailwind dashboard and chat UI
docs/       Architecture notes and document sourcing log
```

## Status

Under active development. See `docs/ARCHITECTURE.md` and the task list for
current progress; this README will gain setup and deployment instructions as
each layer lands.

## Disclaimer

Gig-Wise provides general information based on public LHDN, EPF, and SOCSO
guidance. It is not a substitute for advice from a licensed tax agent or
financial advisor, and it does not file anything on your behalf.
