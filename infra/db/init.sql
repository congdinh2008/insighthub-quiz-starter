-- InsightHub Starter v1 schema for a fresh PostgreSQL volume.
-- Existing volumes are upgraded by api/migrations at application startup.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS embedding_index (
    singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (singleton),
    identity_id TEXT NOT NULL UNIQUE,
    identity JSONB NOT NULL,
    dimension INTEGER NOT NULL CHECK (dimension > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS documents (
    id BIGSERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    mime_type TEXT,
    size_bytes BIGINT CHECK (size_bytes IS NULL OR size_bytes >= 0),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'ready', 'failed')),
    chunk_count INTEGER NOT NULL DEFAULT 0 CHECK (chunk_count >= 0),
    content_sha256 TEXT,
    pipeline_id TEXT,
    embedding_identity_id TEXT REFERENCES embedding_index(identity_id),
    error_code TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (id, embedding_identity_id),
    CHECK (status <> 'ready' OR
        (chunk_count > 0 AND content_sha256 IS NOT NULL AND pipeline_id IS NOT NULL
         AND embedding_identity_id IS NOT NULL AND error_code IS NULL)),
    CHECK (status = 'ready' OR chunk_count = 0)
);

CREATE TABLE IF NOT EXISTS document_sources (
    document_id BIGINT PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
    original_bytes BYTEA NOT NULL,
    extracted_text TEXT,
    extraction_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_version INTEGER NOT NULL DEFAULT 1 CHECK (source_version > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS source_segments (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    segment_index INTEGER NOT NULL CHECK (segment_index >= 0),
    locator_type TEXT NOT NULL CHECK (locator_type IN ('page', 'section', 'paragraph')),
    locator_value TEXT NOT NULL,
    heading TEXT,
    segment_text TEXT NOT NULL CHECK (length(segment_text) > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (document_id, segment_index)
);

-- EMBEDDING_DIM must match VECTOR(1024). Changing it requires a controlled rebuild.
CREATE TABLE IF NOT EXISTS chunks (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    source_segment_id BIGINT REFERENCES source_segments(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    chunk_text TEXT NOT NULL CHECK (length(chunk_text) > 0),
    locator_type TEXT,
    locator_value TEXT,
    embedding VECTOR(1024) NOT NULL,
    embedding_identity_id TEXT NOT NULL REFERENCES embedding_index(identity_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (document_id, chunk_index),
    FOREIGN KEY (document_id, embedding_identity_id)
        REFERENCES documents(id, embedding_identity_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ingestion_attempts (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    previous_attempt_id BIGINT REFERENCES ingestion_attempts(id),
    operation_key TEXT NOT NULL,
    request_fingerprint TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('processing', 'succeeded', 'failed')),
    error_code TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    deadline_at TIMESTAMPTZ NOT NULL,
    UNIQUE (document_id, operation_key)
);

CREATE TABLE IF NOT EXISTS operation_records (
    id BIGSERIAL PRIMARY KEY,
    operation_type TEXT NOT NULL CHECK (operation_type IN ('upload', 'retry', 'chat', 'delete')),
    operation_key TEXT NOT NULL,
    request_fingerprint TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('processing', 'succeeded', 'failed')),
    http_status INTEGER,
    response_body JSONB,
    error_code TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT now() + interval '24 hours',
    UNIQUE (operation_type, operation_key)
);

CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw_idx
    ON chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS documents_status_idx ON documents(status);
CREATE INDEX IF NOT EXISTS documents_sha256_idx ON documents(content_sha256);
CREATE INDEX IF NOT EXISTS source_segments_document_idx ON source_segments(document_id);
CREATE INDEX IF NOT EXISTS ingestion_attempts_document_idx ON ingestion_attempts(document_id, started_at DESC);
CREATE INDEX IF NOT EXISTS operation_records_expiry_idx ON operation_records(expires_at);

INSERT INTO schema_migrations(version) VALUES ('001_starter_v1')
ON CONFLICT (version) DO NOTHING;
