CREATE TABLE IF NOT EXISTS application.ai_rejection_buckets (
    hour timestamptz NOT NULL,
    owner_id text NOT NULL,
    provider text NOT NULL,
    model text NOT NULL,
    count bigint NOT NULL DEFAULT 0 CHECK(count >= 0),
    PRIMARY KEY(hour,owner_id,provider,model)
);
CREATE INDEX IF NOT EXISTS ai_rejection_buckets_owner_time ON application.ai_rejection_buckets(owner_id,hour);
GRANT SELECT, INSERT, UPDATE, DELETE ON application.ai_rejection_buckets TO sum_backend_access;
