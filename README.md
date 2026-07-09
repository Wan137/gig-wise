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

## Backend setup (development)

Requires [Tesseract OCR](https://github.com/UB-Mannheim/tesseract) installed separately (it's a
system binary, not a Python package) - on Windows: `winget install --id UB-Mannheim.TesseractOCR`;
on Debian/Ubuntu (and the deploy Dockerfile): `apt-get install tesseract-ocr`. If it's not on your
PATH, set `TESSERACT_CMD` in `.env` to its full executable path.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements-dev.txt
copy .env.example .env          # fill in GROQ_API_KEY, and generate a JWT_SECRET_KEY:
                                 #   python -c "import secrets; print(secrets.token_hex(32))"
alembic upgrade head             # creates the SQLite schema
python scripts/ingest_documents.py   # builds the Chroma index from backend/app/rag/documents
pytest                                 # runs the test suite
uvicorn app.main:app --reload          # starts the API on http://localhost:8000
```

The RAG knowledge base is built from real public LHDN/EPF/SOCSO documents
committed in `backend/app/rag/documents/` (see `SOURCES.md` there for origin
URLs and retrieval dates). `ingest_documents.py` chunks them, embeds them
locally with sentence-transformers, and persists the vectors to
`backend/chroma_db/` (gitignored - rebuild it anytime with that script).

## API surface

| Endpoint | Purpose |
|---|---|
| `POST /auth/signup`, `POST /auth/login`, `GET /auth/me` | Account creation and JWT auth |
| `POST /chat/sessions`, `GET /chat/sessions` | Create/list conversations |
| `GET /chat/sessions/{id}/messages` | Conversation history |
| `POST /chat/sessions/{id}/messages` | Send a message - streams `trace` / `final` / `error` events over SSE as the graph runs |
| `POST /expenses/upload` | Upload a receipt photo - runs OCR + classification directly, persists the result |
| `GET /expenses`, `GET /expenses/summary` | List logged expenses / category totals for the dashboard |
| `GET /profile/tax-profile`, `PUT /profile/tax-profile` | The user's age/sector/EPF status/income estimate |

Interactive API docs are available at `/docs` once the server is running.

## Status

Under active development. See `docs/ARCHITECTURE.md` and the task list for
current progress; this README will gain full API/frontend setup and
deployment instructions as each layer lands.

## Disclaimer

Gig-Wise provides general information based on public LHDN, EPF, and SOCSO
guidance. It is not a substitute for advice from a licensed tax agent or
financial advisor, and it does not file anything on your behalf.
