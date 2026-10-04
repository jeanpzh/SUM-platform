CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS application;
CREATE SCHEMA IF NOT EXISTS institutional;

CREATE TABLE application.documents (
    id uuid PRIMARY KEY,
    owner_id text NOT NULL,
    current_version_id uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE application.document_versions (
    id uuid PRIMARY KEY,
    document_id uuid NOT NULL REFERENCES application.documents(id),
    metadata jsonb NOT NULL,
    object_key text NOT NULL UNIQUE,
    mime_type text NOT NULL,
    sha256 text NOT NULL CHECK (length(sha256) = 64),
    size_bytes bigint NOT NULL CHECK (size_bytes > 0),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE application.indexing_jobs (
    id uuid PRIMARY KEY,
    document_id uuid NOT NULL REFERENCES application.documents(id),
    version_id uuid NOT NULL UNIQUE REFERENCES application.document_versions(id),
    owner_id text NOT NULL,
    idempotency_key text NOT NULL,
    fingerprint text NOT NULL,
    status text NOT NULL DEFAULT 'en_cola' CHECK (status IN ('en_cola','procesando','completado','fallido','cancelado')),
    stage text,
    priority integer NOT NULL,
    message text NOT NULL DEFAULT 'Documento recibido. La indexación está pendiente.',
    counts jsonb NOT NULL DEFAULT '{}',
    sequence bigint NOT NULL DEFAULT 0,
    error_code text,
    heartbeat_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (owner_id, idempotency_key)
);
CREATE INDEX indexing_jobs_owner_status ON application.indexing_jobs(owner_id, status);
CREATE TABLE application.indexing_events (
    job_id uuid NOT NULL REFERENCES application.indexing_jobs(id),
    sequence bigint NOT NULL,
    operation_id text NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (job_id, sequence),
    UNIQUE (job_id, operation_id)
);
CREATE TABLE application.outbox (
    id uuid PRIMARY KEY,
    job_id uuid NOT NULL REFERENCES application.indexing_jobs(id),
    event_name text NOT NULL,
    payload jsonb NOT NULL,
    attempts integer NOT NULL DEFAULT 0,
    available_at timestamptz NOT NULL DEFAULT now(),
    claim_token uuid,
    claimed_until timestamptz,
    delivered_at timestamptz
);
CREATE INDEX outbox_pending ON application.outbox(available_at) WHERE delivered_at IS NULL;

-- The backend owns the catalogue's visibility decision, including cancellation.
-- Indexer writes only institutional tables. This projection avoids a distributed
-- commit between publishing vectors and checking cancellation in the backend.
CREATE TABLE application.publications (
    document_id uuid PRIMARY KEY REFERENCES application.documents(id),
    version_id uuid NOT NULL REFERENCES application.document_versions(id),
    generation_id uuid NOT NULL,
    manifest jsonb NOT NULL,
    published_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE institutional.generations (
    id uuid PRIMARY KEY,
    document_id uuid NOT NULL,
    version_id uuid NOT NULL,
    profile jsonb NOT NULL,
    metadata jsonb NOT NULL,
    expected_chunks integer NOT NULL CHECK (expected_chunks > 0),
    ready boolean NOT NULL DEFAULT false,
    manifest jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE institutional.chunks (
    id uuid PRIMARY KEY,
    generation_id uuid NOT NULL REFERENCES institutional.generations(id),
    ordinal integer NOT NULL,
    page integer NOT NULL,
    locator text NOT NULL,
    content text NOT NULL,
    token_count integer NOT NULL,
    metadata jsonb NOT NULL,
    UNIQUE (generation_id, ordinal)
);
CREATE TABLE institutional.embeddings (
    chunk_id uuid PRIMARY KEY REFERENCES institutional.chunks(id),
    model text NOT NULL,
    revision text NOT NULL,
    dimension integer NOT NULL,
    embedding vector NOT NULL,
    CHECK (vector_dims(embedding) = dimension)
);
CREATE TABLE institutional.outcomes (
    job_id uuid PRIMARY KEY,
    kind text NOT NULL CHECK (kind IN ('completed','failed')),
    payload jsonb NOT NULL,
    delivered_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX outcomes_pending ON institutional.outcomes(created_at) WHERE delivered_at IS NULL;
CREATE INDEX embeddings_e5_hnsw ON institutional.embeddings
    USING hnsw ((embedding::vector(768)) vector_cosine_ops) WHERE dimension = 768;

CREATE VIEW institutional.published_chunks AS
SELECT c.*, e.model, e.revision, e.dimension, e.embedding,
       g.document_id, g.version_id
FROM institutional.chunks c
JOIN institutional.generations g ON g.id = c.generation_id AND g.ready
JOIN institutional.embeddings e ON e.chunk_id = c.id
JOIN application.publications p ON p.generation_id = g.id
    AND p.document_id = g.document_id AND p.version_id = g.version_id;

-- Login roles/passwords are provisioned by the deployment administrator.
CREATE ROLE sum_backend_access NOLOGIN;
CREATE ROLE sum_indexer_access NOLOGIN;
CREATE ROLE sum_retrieval_access NOLOGIN;
GRANT USAGE ON SCHEMA application TO sum_backend_access;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA application TO sum_backend_access;
GRANT USAGE ON SCHEMA institutional TO sum_indexer_access, sum_retrieval_access;
GRANT SELECT, INSERT, UPDATE, DELETE ON institutional.generations,
    institutional.chunks, institutional.embeddings, institutional.outcomes TO sum_indexer_access;
GRANT SELECT ON institutional.published_chunks TO sum_retrieval_access;
