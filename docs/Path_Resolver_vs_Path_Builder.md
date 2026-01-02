# DocEXPathResolver vs DocEXPathBuilder

## Overview

DocEX has two related but distinct classes for path handling:

1. **`DocEXPathResolver`** - Configuration-based path resolution
2. **`DocEXPathBuilder`** - Operational path building from IDs

## DocEXPathResolver

**Location**: `docex/config/path_resolver.py`

**Purpose**: Resolves configuration-based path components from `config.yaml`

**Responsibilities**:
- Resolves tenant-specific prefixes (tenant_id → `{path_namespace}/{prefix}/{tenant_id}/`)
- Resolves database schema names and paths
- Works with configuration templates
- **Input**: `tenant_id` + config.yaml
- **Output**: Path components/prefixes (not full operational paths)

**Key Methods**:
- `resolve_s3_prefix(tenant_id)` → `"acme-corp/production/acme/"`
- `resolve_s3_basket_prefix(tenant_id, basket_id, basket_name)` → `"acme-corp/production/acme/invoices_a1b2/"`
- `resolve_filesystem_path(tenant_id, basket_id)` → Base filesystem paths
- `resolve_db_schema(tenant_id)` → Database schema names
- `resolve_db_path(tenant_id)` → Database file paths

**Use Cases**:
- Configuration resolution during setup
- Building tenant-aware storage configs
- Database schema/path resolution

## DocEXPathBuilder

**Location**: `docex/storage/path_builder.py`

**Purpose**: Builds complete operational paths from `basket_id` and `document_id`

**Responsibilities**:
- Builds full storage paths for operations (save, load, delete)
- Combines configuration prefixes with basket/document-specific parts
- Ensures S3Storage receives full paths (no interpretation needed)
- **Input**: `basket_id`, `document_id`, `basket_name`, `document_name`, `tenant_id`
- **Output**: Complete operational paths ready for storage backends

**Key Methods**:
- `build_basket_path(basket_id, basket_name, tenant_id)` → Full basket path
- `build_document_path(basket_id, document_id, basket_name, document_name, file_ext, tenant_id)` → Full document path
- `parse_path_to_ids(full_path)` → Reverse operation (internal use)

**Use Cases**:
- Building paths for S3Storage operations
- Building paths for filesystem operations
- Used by DocBasket when calling storage backends

## Relationship

```
DocEXPathBuilder (Operational Layer)
    ↓ uses
DocEXPathResolver (Configuration Layer)
    ↓ uses
ConfigResolver + SchemaResolver
```

**Example Flow**:

```python
# User operation (works with IDs only)
basket.add(file_path, metadata={...})
  ↓
# DocBasket uses DocEXPathBuilder
path_builder = DocEXPathBuilder()
full_path = path_builder.build_document_path(
    basket_id="bas_123",
    document_id="doc_456",
    basket_name="invoices",
    document_name="invoice_001",
    file_ext=".pdf",
    tenant_id="acme"
)
  ↓
# DocEXPathBuilder uses DocEXPathResolver internally
basket_prefix = path_resolver.resolve_s3_basket_prefix(
    tenant_id="acme",
    basket_id="bas_123",
    basket_name="invoices"
)
# Returns: "acme-corp/production/acme/invoices_a1b2/"
  ↓
# DocEXPathBuilder combines prefix with document filename
full_path = f"{basket_prefix}invoice_001_c3d4e5.pdf"
# Returns: "acme-corp/production/acme/invoices_a1b2/invoice_001_c3d4e5.pdf"
  ↓
# S3Storage receives full path (no interpretation)
s3_storage.save(full_path, content)
```

## Key Differences

| Aspect | DocEXPathResolver | DocEXPathBuilder |
|--------|-------------------|------------------|
| **Level** | Configuration resolution | Operational path building |
| **Input** | `tenant_id` + config | `basket_id` + `document_id` + metadata |
| **Output** | Path components/prefixes | Complete operational paths |
| **Used By** | Configuration setup, DocEXPathBuilder | DocBasket, storage operations |
| **Scope** | Tenant-level, configuration | Basket/document-level, operational |
| **Purpose** | Resolve config templates | Build paths for storage operations |

## Design Rationale

### Separation of Concerns

1. **Configuration Resolution** (`DocEXPathResolver`):
   - Handles how paths are structured based on config.yaml
   - Resolves tenant-specific prefixes
   - Database schema/path resolution
   - **Reusable** across different operational contexts

2. **Operational Path Building** (`DocEXPathBuilder`):
   - Handles building complete paths for actual operations
   - Combines config prefixes with operational data (basket_id, document_id)
   - Ensures storage backends receive full paths
   - **User-facing** - this is what DocBasket uses

### Why Two Classes?

1. **Reusability**: `DocEXPathResolver` can be used for configuration setup, tenant provisioning, etc., not just operational paths
2. **Clarity**: Clear separation between "how paths are structured" (resolver) vs "build a path for this operation" (builder)
3. **Testability**: Can test configuration resolution separately from operational path building
4. **Flexibility**: Can change operational path building logic without affecting configuration resolution

## Usage Guidelines

### Use DocEXPathResolver when:
- Setting up tenant-specific storage configurations
- Resolving database schema names/paths
- Building configuration-aware prefixes
- Working at the configuration/setup level

### Use DocEXPathBuilder when:
- Building paths for storage operations (save, load, delete)
- Working with basket_id and document_id
- Calling S3Storage or other storage backends
- Building operational paths from user-facing IDs

## Example: Complete Flow

```python
# 1. Configuration Resolution (DocEXPathResolver)
resolver = DocEXPathResolver()
tenant_prefix = resolver.resolve_s3_prefix(tenant_id="acme")
# Returns: "acme-corp/production/acme/"

# 2. Operational Path Building (DocEXPathBuilder)
builder = DocEXPathBuilder()
full_path = builder.build_document_path(
    basket_id="bas_1234567890abcdef",
    document_id="doc_9876543210fedcba",
    basket_name="invoices",
    document_name="invoice_001",
    file_ext=".pdf",
    tenant_id="acme"
)
# Returns: "acme-corp/production/acme/invoices_a1b2/invoice_001_c3d4e5.pdf"

# 3. Storage Operation (S3Storage - receives full path)
s3_storage.save(full_path, content)
# S3Storage does NOT interpret the path - it uses it as-is
```

## Summary

- **DocEXPathResolver**: Configuration layer - resolves path structure from config.yaml
- **DocEXPathBuilder**: Operational layer - builds complete paths from basket_id/document_id
- **DocEXPathBuilder uses DocEXPathResolver** internally for configuration-based prefixes
- **S3Storage**: Receives full paths from DocEXPathBuilder (no interpretation)

This separation ensures:
- ✅ Users work with `basket_id` and `document_id` only
- ✅ All path building is centralized
- ✅ S3Storage receives full paths (no interpretation)
- ✅ Clear separation of concerns

