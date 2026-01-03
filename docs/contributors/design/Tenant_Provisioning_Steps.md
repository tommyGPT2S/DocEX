# Tenant Provisioning Process - Detailed Steps

## Overview

The tenant provisioning process in DocEX 3.0 is explicit and deterministic. Each tenant must be provisioned before use, with no lazy creation.

## Provisioning Steps

When `TenantProvisioner.create()` is called, the following steps are executed in order:

### Step 1: Create Isolation Boundary

**Purpose:** Create the physical/logical isolation boundary for the tenant.

**For PostgreSQL (schema-per-tenant):**
- Creates a new schema: `CREATE SCHEMA IF NOT EXISTS "tenant_{tenant_id}"`
- Schema name follows template: `tenant_{tenant_id}` (configurable)

**For SQLite (database-per-tenant):**
- Creates a new database file: `storage/tenant_{tenant_id}/docex.db`
- Ensures parent directory exists
- Sets file permissions (644)

**Validation:**
- Schema/database creation is verified
- Errors are caught and reported

---

### Step 2: Initialize Schema (Create Tables)

**Purpose:** Create all required database tables in the tenant's schema/database.

**Actions:**
- Sets schema on all SQLAlchemy Base tables (for PostgreSQL)
- Creates all tables using `Base.metadata.create_all(engine)`
- Creates TransportBase tables if available
- Creates all required tables:
  - `docbasket`
  - `document`
  - `document_metadata`
  - `file_history`
  - `operations`
  - `operation_dependencies`
  - `doc_events`
  - `processors`
  - `processing_operations`
  - `transport_routes` (if transport module available)
  - `route_operations` (if transport module available)

**Validation:**
- Table creation is verified
- Missing tables are logged as warnings

---

### Step 3: Create Performance Indexes

**Purpose:** Create performance indexes for optimal query performance.

**Actions:**
- Reads index definitions from `schema.sql`
- Extracts `CREATE INDEX` statements
- Creates indexes in tenant schema/database
- Handles index creation errors gracefully (non-blocking)

**Indexes Created:**
- `idx_documents_basket_id`
- `idx_documents_document_type`
- `idx_documents_status`
- `idx_documents_related_po`
- `idx_file_history_document_id`
- `idx_operations_document_id`
- `idx_operations_operation_type`
- `idx_operations_status`
- `idx_operation_dependencies_operation_id`
- `idx_operation_dependencies_depends_on`
- `idx_doc_events_basket_id`
- `idx_doc_events_event_type`
- `idx_doc_events_document_id`
- `idx_doc_events_event_timestamp`
- `idx_doc_events_status`
- `idx_document_metadata_document_id`
- `idx_document_metadata_key`
- `idx_document_metadata_type`

**Error Handling:**
- Index creation failures are logged as warnings
- Provisioning continues even if some indexes fail
- Already-existing indexes are skipped

---

### Step 4: Validate Schema

**Purpose:** Verify that the tenant schema is properly set up and ready for use.

**Checks:**
- All required tables exist
- Database connection is working
- Schema is accessible

**Validation:**
- Verifies all 9+ required tables exist
- Raises `TenantProvisioningError` if validation fails
- Logs validation results

---

### Step 5: Register Tenant in Registry

**Purpose:** Record the tenant in the tenant registry for system tracking.

**Actions:**
- Creates `TenantRegistry` entry with:
  - `tenant_id`
  - `display_name`
  - `is_system = False`
  - `isolation_strategy`
  - `schema_name` (PostgreSQL) or `database_path` (SQLite)
  - Audit fields: `created_at`, `created_by`, `last_updated_at`, `last_updated_by`
- Commits to database
- Returns `TenantRegistry` instance

**Validation:**
- Checks for duplicate tenant_id (should not happen due to Step 0 validation)
- Handles database errors

---

## Pre-Provisioning Validation

Before Step 1, the following validations occur:

1. **Tenant ID Validation:**
   - Not empty
   - Not reserved (system tenant pattern)
   - Valid format (alphanumeric, underscores, hyphens)
   - Length check (max 255 characters)

2. **Tenant Existence Check:**
   - Queries tenant registry
   - Raises `TenantExistsError` if tenant already exists

3. **Isolation Strategy Determination:**
   - Auto-detects based on database type if not provided
   - Validates strategy is 'schema' or 'database'

---

## Error Handling & Cleanup

If provisioning fails at any step:

1. **Partial Cleanup:**
   - Attempts to remove tenant from registry (if Step 5 completed)
   - Does NOT delete schema/database (to avoid data loss)
   - Admin can manually clean up if needed

2. **Error Reporting:**
   - Detailed error messages
   - Step where failure occurred
   - Original exception preserved

---

## Logging

Each step logs:
- Start of step: `Step X/5: Description...`
- Completion: `✅ Step X complete: Description`
- Errors: Detailed error messages with context

Example log output:
```
INFO: Provisioning tenant: acme (strategy: schema)
INFO: Step 1/5: Creating isolation boundary for tenant 'acme'...
INFO: Created PostgreSQL schema 'tenant_acme' for tenant 'acme'
INFO: ✅ Step 1 complete: Isolation boundary created
INFO: Step 2/5: Initializing schema (creating tables) for tenant 'acme'...
INFO: Initialized schema for tenant 'acme'
INFO: ✅ Step 2 complete: Schema initialized with all tables
INFO: Step 3/5: Creating performance indexes for tenant 'acme'...
INFO: Creating 17 performance indexes in schema 'tenant_acme'
INFO: ✅ Created 17 performance indexes in schema 'tenant_acme'
INFO: ✅ Step 3 complete: Performance indexes created
INFO: Step 4/5: Validating schema for tenant 'acme'...
INFO: ✅ Step 4 complete: Schema validation passed
INFO: Step 5/5: Registering tenant 'acme' in tenant registry...
INFO: ✅ Step 5 complete: Tenant registered in registry
INFO: ✅ Successfully provisioned tenant: acme
```

---

## Idempotency

The provisioning process is **NOT idempotent** by design:
- Attempting to provision an existing tenant raises `TenantExistsError`
- This ensures explicit control and prevents accidental re-provisioning
- Use `tenant_exists()` check before provisioning if idempotency is needed

---

## Performance Considerations

- **Index Creation:** Can take time for large schemas, but is non-blocking
- **Table Creation:** Fast, uses SQLAlchemy metadata
- **Validation:** Quick, uses database inspection
- **Registry Write:** Single database transaction

---

## Future Enhancements

Potential additions to provisioning process:
- [ ] Custom initialization scripts per tenant
- [ ] Seed data insertion
- [ ] Backup creation
- [ ] Monitoring setup
- [ ] Resource quota assignment

