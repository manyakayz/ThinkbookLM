# ThinkBook LM

A fully local, AI-powered research and learning assistant. Users organize
their own documents into notebooks, retrieve information from them using
semantic search and RAG, and get grounded answers — with learning tools
(summaries, flashcards, quizzes, Study Mode) planned for later.

Everything runs locally: no cloud LLM or embedding APIs.

## Current status

**Foundation milestone.** This repository currently contains the project
scaffolding only:

- A FastAPI backend that starts up, serves a health check, and defines
  clean *integration boundaries* to Postgres, ChromaDB, and Ollama — without
  implementing document ingestion, retrieval, RAG, chat, or study tools yet.
- A React + Tailwind frontend with a single page that confirms it can reach
  the backend.

Nothing beyond this foundation has been built yet. See
["What's deliberately not built yet"](#whats-deliberately-not-built-yet) below.

## Tech stack

| Layer            | Technology                                   |
|-------------------|-----------------------------------------------|
| Frontend          | React + Tailwind CSS, built with Vite         |
| Backend           | Python, FastAPI                               |
| Relational data   | PostgreSQL (accessed directly via psycopg3, no ORM) |
| Vector store       | ChromaDB (local, on-disk persistence)         |
| Local LLM          | Qwen3 1.7B, served through Ollama             |
| Embeddings        | Qwen3-Embedding-0.6B                          |

Target development environment: a Windows laptop with an Intel Core
i5-1135G7, 8 GB RAM, and Iris Xe integrated graphics — everything here is
chosen to stay light enough to run comfortably on that hardware.

## High-level architecture

```
frontend/   React + Tailwind (Vite). Talks to the backend over HTTP.
backend/    FastAPI app.
  app/api/routes/    HTTP route handlers (currently: health only)
  app/services/      Thin boundaries to Postgres, ChromaDB, and Ollama —
                      each knows how to *connect*, not yet how to do the
                      actual RAG/study-tool work
  app/models/         Pydantic schemas & DB row models (not designed yet)
  app/core/            Cross-cutting utilities (logging, etc.)
  app/config.py        All environment-driven settings in one place
  app/main.py          App entrypoint: FastAPI instance, CORS, routers
```

Each external system (Postgres, ChromaDB, Ollama) is optional at startup —
the backend will boot and serve `/health` even if none of them are running
yet. `/health/services` reports which ones are currently reachable, which is
useful while setting up your local environment.

### Architectural decisions worth flagging

- **Vite instead of Create React App.** The brief asked for "React and
  Tailwind CSS" without naming a build tool. CRA is effectively deprecated;
  Vite is the current standard, has a much lighter dev-server footprint
  (relevant on an 8 GB machine), and integrates with Tailwind v4 via an
  official plugin with no extra config files.
- **No ORM**, per the brief — `backend/app/services/db.py` uses `psycopg3`
  directly with a small connection pool. No schema is defined yet.
- **Dev-mode API proxy.** `frontend/vite.config.js` proxies `/api/*` to
  `http://localhost:8000` so the frontend can call a relative path in
  development instead of hardcoding a host. The backend also has CORS
  enabled directly (see `backend/.env.example`) for flexibility if you'd
  rather call it directly.
- **All three external integrations connect lazily.** Postgres, ChromaDB,
  and Ollama clients are only created on first use (or on a `/health/services`
  call), not at import/startup time, so you can develop the frontend or
  backend without all three services running simultaneously.

## Local setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- (Optional for now, needed later) PostgreSQL, [Ollama](https://ollama.com)
  with the `qwen3:1.7b` model pulled

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
copy .env.example .env       # Windows: copy, macOS/Linux: cp
uvicorn app.main:app --reload
```

The API will be running at `http://localhost:8000`. Check
`http://localhost:8000/health` and `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app will be running at `http://localhost:5173` and should show a
"Backend connected" badge if the backend is also running.

## What's deliberately not built yet

Per the current milestone's scope, the following are **not** implemented and
will come in later milestones:

- Authentication / user accounts
- Notebook, document, and conversation database schema
- Document upload and processing (PDF/DOCX/TXT)
- Embedding generation
- ChromaDB ingestion and retrieval
- The RAG pipeline and grounded chat
- Study Mode, flashcards, and quizzes
- Audio, OCR, or web search features

The `app/services/` boundary modules exist so these can be built on top of a
stable connection layer without re-plumbing configuration later.
