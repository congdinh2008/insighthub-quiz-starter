-- Read-only database role for MCP and other AI tools (M0.2, LR-05).
-- The boundary is enforced by PostgreSQL privileges, not by the MCP server mode.
-- The role has no password and cannot log in until the learner runs `make mcp-role`.
-- Grants are explicit per table: new tables (for example Auth sessions) are NOT readable
-- unless a learner grants them on purpose and records the reason in the AI Usage Charter.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'insighthub_readonly') THEN
        CREATE ROLE insighthub_readonly NOLOGIN;
    END IF;
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO insighthub_readonly', current_database());
    EXECUTE format('GRANT USAGE ON SCHEMA %I TO insighthub_readonly', current_schema());
    GRANT SELECT ON documents, document_sources, source_segments, chunks,
        ingestion_attempts, embedding_index, schema_migrations TO insighthub_readonly;
    ALTER ROLE insighthub_readonly SET default_transaction_read_only = on;
    ALTER ROLE insighthub_readonly SET statement_timeout = '5s';
EXCEPTION
    WHEN insufficient_privilege THEN
        RAISE NOTICE 'Skip insighthub_readonly: database user cannot manage roles';
END
$$;
