-- Metadata-only publication access avoids scanning all vectors to pin a corpus.
CREATE OR REPLACE VIEW institutional.published_catalog AS
SELECT g.document_id, g.version_id, g.id AS generation_id,
       g.profile AS embedding_profile, g.metadata AS publication_metadata
FROM institutional.generations g
JOIN application.publications p ON p.generation_id = g.id
    AND p.document_id = g.document_id AND p.version_id = g.version_id
WHERE g.ready;
GRANT SELECT ON institutional.published_catalog TO sum_retrieval_access, sum_backend_access;
