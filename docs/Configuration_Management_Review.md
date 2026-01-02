# Configuration Management Review & Improvements

## Overview

DocEX 3.0 now uses **configuration-file-only** approach. All configuration comes from `config.yaml`, with only `tenant_id` required at runtime.

---

## Key Principles

### 1. Configuration File Only
- ✅ All configuration in `config.yaml` (or `default_config.yaml`)
- ✅ No runtime configuration adjustments
- ✅ `DocEXConfig.setup()` is for initial setup only (backward compatibility)

### 2. Runtime Parameter: Only `tenant_id`
- ✅ Only `tenant_id` is passed at runtime
- ✅ All other values resolved from `config.yaml` using templates
- ✅ Templates use `{tenant_id}` placeholder

### 3. Explicit Resolution Methods
- ✅ `ConfigResolver.resolve_s3_prefix(tenant_id)` - Resolves S3 prefix
- ✅ `SchemaResolver.resolve_schema_name(tenant_id)` - Resolves DB schema
- ✅ `SchemaResolver.resolve_database_path(tenant_id)` - Resolves DB path

---

## Configuration Templates

### S3 Storage Prefix

**Config Structure:**
```yaml
storage:
  type: s3
  s3:
    bucket: my-documents-bucket
    app_name: docex              # Application namespace
    prefix: production            # Environment prefix
    region: us-east-1
```

**Resolution:**
```python
from docex.config.config_resolver import ConfigResolver

resolver = ConfigResolver()
prefix = resolver.resolve_s3_prefix(tenant_id="acme")
# Returns: "docex/production/tenant_acme/"
```

**Final S3 Key Structure:**
```
s3://bucket/docex/production/tenant_acme/documents/invoice.pdf
```

**Method Signature:**
```python
def resolve_s3_prefix(self, tenant_id: str) -> str:
    """
    Resolve S3 prefix for a tenant.
    
    Only parameter: tenant_id (runtime)
    All other config: from config.yaml
    
    Returns: "{app_name}/{prefix}/tenant_{tenant_id}/"
    """
```

---

### Database Schema (PostgreSQL)

**Config Structure:**
```yaml
database:
  type: postgres
  postgres:
    host: localhost
    port: 5432
    database: docex
    user: postgres
    password: postgres
    schema_template: "tenant_{tenant_id}"  # Template with {tenant_id}
```

**Resolution:**
```python
from docex.db.schema_resolver import SchemaResolver

resolver = SchemaResolver()
schema_name = resolver.resolve_schema_name(tenant_id="acme")
# Returns: "tenant_acme"
```

**Method Signature:**
```python
def resolve_schema_name(self, tenant_id: str) -> str:
    """
    Resolve database schema name for a tenant (PostgreSQL).
    
    Only parameter: tenant_id (runtime)
    All other config: from config.yaml (schema_template)
    
    Returns: Schema name (e.g., "tenant_acme")
    """
```

---

### Database Path (SQLite)

**Config Structure:**
```yaml
database:
  type: sqlite
  sqlite:
    path_template: "storage/tenant_{tenant_id}/docex.db"  # Template with {tenant_id}
```

**Resolution:**
```python
from docex.db.schema_resolver import SchemaResolver

resolver = SchemaResolver()
db_path = resolver.resolve_database_path(tenant_id="acme")
# Returns: "storage/tenant_acme/docex.db"
```

**Method Signature:**
```python
def resolve_database_path(self, tenant_id: str) -> str:
    """
    Resolve database file path for a tenant (SQLite).
    
    Only parameter: tenant_id (runtime)
    All other config: from config.yaml (path_template)
    
    Returns: Database file path (e.g., "storage/tenant_acme/docex.db")
    """
```

---

## Implementation Details

### ConfigResolver Class

**Location:** `docex/config/config_resolver.py`

**Methods:**
- `resolve_s3_prefix(tenant_id)` - S3 prefix resolution
- `resolve_db_schema_name(tenant_id)` - PostgreSQL schema resolution
- `resolve_db_path(tenant_id)` - SQLite database path resolution
- `get_storage_config_for_tenant(tenant_id)` - Complete storage config with tenant prefix
- `get_isolation_strategy()` - Get isolation strategy from config

### SchemaResolver Class

**Location:** `docex/db/schema_resolver.py`

**Methods:**
- `resolve_schema_name(tenant_id)` - PostgreSQL schema name
- `resolve_database_path(tenant_id)` - SQLite database path
- `resolve_isolation_boundary(tenant_id)` - Returns (type, name) tuple

---

## Updated Components

### 1. S3 Storage
- ✅ Updated `_get_full_key()` to accept optional `tenant_id`
- ✅ Uses `ConfigResolver` when `tenant_id` provided
- ✅ Falls back to initialization prefix if `tenant_id` not provided

### 2. TenantDatabaseManager
- ✅ Uses `SchemaResolver` for schema/database path resolution
- ✅ All configuration from `config.yaml`
- ✅ Only `tenant_id` required at runtime

### 3. TenantProvisioner
- ✅ Uses `SchemaResolver` for schema/database path resolution
- ✅ Consistent with runtime resolution

### 4. DocEXConfig
- ✅ `setup()` method updated to handle all config sections
- ✅ Documented as "initial setup only"
- ✅ Configuration should be managed via `config.yaml` file

---

## Usage Examples

### S3 Prefix Resolution
```python
from docex.config.config_resolver import ConfigResolver

resolver = ConfigResolver()

# Resolve S3 prefix for tenant
prefix = resolver.resolve_s3_prefix(tenant_id="acme")
# Result: "docex/production/tenant_acme/"

# Get complete storage config with tenant prefix
storage_config = resolver.get_storage_config_for_tenant(tenant_id="acme")
# storage_config['s3']['prefix'] = "docex/production/tenant_acme"
```

### Database Schema Resolution
```python
from docex.db.schema_resolver import SchemaResolver

resolver = SchemaResolver()

# PostgreSQL schema
schema_name = resolver.resolve_schema_name(tenant_id="acme")
# Result: "tenant_acme"

# SQLite database path
db_path = resolver.resolve_database_path(tenant_id="acme")
# Result: "storage/tenant_acme/docex.db"

# Isolation boundary (works for both)
boundary_type, boundary_name = resolver.resolve_isolation_boundary(tenant_id="acme")
# PostgreSQL: ('schema', 'tenant_acme')
# SQLite: ('database', 'storage/tenant_acme/docex.db')
```

---

## Configuration File Structure

### Complete Example

```yaml
# config.yaml
config_version: 1

# Database configuration
database:
  type: postgres  # or sqlite
  postgres:
    host: localhost
    port: 5432
    database: docex
    user: postgres
    password: postgres
    schema_template: "tenant_{tenant_id}"  # Template with {tenant_id}
  sqlite:
    path_template: "storage/tenant_{tenant_id}/docex.db"  # Template with {tenant_id}

# Storage configuration
storage:
  type: s3
  s3:
    bucket: my-documents-bucket
    app_name: docex              # Application namespace
    prefix: production            # Environment prefix
    region: us-east-1
    # Note: tenant_id automatically added: {app_name}/{prefix}/tenant_{tenant_id}/

# Multi-tenancy configuration
multi_tenancy:
  enabled: true
  isolation_strategy: schema
  bootstrap_tenant:
    id: _docex_system_
    display_name: DocEX System
    schema: docex_system
    database_path: storage/_docex_system_/docex.db
```

---

## Benefits

### 1. Single Source of Truth
- ✅ All configuration in `config.yaml`
- ✅ No runtime configuration adjustments
- ✅ Easy to version control and audit

### 2. Explicit Resolution
- ✅ Clear methods for resolving tenant-specific configs
- ✅ Easy to test and debug
- ✅ Self-documenting code

### 3. Runtime Simplicity
- ✅ Only `tenant_id` required at runtime
- ✅ No complex configuration passing
- ✅ Consistent across all components

### 4. Maintainability
- ✅ Configuration changes in one place
- ✅ Template-based approach is flexible
- ✅ Easy to add new resolution methods

---

## Migration Notes

### For Existing Code

**Before:**
```python
# Runtime configuration adjustments
storage_config = {
    'type': 's3',
    'bucket': 'my-bucket',
    'prefix': f"tenant_{tenant_id}/"
}
```

**After:**
```python
# Configuration from config.yaml, only tenant_id at runtime
from docex.config.config_resolver import ConfigResolver

resolver = ConfigResolver()
storage_config = resolver.get_storage_config_for_tenant(tenant_id=tenant_id)
```

---

## Summary

✅ **Configuration Management:** File-based only (`config.yaml`)  
✅ **Runtime Parameter:** Only `tenant_id`  
✅ **S3 Prefix Resolution:** `ConfigResolver.resolve_s3_prefix(tenant_id)`  
✅ **DB Schema Resolution:** `SchemaResolver.resolve_schema_name(tenant_id)`  
✅ **DB Path Resolution:** `SchemaResolver.resolve_database_path(tenant_id)`  
✅ **Explicit Methods:** All resolution methods are explicit and documented

