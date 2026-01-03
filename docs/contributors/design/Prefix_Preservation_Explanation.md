# Prefix Preservation Fix Explanation

## What is "Prefix Preservation"?

The "Prefix preservation — hybrid format handler fixed" refers to a bug fix in `DocBasket.create()` where the hybrid format handler was incorrectly overwriting pre-resolved S3 prefixes.

## The Problem

When `ConfigResolver.get_storage_config_for_tenant()` pre-resolves the S3 prefix (e.g., `acme-corp/production/tenant_acme`), the hybrid format handler in `DocBasket.create()` was overwriting this correctly resolved prefix with a top-level `prefix` value from the config, if one existed.

This caused:
- Incorrect S3 prefixes in basket storage_config
- Mismatch between database paths and actual S3 keys
- Potential cross-tenant data access issues

## The Fix

The fix ensures that if `s3.prefix` is already set (pre-resolved by `ConfigResolver`), it is **not** overwritten by top-level `prefix` values. The code now checks:

```python
# Handle prefix separately - only use top-level prefix if s3.prefix is not set
if 'prefix' in storage_config and storage_config['prefix'] is not None:
    if 'prefix' not in s3_config or not s3_config['prefix']:
        # Only use top-level prefix if s3.prefix is not already set
        s3_config['prefix'] = storage_config['prefix']
    # Always remove from top level to avoid duplication
    del storage_config['prefix']
```

## Breaking Backward Compatibility

Since we're moving to DocEX 3.0, we can break backward compatibility. The following changes were made:

1. **Removed `tenant_id` parameter from `S3Storage._get_full_key()`**: The method now only accepts `path` as a parameter. The prefix should be pre-resolved during `S3Storage` initialization.

2. **Removed backward compatibility code**: The deprecation warning and fallback logic for `tenant_id` parameter have been removed.

## Impact

- **S3Storage** is now a pure low-level storage abstraction
- All path resolution must happen at higher levels (e.g., `DocEXPathResolver`, `ConfigResolver`)
- This ensures consistent path resolution across the system
- Eliminates one-off path building logic

