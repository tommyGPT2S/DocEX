# S3 Storage Path Resolution

## Overview

S3Storage is a **low-level storage abstraction** that should **NOT** resolve paths itself. All path resolution should happen at higher levels using `DocEXPathResolver` or `ConfigResolver` before passing configuration to `S3Storage`.

## Design Principle

**Storage classes are path-agnostic.** They receive fully resolved prefixes/paths and use them as-is. This ensures:
- Consistent path resolution across the system
- No one-off path construction logic
- Clear separation of concerns
- Easier testing and maintenance

## Path Resolution Flow

```
┌─────────────────────────────────────┐
│  DocBasket.create()                 │
│  or                                 │
│  ConfigResolver.get_storage_...()   │
└──────────────┬──────────────────────┘
               │
               │ Uses DocEXPathResolver
               │ or ConfigResolver
               ▼
┌─────────────────────────────────────┐
│  Resolve prefix with tenant_id      │
│  Example:                            │
│  "acme-corp/production/tenant_acme/" │
└──────────────┬──────────────────────┘
               │
               │ Passes resolved prefix
               │ in storage_config
               ▼
┌─────────────────────────────────────┐
│  S3Storage.__init__(config)          │
│  - Uses prefix as-is                 │
│  - No path resolution logic          │
└─────────────────────────────────────┘
```

## Usage Examples

### Correct: Pre-resolve prefix before creating S3Storage

```python
from docex.config.path_resolver import DocEXPathResolver
from docex.storage.s3_storage import S3Storage

# Resolve prefix at higher level
path_resolver = DocEXPathResolver()
tenant_prefix = path_resolver.resolve_s3_prefix(tenant_id='acme')
basket_prefix = path_resolver.resolve_s3_basket_prefix(tenant_id='acme', basket_id='basket_123')

# Pass fully resolved prefix to S3Storage
s3_config = {
    'bucket': 'my-bucket',
    'prefix': basket_prefix.rstrip('/'),  # Already includes tenant_id
    'region': 'us-east-1'
}
storage = S3Storage(s3_config)
```

### Correct: Use ConfigResolver

```python
from docex.config.config_resolver import ConfigResolver

resolver = ConfigResolver()
storage_config = resolver.get_storage_config_for_tenant(tenant_id='acme')
# storage_config['s3']['prefix'] is already resolved: "acme-corp/production/tenant_acme/"

storage = S3Storage(storage_config['s3'])
```

### Incorrect: Let S3Storage resolve paths

```python
# ❌ DON'T DO THIS
# S3Storage should not resolve paths itself
s3_config = {
    'bucket': 'my-bucket',
    'app_name': 'acme-corp',
    'prefix': 'production',
    # Missing tenant_id - S3Storage can't resolve it
}
storage = S3Storage(s3_config)  # Prefix won't include tenant_id!
```

## What S3Storage Does

1. **Receives** a fully resolved prefix in config
2. **Stores** the prefix as-is
3. **Uses** the prefix when constructing S3 keys
4. **Does NOT** resolve paths or construct prefixes

## What S3Storage Does NOT Do

1. ❌ Resolve tenant-aware prefixes
2. ❌ Build prefixes from app_name and prefix parts
3. ❌ Use DocEXPathResolver or ConfigResolver
4. ❌ Know about tenant_id or multi-tenancy

## Migration Guide

If you have code that passes `app_name` and `prefix` separately to S3Storage:

**Before:**
```python
s3_config = {
    'bucket': 'my-bucket',
    'app_name': 'acme-corp',
    'prefix': 'production',
    'region': 'us-east-1'
}
storage = S3Storage(s3_config)
```

**After:**
```python
from docex.config.path_resolver import DocEXPathResolver

path_resolver = DocEXPathResolver()
resolved_prefix = path_resolver.resolve_s3_prefix(tenant_id='acme')

s3_config = {
    'bucket': 'my-bucket',
    'prefix': resolved_prefix.rstrip('/'),  # Fully resolved
    'region': 'us-east-1'
}
storage = S3Storage(s3_config)
```

## Benefits

1. **Consistency**: All paths resolved the same way
2. **Maintainability**: Path logic in one place (DocEXPathResolver)
3. **Testability**: Easy to test path resolution separately
4. **Clarity**: Clear separation between storage and path resolution
5. **No One-offs**: No duplicate path construction logic

