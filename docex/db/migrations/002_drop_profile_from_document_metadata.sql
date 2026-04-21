BEGIN;

DO $$
DECLARE
    schema_row RECORD;
BEGIN
    FOR schema_row IN
        SELECT DISTINCT table_schema
        FROM information_schema.columns
        WHERE table_name = 'document_metadata'
          AND column_name = 'profile'
    LOOP
        EXECUTE format(
            'ALTER TABLE %I.document_metadata DROP COLUMN IF EXISTS profile',
            schema_row.table_schema
        );
    END LOOP;
END $$;

COMMIT;
