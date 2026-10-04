-- Storage deletions are retried after a successful database transaction.
CREATE TABLE IF NOT EXISTS application.object_deletions (
    object_key text PRIMARY KEY,
    document_id uuid NOT NULL,
    kind text NOT NULL CHECK (kind IN ('object','prefix')),
    created_at timestamptz NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, DELETE ON application.object_deletions TO sum_backend_access;

CREATE OR REPLACE FUNCTION institutional.delete_document_generations(p_document_id uuid)
RETURNS SETOF uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, institutional
AS $$
DECLARE
    generation_ids uuid[];
BEGIN
    SELECT array_agg(id) INTO generation_ids
    FROM application.indexing_jobs
    WHERE document_id = p_document_id;

    IF generation_ids IS NULL THEN
        RETURN;
    END IF;

    DELETE FROM institutional.outcomes WHERE job_id = ANY(generation_ids);
    DELETE FROM institutional.embeddings
    WHERE chunk_id IN (
        SELECT id FROM institutional.chunks WHERE generation_id = ANY(generation_ids)
    );
    DELETE FROM institutional.chunks WHERE generation_id = ANY(generation_ids);
    DELETE FROM institutional.generations WHERE id = ANY(generation_ids);
    RETURN QUERY SELECT unnest(generation_ids);
END;
$$;

REVOKE ALL ON FUNCTION institutional.delete_document_generations(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION institutional.delete_document_generations(uuid)
TO sum_backend_access;
