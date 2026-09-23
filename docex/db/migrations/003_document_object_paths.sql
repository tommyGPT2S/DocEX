-- Apply as owner for an explicitly selected tenant schema. S3 keys and full
-- tenant paths are not limited to the filename's 255-character maximum.
-- psql "$DATABASE_URL" -v tenant_schema=tenant_example -f 003_document_object_paths.sql
\set ON_ERROR_STOP on
\if :{?tenant_schema}
\else
\echo 'tenant_schema is required'
\quit 2
\endif
BEGIN;
ALTER TABLE :"tenant_schema".document
    ALTER COLUMN source TYPE TEXT,
    ALTER COLUMN path TYPE TEXT;
ALTER TABLE IF EXISTS :"tenant_schema".file_history
    ALTER COLUMN original_path TYPE TEXT,
    ALTER COLUMN internal_path TYPE TEXT;
COMMIT;
