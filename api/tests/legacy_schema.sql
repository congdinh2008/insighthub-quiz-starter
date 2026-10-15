CREATE TABLE embedding_index (
    singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (singleton),
    identity_id TEXT NOT NULL UNIQUE,
    identity JSONB NOT NULL,
    dimension INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','ready','failed')),
    chunk_count INTEGER NOT NULL DEFAULT 0,
    content_sha256 TEXT,
    pipeline_id TEXT,
    embedding_identity_id TEXT REFERENCES embedding_index(identity_id),
    error_code TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(id,embedding_identity_id)
);
CREATE TABLE chunks (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding VECTOR(1024) NOT NULL,
    embedding_identity_id TEXT NOT NULL REFERENCES embedding_index(identity_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(document_id,chunk_index),
    FOREIGN KEY(document_id,embedding_identity_id) REFERENCES documents(id,embedding_identity_id) ON DELETE CASCADE
);
