-- Named connections and immutable secret-bearing revisions. Backend role only.
CREATE TABLE IF NOT EXISTS application.ai_provider_connections (
    id uuid PRIMARY KEY,
    owner_id text NOT NULL,
    revision integer NOT NULL CHECK(revision > 0),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ai_provider_connections_owner ON application.ai_provider_connections(owner_id);
CREATE TABLE IF NOT EXISTS application.ai_provider_revisions (
    config_id uuid NOT NULL REFERENCES application.ai_provider_connections(id),
    revision integer NOT NULL CHECK(revision > 0),
    config jsonb NOT NULL,
    encrypted_key text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(config_id, revision)
);
GRANT SELECT, INSERT, UPDATE ON application.ai_provider_connections TO sum_backend_access;
GRANT SELECT, INSERT ON application.ai_provider_revisions TO sum_backend_access;
