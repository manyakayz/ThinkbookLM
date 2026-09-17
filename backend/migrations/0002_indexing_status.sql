-- Milestone 2: Add indexing_status and indexing_error to documents.
--
-- Separates text-extraction state (processing_status) from vector-indexing
-- state (indexing_status) so failures in each phase are clearly attributed.
-- A document with processing_status='completed' but indexing_status='failed'
-- has its text in PostgreSQL but is NOT retrieval-ready.
--
-- Do NOT wrap in BEGIN/COMMIT -- scripts/migrate.py applies each file inside
-- its own transaction.

ALTER TABLE documents
    ADD COLUMN indexing_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (indexing_status IN ('pending', 'indexing', 'indexed', 'failed')),
    ADD COLUMN indexing_error  TEXT;

-- Documents that were marked completed before this migration exist with
-- processing_status='completed' but have never been indexed. Leave them
-- as indexing_status='pending' (the default) so the re-index endpoint can
-- pick them up.
