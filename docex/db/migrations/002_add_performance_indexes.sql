-- Migration: Add performance indexes for document queries
-- This migration adds composite indexes to optimize:
-- 1. find_documents_by_metadata queries (metadata key/value)
-- 2. list_documents queries with filters (basket_id + status/type)
-- 3. General document lookups by basket_id with sorting

BEGIN;

-- Composite index for metadata queries: key + value
-- This dramatically improves performance for find_documents_by_metadata
-- when filtering by metadata key-value pairs
CREATE INDEX IF NOT EXISTS idx_document_metadata_key_value 
ON document_metadata(key, value);

-- Composite index for document queries with basket_id + status
-- Improves list_documents with status filter
CREATE INDEX IF NOT EXISTS idx_document_basket_status 
ON document(basket_id, status);

-- Composite index for document queries with basket_id + document_type
-- Improves list_documents with document_type filter
CREATE INDEX IF NOT EXISTS idx_document_basket_type 
ON document(basket_id, document_type);

-- Composite index for sorting: basket_id + created_at
-- Improves list_documents with sorting by created_at
CREATE INDEX IF NOT EXISTS idx_document_basket_created 
ON document(basket_id, created_at DESC);

-- Composite index for sorting: basket_id + updated_at
-- Improves list_documents with sorting by updated_at
CREATE INDEX IF NOT EXISTS idx_document_basket_updated 
ON document(basket_id, updated_at DESC);

-- Composite index for sorting: basket_id + name
-- Improves list_documents with sorting by name
CREATE INDEX IF NOT EXISTS idx_document_basket_name 
ON document(basket_id, name);

COMMIT;

