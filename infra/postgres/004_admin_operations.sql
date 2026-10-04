ALTER TABLE application.document_versions
  ADD COLUMN IF NOT EXISTS embedding_profile jsonb NOT NULL DEFAULT '{"model":"intfloat/multilingual-e5-base","revision":"d13f1b27baf31030b7fd040960d60d909913633f","dimension":768,"max_tokens":512,"passage_prefix":"passage: ","query_prefix":"query: ","normalized":true}'::jsonb;

-- Reindexing references the existing original rather than uploading another copy.
ALTER TABLE application.document_versions
  DROP CONSTRAINT IF EXISTS document_versions_object_key_key;
CREATE INDEX IF NOT EXISTS document_versions_object_key
  ON application.document_versions(object_key);

UPDATE application.document_versions v
SET embedding_profile = p.manifest->'profile'
FROM application.publications p
WHERE p.version_id=v.id AND p.manifest ? 'profile';

CREATE TABLE IF NOT EXISTS application.embedding_configuration (
  singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
  profile jsonb NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO application.embedding_configuration(singleton, profile)
VALUES (true, '{"provider":"tei","model":"intfloat/multilingual-e5-base","revision":"d13f1b27baf31030b7fd040960d60d909913633f","dimension":768,"max_tokens":512}')
ON CONFLICT (singleton) DO NOTHING;
GRANT SELECT, INSERT, UPDATE ON application.embedding_configuration TO sum_backend_access;
