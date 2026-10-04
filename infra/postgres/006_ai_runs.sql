-- Durable admin AI runs; apply after 001_indexing.sql through 005 migrations.
CREATE TABLE IF NOT EXISTS application.ai_runs (
    id uuid PRIMARY KEY,
    owner_id text NOT NULL,
    idempotency_key text NOT NULL,
    fingerprint char(64) NOT NULL,
    request jsonb NOT NULL,
    status text NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','running','completed','failed','cancelled')),
    stage text,
    sequence bigint NOT NULL DEFAULT 0,
    result jsonb,
    error_code text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    UNIQUE(owner_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS ai_runs_owner_status_time ON application.ai_runs(owner_id, status, created_at DESC);
CREATE TABLE IF NOT EXISTS application.ai_events (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES application.ai_runs(id) ON DELETE CASCADE,
    sequence bigint NOT NULL,
    operation_id text NOT NULL,
    kind text NOT NULL,
    stage text,
    duration_ms double precision,
    code text,
    payload jsonb NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(run_id, sequence),
    UNIQUE(run_id, operation_id)
);
CREATE INDEX IF NOT EXISTS ai_events_time ON application.ai_events(created_at);
CREATE TABLE IF NOT EXISTS application.ai_artifacts (
    run_id uuid NOT NULL REFERENCES application.ai_runs(id) ON DELETE CASCADE,
    kind text NOT NULL,
    data jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(run_id, kind)
);
CREATE TABLE IF NOT EXISTS application.ai_usage (
    run_id uuid NOT NULL REFERENCES application.ai_runs(id) ON DELETE CASCADE,
    operation_id text NOT NULL,
    input_tokens integer NOT NULL CHECK(input_tokens >= 0),
    output_tokens integer NOT NULL CHECK(output_tokens >= 0),
    estimated_cost_usd numeric(16,8) NOT NULL CHECK(estimated_cost_usd >= 0),
    pricing_date date,
    PRIMARY KEY(run_id, operation_id)
);
ALTER TABLE application.outbox ALTER COLUMN job_id DROP NOT NULL;
ALTER TABLE application.outbox ADD COLUMN IF NOT EXISTS run_id uuid REFERENCES application.ai_runs(id) ON DELETE CASCADE;
ALTER TABLE application.outbox DROP CONSTRAINT IF EXISTS outbox_one_subject;
ALTER TABLE application.outbox ADD CONSTRAINT outbox_one_subject CHECK ((job_id IS NULL) <> (run_id IS NULL));
CREATE INDEX IF NOT EXISTS outbox_run_id ON application.outbox(run_id) WHERE run_id IS NOT NULL;
GRANT SELECT, INSERT, UPDATE, DELETE ON application.ai_runs, application.ai_events,
    application.ai_artifacts, application.ai_usage TO sum_backend_access;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA application TO sum_backend_access;
CREATE OR REPLACE VIEW institutional.published_chunks AS
SELECT c.*, e.model, e.revision, e.dimension, e.embedding,
       g.document_id, g.version_id, g.profile AS embedding_profile,
       g.metadata AS publication_metadata
FROM institutional.chunks c
JOIN institutional.generations g ON g.id = c.generation_id AND g.ready
JOIN institutional.embeddings e ON e.chunk_id = c.id
JOIN application.publications p ON p.generation_id = g.id
    AND p.document_id = g.document_id AND p.version_id = g.version_id;
GRANT SELECT ON institutional.published_chunks TO sum_retrieval_access;
