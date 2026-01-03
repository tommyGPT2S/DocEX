# Path Resolver Analysis and Recommendations

## Current State

### Existing Resolvers

1. **ConfigResolver** (`docex/config/config_resolver.py`)
   - `resolve_s3_prefix(tenant_id)` - Resolves S3 prefix: `{app_name}/{prefix}/tenant_{tenant_id}/`
   - `resolve_db_schema_name(tenant_id)` - Resolves PostgreSQL schema names
   - `resolve_db_path(tenant_id)` - Resolves SQLite database paths

2. **SchemaResolver** (`docex/db/schema_resolver.py`)
   - Wrapper around ConfigResolver for database-specific resolution
   - `resolve_schema_name(tenant_id)`
   - `resolve_database_path(tenant_id)`
   - `resolve_isolation_boundary(tenant_id)`

### Missing: Unified Path Resolver

**There is NO `DocEXPathResolver` class** - path resolution is scattered:
- S3 paths: `ConfigResolver.resolve_s3_prefix()`
- Filesystem paths: Direct path construction in `FileSystemStorage`
- Database paths: `ConfigResolver.resolve_db_path()` / `SchemaResolver`

## Current S3 Prefix Structure

```
{app_name}/{prefix}/tenant_{tenant_id}/
```

**Example:**
- `docex/production/tenant_acme/`
- `docex/test/tenant_contoso/`

### Why Both `app_name` and `prefix`?

**Current Rationale:**
1. **`app_name`**: Application-level namespace
   - Use case: Multiple applications sharing the same S3 bucket
   - Example: `docex`, `docflow`, `docproc` all in same bucket
   - Structure: `docex/...`, `docflow/...`, `docproc/...`

2. **`prefix`**: Environment/instance-level namespace
   - Use case: Same application, different environments
   - Example: `production`, `staging`, `dev`, `test`
   - Structure: `docex/production/...`, `docex/staging/...`

**Combined Use Case:**
- Multiple applications, each with multiple environments
- Structure: `{app_name}/{environment}/tenant_{tenant_id}/`
- Example: `docex/production/tenant_acme/`, `docflow/staging/tenant_contoso/`

## Analysis: Do We Need Both?

### Option 1: Keep Both (Current)
**Pros:**
- Clear separation of concerns
- Supports complex multi-application, multi-environment deployments
- Flexible for enterprise use cases

**Cons:**
- More configuration parameters
- Potential confusion about when to use which
- More complex path resolution logic

### Option 2: Simplify to Single `prefix`
**Pros:**
- Simpler configuration
- Less confusion
- Still flexible (users can include app_name in prefix if needed)

**Cons:**
- Less structured
- Harder to enforce consistent naming
- Users must manually construct prefixes

### Option 3: Make `prefix` Optional
**Pros:**
- Backward compatible
- Simple for single-environment deployments
- Flexible for multi-environment deployments

**Cons:**
- Still two parameters, but one is optional

## Recommendation

### Keep Both, But Make `prefix` Optional

**Rationale:**
1. **`app_name` is essential** for multi-application deployments
2. **`prefix` is useful** for environment separation but not always needed
3. **Backward compatibility** - existing deployments may not have `prefix`

**Proposed Structure:**
```yaml
storage:
  s3:
    app_name: docex          # Required: Application identifier
    prefix: production       # Optional: Environment prefix (default: empty)
```

**Path Resolution:**
- If `prefix` provided: `{app_name}/{prefix}/tenant_{tenant_id}/`
- If `prefix` empty/omitted: `{app_name}/tenant_{tenant_id}/`

**Examples:**
- `docex/production/tenant_acme/` (with prefix)
- `docex/tenant_acme/` (without prefix)

## Proposed: Unified Path Resolver

Create a `DocEXPathResolver` class that unifies all path resolution:

```python
class DocEXPathResolver:
    """
    Unified path resolver for DocEX storage and database paths.
    
    Provides consistent path resolution across:
    - S3 storage prefixes
    - Filesystem storage paths
    - Database schema names
    - Database file paths
    """
    
    def __init__(self, config: Optional[DocEXConfig] = None):
        self.config = config or DocEXConfig()
        self.config_resolver = ConfigResolver(config)
        self.schema_resolver = SchemaResolver(config)
    
    # S3 Path Resolution
    def resolve_s3_prefix(self, tenant_id: str) -> str:
        """Resolve S3 prefix for tenant"""
        return self.config_resolver.resolve_s3_prefix(tenant_id)
    
    # Filesystem Path Resolution
    def resolve_filesystem_path(self, tenant_id: str, basket_id: Optional[str] = None) -> str:
        """Resolve filesystem storage path for tenant/basket"""
        # Implementation for filesystem paths
        pass
    
    # Database Path Resolution
    def resolve_db_schema(self, tenant_id: str) -> str:
        """Resolve database schema name for tenant"""
        return self.schema_resolver.resolve_schema_name(tenant_id)
    
    def resolve_db_path(self, tenant_id: str) -> str:
        """Resolve database file path for tenant"""
        return self.schema_resolver.resolve_database_path(tenant_id)
```

## Action Items

1. ✅ **Review current path resolution** - DONE
2. ⏳ **Decide on app_name vs prefix** - Make prefix optional
3. ⏳ **Create unified DocEXPathResolver** - If desired
4. ⏳ **Update S3 prefix resolution** - Make prefix optional
5. ⏳ **Update documentation** - Clarify app_name vs prefix usage

