# ThinkBook LM

A fully local, AI-powered research and learning assistant inspired by Google's NotebookLM. Users organize documents into notebooks, retrieve information using semantic search and local embeddings, and interact through a grounded workspace with studio learning tools.

Everything runs locally: no cloud LLM or paid embedding APIs required.

---

## Current Status

**Milestone 3: Complete Authentication & User Data Isolation.**
- **Authentication**: Complete email/password authentication system featuring user registration, login, logout, and session restoration.
  - **Password Security**: Argon2id password hashing via `argon2-cffi`. Never logs or stores plaintext passwords.
  - **Session Management**: Database-backed sessions in PostgreSQL (`user_sessions` table) with cryptographic session tokens.
  - **Cookie-Based Security**: Secure, HTTP-only cookies (`thinkbook_session`) prevent client-side script token theft; frontend state never stores passwords or session secrets in `localStorage` or `sessionStorage`.
  - **CSRF Protection**: Synchronizer token protection (`thinkbook_csrf` cookie + `X-CSRF-Token` header) for all state-changing requests.
  - **Rate Limiting**: Defends against brute-force login attacks with sliding window attempt tracking and generic 401 error responses that prevent account enumeration.
- **User Data Isolation**:
  - **PostgreSQL Scoping**: Notebooks and documents are strictly bound to their creator via `user_id` foreign keys and parameterized SQL queries. A user cannot view, list, or manipulate another user's notebooks or sources.
  - **ChromaDB Isolation**: Every vector chunk is indexed with `user_id` in its ChromaDB metadata. Semantic search queries strictly filter by `{"user_id": current_user.id}`, guaranteeing complete cross-user vector store isolation.
  - **Legacy Data Preservation**: Pre-authentication data is safely preserved with nullable `user_id` columns and can be claimed with the provided migration utility (`scripts/claim_legacy_data.py`).
- **Frontend Experience**:
  - Polished dark-mode **Login** and **Sign up** pages matching ThinkbookLM's NotebookLM aesthetics.
  - Real-time password requirement checklist and confirmation validation.
  - Seamless session persistence on browser reload via `GET /api/auth/me`.
  - Protected routing that displays a dark loading state during verification, preventing private workspace content flashing.
  - User avatar with initials and an interactive profile dropdown with user info and a working logout action.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, Tailwind CSS v4, built with Vite |
| **Backend** | Python 3.9+, FastAPI, Uvicorn |
| **Authentication** | Argon2id (`argon2-cffi`), HTTP-only cookies, Double-Submit CSRF |
| **Relational Data** | PostgreSQL (accessed directly via `psycopg3` connection pool, no ORM) |
| **Vector Store** | ChromaDB (local on-disk persistence) |
| **Embeddings** | `qwen3-embedding:0.6b` served via Ollama |
| **Local LLM** | `qwen3:1.7b` served via Ollama |

---

## Authentication & API Endpoints

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/auth/register` | Register new account and establish session | No |
| `POST` | `/api/auth/login` | Authenticate with email/password and establish session | No |
| `POST` | `/api/auth/logout` | Invalidate active session and clear cookies | Yes |
| `GET` | `/api/auth/me` | Retrieve profile and CSRF token for current session | Yes |
| `GET` | `/api/notebooks` | List all notebooks owned by the authenticated user | Yes |
| `POST` | `/api/notebooks` | Create a new notebook for the authenticated user | Yes |
| `GET` | `/api/notebooks/{id}` | Get specific notebook (404 if not owned by user) | Yes |
| `GET` | `/api/notebooks/{id}/documents` | List documents in a notebook owned by user | Yes |
| `POST` | `/api/notebooks/{id}/documents` | Upload and index document in user's notebook | Yes |
| `GET` | `/api/documents/{id}` | Get document metadata (404 if not owned by user) | Yes |
| `POST` | `/api/retrieve` | Semantic search scoped to user's notebook | Yes |
| `POST` | `/api/documents/{id}/reindex` | Re-trigger embedding for user's document | Yes |
| `GET` | `/health` / `/health/services` | Service liveness and connectivity status | No |

---

## Local Setup

### Prerequisites

- Python 3.9+
- Node.js 18+
- PostgreSQL running locally (database `thinkbook_lm`, user `thinkbook`, password `thinkbook`)
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
.\venv\Scripts\activate          # Windows (PowerShell/CMD)
# source venv/bin/activate       # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env           # Windows
# cp .env.example .env           # macOS/Linux

# Run database migrations (0001, 0002, and 0003_authentication)
python -m scripts.migrate

# (Optional) Check or claim pre-existing legacy data
python -m scripts.claim_legacy_data --status
# python -m scripts.claim_legacy_data --email your_registered_email@example.com

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

## Running Tests

From the `backend/` directory with virtualenv active:

```bash
# Run unit tests, authentication tests, and data isolation tests
python -m pytest -m "not integration"

# Run tests including integration tests calling live Ollama:
python -m pytest
```

To build and validate the frontend production bundle:

```bash
cd frontend
npm run build
npm run lint
```
