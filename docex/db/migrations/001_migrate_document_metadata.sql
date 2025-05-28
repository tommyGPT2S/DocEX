-- Migration script to handle transition from old document_metadata to new schema
BEGIN;

-- Step 1: Create temporary table to store the mapping between old and new document IDs
CREATE TEMPORARY TABLE document_id_mapping (
    old_document_id VARCHAR(36),
    new_document_id VARCHAR(36),
    basket_id VARCHAR(36)
);

-- Step 2: Insert documents from old table into new documents table
INSERT INTO docex.documents (
    id,
    basket_id,
    document_type,
    status,
    source,
    related_po,
    checksum,
    content,
    raw_content,
    created_at,
    updated_at
)
SELECT 
    dm.document_id,
    -- We need to create a basket for each tenant_alias
    -- This is a temporary basket that can be updated later
    'temp_' || dm.tenant_alias,
    dm.document_type,
    dm.status,
    dm.source,
    dm.related_po,
    dm.checksum,
    dm.additional_info,
    NULL, -- raw_content will be NULL initially
    dm.created_at,
    dm.updated_at
FROM integration.document_metadata dm;

-- Step 3: Insert file history records
INSERT INTO docex.file_history (
    id,
    document_id,
    original_path,
    internal_path,
    checksum,
    created_at
)
SELECT 
    gen_random_uuid()::VARCHAR(36),
    dm.document_id,
    dm.original_file_path,
    dm.current_file_path,
    dm.checksum,
    dm.created_at
FROM integration.document_metadata dm;

-- Step 4: Create docbaskets for each tenant
INSERT INTO docex.docbasket (
    id,
    name,
    description,
    config,
    status,
    created_at,
    updated_at
)
SELECT DISTINCT
    'temp_' || tenant_alias,
    tenant_alias || ' Documents',
    'Migrated from integration schema',
    '{"tenant_alias": "' || tenant_alias || '"}',
    'active',
    MIN(created_at),
    MAX(updated_at)
FROM integration.document_metadata
GROUP BY tenant_alias;

-- Step 5: Update document basket references
UPDATE docex.documents d
SET basket_id = 'temp_' || dm.tenant_alias
FROM integration.document_metadata dm
WHERE d.id = dm.document_id;

-- Step 6: Create metadata entries for additional_info
INSERT INTO docex.document_metadata (
    document_id,
    key,
    value,
    metadata_type,
    created_at,
    updated_at
)
SELECT 
    document_id,
    'additional_info',
    additional_info,
    'system',
    created_at,
    updated_at
FROM integration.document_metadata
WHERE additional_info IS NOT NULL AND additional_info != '{}'::jsonb;

-- Step 7: Create metadata entries for file paths
INSERT INTO docex.document_metadata (
    document_id,
    key,
    value,
    metadata_type,
    created_at,
    updated_at
)
SELECT 
    document_id,
    'file_paths',
    json_build_object(
        'current', current_file_path,
        'original', original_file_path
    ),
    'system',
    created_at,
    updated_at
FROM integration.document_metadata;

-- Step 8: Verify migration
DO $$
DECLARE
    old_count INTEGER;
    new_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO old_count FROM integration.document_metadata;
    SELECT COUNT(*) INTO new_count FROM docex.documents;
    
    IF old_count != new_count THEN
        RAISE EXCEPTION 'Migration failed: Document count mismatch. Old: %, New: %', old_count, new_count;
    END IF;
END $$;

COMMIT; 