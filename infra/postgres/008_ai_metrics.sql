CREATE TABLE IF NOT EXISTS application.ai_evaluations (
    id uuid PRIMARY KEY,
    owner_id text NOT NULL,
    idempotency_key text NOT NULL,
    fingerprint text NOT NULL,
    dataset_id text NOT NULL,
    dataset_version text NOT NULL,
    provider text NOT NULL,
    model text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(owner_id, idempotency_key)
);
ALTER TABLE application.ai_runs ADD COLUMN IF NOT EXISTS evaluation_context jsonb;
ALTER TABLE application.ai_runs ADD COLUMN IF NOT EXISTS evaluation_id uuid REFERENCES application.ai_evaluations(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS ai_runs_evaluation ON application.ai_runs(evaluation_id) WHERE evaluation_id IS NOT NULL;
CREATE TABLE IF NOT EXISTS application.ai_metric_runs (
    run_id uuid PRIMARY KEY REFERENCES application.ai_runs(id) ON DELETE CASCADE,
    projected_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS application.ai_metric_buckets (
    hour timestamptz NOT NULL,
    owner_id text NOT NULL,
    provider text NOT NULL,
    model text NOT NULL,
    status text NOT NULL,
    corpus_key text NOT NULL,
    generation_ids jsonb NOT NULL,
    traffic text NOT NULL CHECK(traffic IN ('interactive','evaluation')),
    stage text NOT NULL,
    data jsonb NOT NULL,
    PRIMARY KEY(hour,owner_id,provider,model,status,corpus_key,traffic,stage)
);
CREATE INDEX IF NOT EXISTS ai_metric_buckets_owner_time ON application.ai_metric_buckets(owner_id,hour);
CREATE INDEX IF NOT EXISTS ai_metric_buckets_generations ON application.ai_metric_buckets USING gin(generation_ids);
GRANT SELECT, INSERT, UPDATE, DELETE ON application.ai_evaluations, application.ai_metric_runs,
    application.ai_metric_buckets TO sum_backend_access;
