-- Safe to apply to an existing workspace; keeps existing documents and vectors.
ALTER TABLE application.indexing_jobs ADD COLUMN IF NOT EXISTS finished_at timestamptz;
CREATE TABLE IF NOT EXISTS application.indexing_stage_attempts (
    id uuid PRIMARY KEY,
    job_id uuid NOT NULL REFERENCES application.indexing_jobs(id) ON DELETE CASCADE,
    stage text NOT NULL CHECK (stage IN ('validando','extrayendo','fragmentando','generando_vectores','guardando','publicando')),
    started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    finished_at timestamptz,
    duration_ms double precision CHECK (duration_ms >= 0 AND duration_ms < 'Infinity'::float8),
    outcome text NOT NULL DEFAULT 'en_curso' CHECK (outcome IN ('en_curso','completado','fallido','cancelado','interrumpido')),
    CHECK ((outcome = 'en_curso') = (finished_at IS NULL))
);
CREATE INDEX IF NOT EXISTS indexing_stage_attempts_job ON application.indexing_stage_attempts(job_id,started_at,id);
GRANT SELECT, INSERT, UPDATE, DELETE ON application.indexing_stage_attempts TO sum_backend_access;
-- Only the published view is exposed, never staged generations or raw embeddings.
GRANT USAGE ON SCHEMA institutional TO sum_backend_access;
GRANT SELECT ON institutional.published_chunks TO sum_backend_access;
