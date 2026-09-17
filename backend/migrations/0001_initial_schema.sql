-- Milestone 1: notebooks, documents, chunks.
--
-- No ORM is used in this project (see backend/app/services/db.py), so
-- migrations are plain SQL files applied in order by scripts/migrate.py.
-- Naming convention: NNNN_description.sql, applied in filename order.
--
-- Do NOT wrap this file's statements in BEGIN/COMMIT -- scripts/migrate.py
-- already applies the whole file inside one transaction.

CREATE TABLE notebooks (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        TEXT NOT NULL CHECK (btrim(name) <> ''),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE documents (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    notebook_id         INTEGER NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,

    -- What the user uploaded, preserved purely as display metadata.
    original_filename   TEXT NOT NULL,
    -- The actual filename on disk under DOCUMENT_STORAGE_DIR: a generated,
    -- collision-free, path-traversal-safe identifier. Never derived from
    -- user input. See app/services/storage.py.
    stored_filename      TEXT NOT NULL UNIQUE,

    file_type           TEXT NOT NULL CHECK (file_type IN ('pdf', 'docx', 'txt')),
    file_size            BIGINT NOT NULL CHECK (file_size >= 0),
    page_count           INTEGER CHECK (page_count IS NULL OR page_count >= 0),

    processing_status    TEXT NOT NULL DEFAULT 'pending'
                          CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    error_message         TEXT,

    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_documents_notebook_id ON documents(notebook_id);

CREATE TABLE chunks (
    id             INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id     INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    chunk_index      INTEGER NOT NULL CHECK (chunk_index >= 0),
    text             TEXT NOT NULL CHECK (btrim(text) <> ''),

    -- Provenance metadata -- what a future citation ("Document X, page 7")
    -- needs. All nullable: not every source format has every field
    -- (e.g. TXT has no page_number, PDF has no section).
    page_number      INTEGER CHECK (page_number IS NULL OR page_number >= 1),
    section          TEXT,
    char_start        INTEGER CHECK (char_start IS NULL OR char_start >= 0),
    char_end          INTEGER CHECK (char_end IS NULL OR char_end >= char_start),

    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (document_id, chunk_index)
);

CREATE INDEX idx_chunks_document_id ON chunks(document_id);

