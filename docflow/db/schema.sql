-- BEGIN POSTGRES-SPECIFIC
-- Create schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS docflow;

-- Set search path
SET search_path TO docflow;
-- END POSTGRES-SPECIFIC

-- Drop existing tables (in reverse dependency order)
DROP TABLE IF EXISTS operation_dependencies;
DROP TABLE IF EXISTS operations;
DROP TABLE IF EXISTS file_history;
DROP TABLE IF EXISTS document_metadata;
DROP TABLE IF EXISTS doc_events;
DROP TABLE IF EXISTS documents;
DROP TABLE IF EXISTS docbasket;

-- Create docbasket table
CREATE TABLE IF NOT EXISTS docbasket (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    config JSON,  -- SQLite will store as TEXT, handled by SQLAlchemy
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create documents table
CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(36) PRIMARY KEY,
    basket_id VARCHAR(36) NOT NULL REFERENCES docbasket(id) ON DELETE CASCADE,
    document_type VARCHAR(50) NOT NULL,
    source VARCHAR(255) NOT NULL,
    content JSON,  -- SQLite will store as TEXT, handled by SQLAlchemy
    raw_content TEXT,
    related_po VARCHAR(50),
    checksum VARCHAR(64),
    status VARCHAR(50) NOT NULL DEFAULT 'RECEIVED',
    processing_attempts INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create file_history table
CREATE TABLE IF NOT EXISTS file_history (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    original_path VARCHAR(255) NOT NULL,
    internal_path VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create operations table
CREATE TABLE IF NOT EXISTS operations (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    operation_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    details JSON,  -- SQLite will store as TEXT, handled by SQLAlchemy
    error TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Create operation_dependencies table
CREATE TABLE IF NOT EXISTS operation_dependencies (
    id VARCHAR(36) PRIMARY KEY,
    operation_id VARCHAR(36) NOT NULL REFERENCES operations(id) ON DELETE CASCADE,
    depends_on VARCHAR(36) NOT NULL REFERENCES operations(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(operation_id, depends_on)
);

-- Create doc_events table
CREATE TABLE IF NOT EXISTS doc_events (
    id VARCHAR(36) PRIMARY KEY,
    basket_id VARCHAR(36) NOT NULL REFERENCES docbasket(id) ON DELETE CASCADE,
    document_id VARCHAR(36) REFERENCES documents(id) ON DELETE NO ACTION,
    event_type VARCHAR(50) NOT NULL,
    event_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data JSON,  -- SQLite will store as TEXT, handled by SQLAlchemy
    source VARCHAR(50) NOT NULL DEFAULT 'docflow',
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create document_metadata table
CREATE TABLE IF NOT EXISTS document_metadata (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    key VARCHAR(100) NOT NULL,
    value JSON NOT NULL,  -- SQLite will store as TEXT, handled by SQLAlchemy
    metadata_type VARCHAR(50) NOT NULL DEFAULT 'custom',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, key)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_documents_basket_id ON documents(basket_id);
CREATE INDEX IF NOT EXISTS idx_documents_document_type ON documents(document_type);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_related_po ON documents(related_po);
CREATE INDEX IF NOT EXISTS idx_file_history_document_id ON file_history(document_id);
CREATE INDEX IF NOT EXISTS idx_operations_document_id ON operations(document_id);
CREATE INDEX IF NOT EXISTS idx_operations_operation_type ON operations(operation_type);
CREATE INDEX IF NOT EXISTS idx_operations_status ON operations(status);
CREATE INDEX IF NOT EXISTS idx_operation_dependencies_operation_id ON operation_dependencies(operation_id);
CREATE INDEX IF NOT EXISTS idx_operation_dependencies_depends_on ON operation_dependencies(depends_on);
CREATE INDEX IF NOT EXISTS idx_doc_events_basket_id ON doc_events(basket_id);
CREATE INDEX IF NOT EXISTS idx_doc_events_event_type ON doc_events(event_type);
CREATE INDEX IF NOT EXISTS idx_doc_events_document_id ON doc_events(document_id);
CREATE INDEX IF NOT EXISTS idx_doc_events_event_timestamp ON doc_events(event_timestamp);
CREATE INDEX IF NOT EXISTS idx_doc_events_status ON doc_events(status);
CREATE INDEX IF NOT EXISTS idx_document_metadata_document_id ON document_metadata(document_id);
CREATE INDEX IF NOT EXISTS idx_document_metadata_key ON document_metadata(key);
CREATE INDEX IF NOT EXISTS idx_document_metadata_type ON document_metadata(metadata_type); 