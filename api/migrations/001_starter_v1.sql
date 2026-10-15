CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS mime_type TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS size_bytes BIGINT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
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
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS source_segment_id BIGINT REFERENCES source_segments(id) ON DELETE CASCADE;
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS locator_type TEXT;
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS locator_value TEXT;
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
CREATE INDEX IF NOT EXISTS documents_sha256_idx ON documents(content_sha256);
CREATE INDEX IF NOT EXISTS source_segments_document_idx ON source_segments(document_id);
CREATE INDEX IF NOT EXISTS ingestion_attempts_document_idx ON ingestion_attempts(document_id, started_at DESC);
CREATE INDEX IF NOT EXISTS operation_records_expiry_idx ON operation_records(expires_at);
INSERT INTO schema_migrations(version) VALUES ('001_starter_v1') ON CONFLICT (version) DO NOTHING;
