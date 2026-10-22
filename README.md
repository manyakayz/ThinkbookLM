# ThinkBook LM

A fully local, AI-powered research and learning assistant inspired by Google's NotebookLM. Users organize documents into notebooks, retrieve information using semantic search and local embeddings, and interact through a grounded RAG workspace.

Everything runs locally: no cloud LLM or paid embedding APIs required.

---

## Current Status

**Part 1 Complete: Local LLM, Document Ingestion, Semantic Retrieval & Grounded RAG Pipeline.**

- **Local Models (Ollama)**:
  - **Generation**: `qwen3:1.7b` (Qwen3 1.7B parameter instruction model, ~1.0 GB VRAM/RAM).
  - **Embeddings**: `qwen3-embedding:0.6b` (1024-dimensional dense vectors, ~400 MB VRAM/RAM).
- **Document Ingestion & Chunking**:
  - Supports `.pdf`, `.docx`, and `.txt` files up to 25 MB.
  - Character-based chunking with configurable overlap (default 1200 chars / 200 overlap).
  - Automatic indexing into PostgreSQL provenance tables (`documents`, `document_chunks`) and ChromaDB vector store.
- **Vector Search & Semantic Retrieval**:
  - ChromaDB persistent vector database configured with cosine distance space (`hnsw:space: cosine`).
  - Strict user and notebook isolation on vector metadata (`{"user_id": current_user.id, "notebook_id": notebook_id}`).
  - Dynamic dimensional handling prevents crashes between test mocks and live models.
- **RAG Conversation Pipeline**:
  - Grounded question answering strictly based on retrieved evidence.
  - **Prompt Injection Defense**: Document text is isolated inside `<EVIDENCE>` XML delimiters in the user turn; the model is instructed never to treat evidence text as instructions.
  - **Verified Source Attribution**: All source references (`chunk_id`, `document_id`, `document_name`, `page_number`, `section`, `distance`) are built from PostgreSQL database metadata — never hallucinated by the model.
  - **Context Window Management**: Multi-turn dialogue history is capped to the last 5 conversation pairs (10 turns); chunks are bounded to avoid RAM exhaustion on 8 GB local machines.
  - **Honest Fallback**: When no relevant content is retrieved, the response indicates `grounded=false` with empty sources, instructing the model to declare the absence of document evidence.
- **Authentication & Security**:
  - Argon2id password hashing via `argon2-cffi`. Never logs plaintext passwords or private document text.
  - Database-backed sessions in PostgreSQL (`user_sessions` table) with cryptographic session tokens.
  - Secure, HTTP-only session cookies (`thinkbook_session`) and double-submit CSRF protection (`thinkbook_csrf` cookie + `X-CSRF-Token` header).
  - Parameterized SQL queries and multi-tenant isolation at both database and vector-store levels.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, Tailwind CSS v4, built with Vite |
| **Backend** | Python 3.9+, FastAPI, Uvicorn |
| **Authentication** | Argon2id (`argon2-cffi`), HTTP-only cookies, Double-Submit CSRF |
| **Relational Data** | PostgreSQL (accessed directly via `psycopg3` connection pool, no ORM) |
| **Vector Store** | ChromaDB (local on-disk persistence, cosine distance) |
| **Embeddings** | `qwen3-embedding:0.6b` served via Ollama (1024 dimensions) |
| **Local LLM** | `qwen3:1.7b` served via Ollama |

---

## API Endpoints

All endpoints are also available with the `/api` prefix (e.g. `/api/chat/rag`).

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/auth/register` | Register new account and establish session | No |
| `POST` | `/auth/login` | Authenticate with email/password and establish session | No |
| `POST` | `/auth/logout` | Invalidate active session and clear cookies | Yes |
| `GET` | `/auth/me` | Retrieve profile and CSRF token for current session | Yes |
| `GET` | `/notebooks` | List all notebooks owned by the authenticated user | Yes |
| `POST` | `/notebooks` | Create a new notebook for the authenticated user | Yes |
| `GET` | `/notebooks/{id}` | Get specific notebook (404 if not owned by user) | Yes |
| `DELETE` | `/notebooks/{id}` | Delete notebook, its documents, and vectors | Yes |
| `GET` | `/notebooks/{id}/documents` | List documents in a notebook owned by user | Yes |
| `POST` | `/notebooks/{id}/documents` | Upload and index document in user's notebook | Yes |
| `GET` | `/documents/{id}` | Get document metadata (404 if not owned by user) | Yes |
| `DELETE` | `/documents/{id}` | Delete document, chunks, physical file, and vectors | Yes |
| `POST` | `/documents/{id}/reindex` | Re-trigger embedding and indexing for user document | Yes |
| `POST` | `/retrieve` | Semantic search over chunks scoped to user's notebook | Yes |
| `POST` | `/chat` | Direct conversation with local Qwen3 1.7B LLM | Yes |
| `POST` | `/chat/rag` | Grounded RAG conversation with verified sources | Yes |
| `GET` | `/health` / `/health/services` | Service liveness and connectivity status | No |

---

## Local Setup

### Prerequisites

- Python 3.9+
- Node.js 18+
- PostgreSQL running locally (database `thinkbook_lm`, user `thinkbook`, password `thinkbook`)
- [Ollama](https://ollama.com) installed and running:
  ```bash
  ollama serve
  ```
- Pull the required local models:
  ```bash
  ollama pull qwen3:1.7b
  ollama pull qwen3-embedding:0.6b
  ```

### 1. Backend Setup

```bash
cd backend

# Create & activate virtualenv
python -m venv venv
.\venv\Scripts\activate          # Windows (PowerShell/CMD)
# source venv/bin/activate       # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env           # Windows
# cp .env.example .env           # macOS/Linux

# Run database migrations
python -m scripts.migrate

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://127.0.0.1:8000`. Swagger documentation is accessible at `http://127.0.0.1:8000/docs`.

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```

The app will run at `http://localhost:5173`. In development, Vite proxies `/api/*` directly to `http://localhost:8000`.

---

## Testing & Verification

From the `backend/` directory with the virtualenv active:

### 1. Deterministic Automated Tests (Mocked Ollama)

Runs all unit tests, authentication tests, security checks, and deterministic pipeline tests without needing live Ollama models:

```bash
python -m pytest -m "not integration"
```

### 2. Full Test Suite (Including Live Integration Tests)

Runs the complete automated suite (116 tests), including live tests that invoke real Qwen3 1.7B and Qwen3 Embedding 0.6B via local Ollama:

```bash
python -m pytest
```

### 3. Live Pipeline Smoke Test

Runs an end-to-end verification script testing health, registration, notebook creation, document ingestion, semantic search, grounded RAG answering, multi-turn follow-ups, and user isolation:

```bash
# In-process smoke test:
python -m scripts.smoke_test

# Or against an active uvicorn server:
python -m scripts.smoke_test --url http://127.0.0.1:8000
```

---

## Configuration Reference

Key variables configured in `.env`:

| Variable | Default | Purpose |
|---|---|---|
| `APP_ENV` | `development` | `development` or `production` |
| `POSTGRES_DSN` | `postgresql://thinkbook:thinkbook@localhost:5432/thinkbook_lm` | PostgreSQL connection string |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | URL of local Ollama instance |
| `OLLAMA_MODEL` | `qwen3:1.7b` | LLM generation model |
| `EMBEDDING_MODEL` | `qwen3-embedding:0.6b` | Text embedding model |
| `EMBEDDING_BATCH_SIZE` | `16` | Batch size for embedding calls (tuned for 8 GB RAM) |
| `CHROMA_PERSIST_DIR` | `./data/chroma` | On-disk path for ChromaDB vector store |
| `DOCUMENT_STORAGE_DIR` | `./data/documents` | Storage folder for uploaded source documents |
| `MAX_UPLOAD_SIZE_MB` | `25` | Maximum upload size per file |
| `ALLOWED_FILE_TYPES` | `pdf,docx,txt` | Permitted file extensions |
| `CHUNK_SIZE_CHARS` | `1200` | Chunk size in characters |
| `CHUNK_OVERLAP_CHARS` | `200` | Overlap between chunks |
| `RETRIEVAL_TOP_K` | `5` | Default number of retrieved chunks |

---

## Known Limitations & Design Notes

1. **Stateless Conversation History**: RAG conversation history is passed in the request body from the client (`history: list[RAGMessage]`). Conversation session persistence in PostgreSQL tables is deferred to Part 2.
2. **Local Inference Latency**: Inference speed is governed by local CPU/GPU hardware. On CPU-only machines, generation with `qwen3:1.7b` typically requires 5–15 seconds per turn.
3. **Chunking Strategy**: Chunking is currently character-based with sliding window overlap. Page numbers are captured for PDFs and section headings for DOCX files.
4. **Context Window Bounds**: History is capped at the 5 most recent turn pairs (10 messages) and retrieved evidence is capped at 6,000 characters to prevent out-of-memory errors on machines with 8 GB RAM.
