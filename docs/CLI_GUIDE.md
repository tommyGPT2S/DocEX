# DocEX CLI Guide

Complete guide to using the DocEX command-line interface.

## Overview

The DocEX CLI provides commands for managing tenants, baskets, documents, and performing operations like vector indexing.

## Commands

### Main Commands

- `init` - Initialize DocEX with configuration
- `embed` - Generate vector embeddings for documents
- `provision-tenant` - Provision a new tenant
- `basket` - Manage document baskets
- `document` - Manage documents
- `processor` - Manage document processors

## Basket Commands

### List Baskets

List all document baskets for a tenant.

```bash
# List all baskets
docex basket list --tenant-id docEX-Demo-PS

# List with JSON output
docex basket list --tenant-id docEX-Demo-PS --format json

# List with simple format (tab-separated)
docex basket list --tenant-id docEX-Demo-PS --format simple
```

**Options:**
- `--tenant-id` - Tenant ID for multi-tenant setups
- `--format` - Output format: `table` (default), `json`, or `simple`

### Create Basket

Create a new document basket.

```bash
# Create a basket
docex basket create --tenant-id docEX-Demo-PS --name "My Basket" --description "Description here"
```

**Options:**
- `--tenant-id` - Tenant ID for multi-tenant setups
- `--name` - Basket name (required)
- `--description` - Basket description

## Document Commands

### List Documents

List documents in a basket with pagination, sorting, and filtering.

```bash
# List first 20 documents
docex document list --tenant-id docEX-Demo-PS --basket-id bas_123 --limit 20

# List with pagination (page 2)
docex document list --tenant-id docEX-Demo-PS --basket-id bas_123 --limit 20 --offset 20

# List sorted by name
docex document list --tenant-id docEX-Demo-PS --basket-id bas_123 --order-by name

# List newest first
docex document list --tenant-id docEX-Demo-PS --basket-id bas_123 --order-by created_at --order-desc

# Filter by status
docex document list --tenant-id docEX-Demo-PS --basket-id bas_123 --status active

# Filter by document type
docex document list --tenant-id docEX-Demo-PS --basket-id bas_123 --document-type file

# JSON output
docex document list --tenant-id docEX-Demo-PS --basket-id bas_123 --format json
```

**Options:**
- `--tenant-id` - Tenant ID for multi-tenant setups
- `--basket-id` - Basket ID (required)
- `--limit` - Maximum number of documents to return
- `--offset` - Number of documents to skip (default: 0)
- `--order-by` - Field to sort by: `name`, `created_at`, `updated_at`, `size`, `status`
- `--order-desc` - Sort in descending order
- `--status` - Filter by document status
- `--document-type` - Filter by document type
- `--format` - Output format: `table` (default), `json`, or `simple`

### Count Documents

Count documents in a basket.

```bash
# Count all documents
docex document count --tenant-id docEX-Demo-PS --basket-id bas_123

# Count with filters
docex document count --tenant-id docEX-Demo-PS --basket-id bas_123 --status active
docex document count --tenant-id docEX-Demo-PS --basket-id bas_123 --document-type file
```

**Options:**
- `--tenant-id` - Tenant ID for multi-tenant setups
- `--basket-id` - Basket ID (required)
- `--status` - Filter by document status
- `--document-type` - Filter by document type

### Search Documents by Metadata

Search documents using metadata filters with pagination and sorting.

```bash
# Search by single metadata key
docex document search --tenant-id docEX-Demo-PS --basket-id bas_123 --metadata '{"category":"invoice"}'

# Search with multiple filters (AND logic)
docex document search --tenant-id docEX-Demo-PS --basket-id bas_123 --metadata '{"category":"invoice","author":"Alice"}'

# Search with pagination
docex document search --tenant-id docEX-Demo-PS --basket-id bas_123 --metadata '{"category":"invoice"}' --limit 10 --offset 0

# Search with sorting
docex document search --tenant-id docEX-Demo-PS --basket-id bas_123 --metadata '{"category":"invoice"}' --order-by created_at --order-desc

# JSON output
docex document search --tenant-id docEX-Demo-PS --basket-id bas_123 --metadata '{"category":"invoice"}' --format json
```

**Options:**
- `--tenant-id` - Tenant ID for multi-tenant setups
- `--basket-id` - Basket ID (required)
- `--metadata` - Metadata filter as JSON (required)
- `--limit` - Maximum number of results to return
- `--offset` - Number of results to skip (default: 0)
- `--order-by` - Field to sort by: `name`, `created_at`, `updated_at`, `size`
- `--order-desc` - Sort in descending order
- `--format` - Output format: `table` (default), `json`, or `simple`

**Metadata Filter Examples:**
```json
# Single filter
{"category":"invoice"}

# Multiple filters (AND)
{"category":"invoice","author":"Alice","status":"processed"}

# With numeric values
{"document_number":123,"batch":"test_batch"}
```

### Get Document Details

Get detailed information about a specific document.

```bash
# Get document details
docex document get --tenant-id docEX-Demo-PS --basket-id bas_123 --document-id doc_456

# JSON output
docex document get --tenant-id docEX-Demo-PS --basket-id bas_123 --document-id doc_456 --format json
```

**Options:**
- `--tenant-id` - Tenant ID for multi-tenant setups
- `--basket-id` - Basket ID (required)
- `--document-id` - Document ID (required)
- `--format` - Output format: `table` (default), `json`, or `simple`

### Add Document

Add a document to a basket.

```bash
# Add a document
docex document add --tenant-id docEX-Demo-PS --basket-id bas_123 --file /path/to/document.pdf

# Add with metadata
docex document add --tenant-id docEX-Demo-PS --basket-id bas_123 --file /path/to/document.pdf --metadata '{"author":"Alice","category":"invoice"}'

# Add with document type
docex document add --tenant-id docEX-Demo-PS --basket-id bas_123 --file /path/to/document.pdf --document-type purchase_order
```

**Options:**
- `--tenant-id` - Tenant ID for multi-tenant setups
- `--basket-id` - Basket ID (required)
- `--file` - Path to file to add (required)
- `--metadata` - Metadata as JSON
- `--document-type` - Document type (default: `file`)

## Tenant Commands

### Provision Tenant

Provision a new tenant with isolated database/schema.

```bash
# Provision a tenant
docex provision-tenant --tenant-id acme-corp

# Provision with verification
docex provision-tenant --tenant-id acme-corp --verify

# Enable multi-tenancy and provision
docex provision-tenant --tenant-id acme-corp --enable-multi-tenancy
```

**Options:**
- `--tenant-id` - Tenant ID to provision (required)
- `--verify` - Verify tenant by creating a test basket
- `--enable-multi-tenancy` - Enable database-level multi-tenancy in config if not already enabled

## Vector Indexing Commands

### Embed Documents

Generate vector embeddings for documents.

```bash
# Index all documents for a tenant
docex embed --tenant-id my-tenant --all

# Index documents in a specific basket
docex embed --tenant-id my-tenant --basket my_basket_name

# Index with filters
docex embed --tenant-id my-tenant --all --document-type purchase_order

# Force re-indexing
docex embed --tenant-id my-tenant --all --force

# Dry run
docex embed --tenant-id my-tenant --all --dry-run
```

**Options:**
- `--tenant-id` - Tenant ID for multi-tenant setups
- `--all` - Index all documents across all baskets
- `--basket` - Index documents in a specific basket (by name)
- `--basket-id` - Index documents in a specific basket (by ID)
- `--document-type` - Filter documents by document type
- `--force` - Force re-indexing of already indexed documents
- `--model` - Embedding model to use (default: `all-mpnet-base-v2`)
- `--batch-size` - Number of documents to process in each batch (default: 10)
- `--limit` - Maximum number of documents to index
- `--skip` - Number of documents to skip (for pagination)
- `--dry-run` - Show what would be indexed without actually indexing
- `--vector-db-type` - Vector database type: `pgvector` (default) or `memory`

## Output Formats

### Table Format (Default)

Human-readable table format with headers and alignment.

```bash
docex document list --basket-id bas_123
```

### JSON Format

Machine-readable JSON output.

```bash
docex document list --basket-id bas_123 --format json
```

### Simple Format

Tab-separated values, suitable for scripting.

```bash
docex document list --basket-id bas_123 --format simple
```

## Examples

### Complete Workflow

```bash
# 1. Provision a tenant
docex provision-tenant --tenant-id acme-corp --enable-multi-tenancy --verify

# 2. List baskets
docex basket list --tenant-id acme-corp

# 3. Create a basket
docex basket create --tenant-id acme-corp --name "Invoices" --description "Invoice documents"

# 4. Add documents
docex document add --tenant-id acme-corp --basket-id bas_123 --file invoice1.pdf --metadata '{"category":"invoice","author":"Alice"}'
docex document add --tenant-id acme-corp --basket-id bas_123 --file invoice2.pdf --metadata '{"category":"invoice","author":"Bob"}'

# 5. List documents with pagination
docex document list --tenant-id acme-corp --basket-id bas_123 --limit 10 --order-by created_at --order-desc

# 6. Search by metadata
docex document search --tenant-id acme-corp --basket-id bas_123 --metadata '{"category":"invoice"}' --limit 10

# 7. Count documents
docex document count --tenant-id acme-corp --basket-id bas_123

# 8. Index for semantic search
docex embed --tenant-id acme-corp --basket-id bas_123
```

### Advanced Queries

```bash
# Find all invoices by Alice, sorted by creation date
docex document search --tenant-id acme-corp --basket-id bas_123 \
  --metadata '{"category":"invoice","author":"Alice"}' \
  --order-by created_at --order-desc \
  --limit 20

# List documents with pagination (page 3)
docex document list --tenant-id acme-corp --basket-id bas_123 \
  --limit 20 --offset 40 \
  --order-by name

# Get document details
docex document get --tenant-id acme-corp --basket-id bas_123 --document-id doc_456
```

## Tips

1. **Use JSON format for scripting**: When integrating with other tools, use `--format json` for machine-readable output.

2. **Pagination for large datasets**: Always use `--limit` and `--offset` when working with large numbers of documents.

3. **Metadata search is case-sensitive**: Metadata values must match exactly (including JSON encoding).

4. **Tenant ID is optional**: If multi-tenancy is not enabled, you can omit `--tenant-id`.

5. **Use dry-run for testing**: Use `--dry-run` with embed command to see what would be indexed without actually doing it.

## Troubleshooting

### Error: "Basket not found"
- Verify the basket ID with `docex basket list`
- Ensure you're using the correct tenant ID

### Error: "Invalid JSON in --metadata"
- Ensure JSON is properly quoted: `'{"key":"value"}'`
- Use single quotes around the JSON string
- Escape special characters if needed

### Error: "Tenant not found"
- Verify tenant exists: `docex provision-tenant --tenant-id <id> --verify`
- Check multi-tenancy is enabled in config

### Performance Tips
- Use `--limit` to avoid loading too many documents at once
- Use `--order-by` with indexed fields (name, created_at) for better performance
- Use metadata search instead of filtering after loading all documents

## See Also

- [Tenant Provisioning Guide](TENANT_PROVISIONING.md)
- [Document Query Optimizations](DOCUMENT_QUERY_OPTIMIZATIONS.md)
- [Multi-Tenancy Guide](MULTI_TENANCY_GUIDE.md)

