# ThinkBook LM

A fully local, AI-powered research and learning assistant inspired by Google's NotebookLM. Users organize documents into notebooks, retrieve information using semantic search and local embeddings, and interact through a grounded workspace with studio learning tools.

Everything runs locally: no cloud LLM or paid embedding APIs required.

---

## Current Status

**Milestone 2 + NotebookLM UI.**
- **Backend**: FastAPI app with PostgreSQL persistence (`psycopg3`), local ChromaDB vector store, document text extraction (`pdf`, `docx`, `txt`), chunking pipeline, and local semantic retrieval (`qwen3-embedding:0.6b` via Ollama).
- **Frontend**: Full Google NotebookLM dark-mode interface with a 3-panel workspace:
  - **Left Panel (Sources)**: Source upload (drag-and-drop), web search stub, and document indexing status with scope checkboxes.
  - **Center Panel (Chat / Canvas)**: Waving hand welcome screen, prompt suggestion pills, conversation thread with distance score citations, and bottom rounded search bar.
  - **Right Panel (Studio)**: Multilingual Audio Overview banner, interactive reports promo, 9 Studio tool cards, and quick note-taking.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, Tailwind CSS v4, built with Vite |
| **Backend** | Python 3.10+, FastAPI, Uvicorn |
| **Relational Data** | PostgreSQL (accessed directly via `psycopg3` connection pool, no ORM) |
| **Vector Store** | ChromaDB (local on-disk persistence) |
| **Embeddings** | `qwen3-embedding:0.6b` served via Ollama |
| **Local LLM** | `qwen3:1.7b` served via Ollama |

---

## High-Level Architecture

```
frontend/                 React 19 + Tailwind CSS (Vite dev server proxies /api -> :8000)
  src/components/
    Navbar.jsx            Top header with notebook switcher, + Create notebook, profile
    SourcesPanel.jsx      Left column: source management, upload dropzone, scope filters
    ChatPanel.jsx         Center column: welcome canvas, retrieval queries, citations
    StudioPanel.jsx       Right column: Studio cards (Audio, Mind Map, Flashcards, Notes)
    CreateNotebookModal.jsx Modal dialog for new notebook creation
backend/                  FastAPI app running on :8000
  app/api/routes/         Endpoints for /health, /notebooks, /documents, /retrieve
  app/services/           db, storage, vector_store, embedding, indexing, retrieval
  app/repositories/       psycopg3 SQL queries for notebooks, documents, chunks
  app/models/             Pydantic models for data validation and API schemas
  migrations/             SQL schema migrations (0001_initial_schema.sql, 0002_indexing_status.sql)
  scripts/migrate.py      Lightweight migration runner
```

---

## Local Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL running locally (database `thinkbook_lm`)
- [Ollama](https://ollama.com) running with the embedding model:
  ```bash
  ollama pull qwen3-embedding:0.6b
  ollama pull qwen3:1.7b
  ```

### 1. Backend Setup

```bash
cd backend

# Create & activate virtualenv
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env         # Windows
# cp .env.example .env         # macOS/Linux

# Run database migrations
python scripts/migrate.py

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://127.0.0.1:8000`. Check Swagger docs at `http://127.0.0.1:8000/docs` and health at `http://127.0.0.1:8000/health/services`.

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```

The app will run at `http://localhost:5173`. In development, Vite proxies all `/api/*` calls directly to `http://localhost:8000`.

---

## Running Tests

From the `backend/` directory with virtualenv active:

```bash
# Run all tests (embedding, ingestion, vector store, retrieval)
python -m pytest

# Run only unit tests without Ollama dependency
python -m pytest -m "not integration"
```
