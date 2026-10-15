-- Milestone 3: Complete Authentication & Data Isolation.
--
-- Adds:
--   1. `users` table: accounts with Argon2-hashed passwords and normalized emails.
--   2. `user_sessions` table: database-backed sessions with expiration and CSRF protection.
--   3. `user_id` foreign key on `notebooks` (nullable to safely preserve pre-existing legacy data).
--   4. `user_id` foreign key on `documents` (nullable to safely preserve pre-existing legacy data).
--
-- Do NOT wrap in BEGIN/COMMIT -- scripts/migrate.py applies each file inside
-- its own transaction.

CREATE TABLE users (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    full_name     TEXT NOT NULL CHECK (btrim(full_name) <> ''),
    email         TEXT NOT NULL UNIQUE CHECK (btrim(email) <> ''),
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_users_email ON users(email);

CREATE TABLE user_sessions (
    id          TEXT PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    csrf_token  TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_expires_at ON user_sessions(expires_at);

-- Add user ownership to notebooks
ALTER TABLE notebooks
    ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;

CREATE INDEX idx_notebooks_user_id ON notebooks(user_id);

-- Add user ownership to documents
ALTER TABLE documents
    ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;

CREATE INDEX idx_documents_user_id ON documents(user_id);
