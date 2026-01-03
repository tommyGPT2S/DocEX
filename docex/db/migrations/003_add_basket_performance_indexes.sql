-- Migration: Add performance indexes for basket queries
-- This migration adds indexes to optimize:
-- 1. Basket filtering by status
-- 2. Basket sorting by created_at
-- 3. Document metadata queries with document_id

BEGIN;

-- Index for basket status filtering
-- Improves list_baskets with status filter
CREATE INDEX IF NOT EXISTS idx_docbasket_status 
ON docbasket(status);

-- Index for basket sorting by created_at
-- Improves list_baskets with sorting by created_at
CREATE INDEX IF NOT EXISTS idx_docbasket_created_at 
ON docbasket(created_at DESC);

-- Composite index for document metadata queries
-- Improves find_documents_by_metadata with document_id joins
CREATE INDEX IF NOT EXISTS idx_document_metadata_doc_key_value 
ON document_metadata(document_id, key, value);

COMMIT;

