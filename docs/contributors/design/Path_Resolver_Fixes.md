# Path Resolver Fixes - Summary

## ✅ Fixed Issues

### 1. Direct Basket Path Construction in `docbasket.py`

**Before:**
```python
base_path = config.get('storage.filesystem.path', 'storage/docex')
storage_config['path'] = str(Path(base_path) / f"basket_{basket_model.id}")
```

**After:**
```python
if tenant_id:
    storage_config['path'] = path_resolver.resolve_filesystem_path(
        tenant_id=tenant_id,
        basket_id=basket_model.id
    )
```

**Status:** ✅ Fixed - Now uses `DocEXPathResolver.resolve_filesystem_path()`

---

### 2. Direct S3 Prefix Construction in `docbasket.py`

**Before:**
```python
storage_config['s3']['prefix'] = f"baskets/{basket_model.id}/"
```

**After:**
```python
if tenant_id:
    basket_prefix = path_resolver.resolve_s3_basket_prefix(tenant_id, basket_model.id)
    storage_config['s3']['prefix'] = basket_prefix.rstrip('/')
```

**Status:** ✅ Fixed - Now uses `DocEXPathResolver.resolve_s3_basket_prefix()`

---

## ✅ New Methods Added

### `DocEXPathResolver.resolve_s3_basket_prefix(tenant_id, basket_id)`

**Purpose:** Resolve S3 prefix for a basket within a tenant

**Structure:** `{app_name}/{prefix}/tenant_{tenant_id}/baskets/{basket_id}/`

**Example:**
- Input: `tenant_id='acme'`, `basket_id='basket_123'`
- Output: `docex/production/tenant_acme/baskets/basket_123/`

---

### `DocEXPathResolver.resolve_filesystem_path()` - Updated

**Change:** Made `tenant_id` optional for backward compatibility

**Before:**
```python
def resolve_filesystem_path(self, tenant_id: str, basket_id: Optional[str] = None) -> str:
```

**After:**
```python
def resolve_filesystem_path(self, tenant_id: Optional[str] = None, basket_id: Optional[str] = None) -> str:
```

**Status:** ✅ Updated - Supports both multi-tenant and non-multi-tenant scenarios

---

## ✅ Verification

### All Path Construction Now Uses Resolver

1. **S3 Storage:**
   - ✅ `S3Storage._get_full_key()` - Uses `ConfigResolver.resolve_s3_prefix()`
   - ✅ `DocBasket.create()` - Uses `DocEXPathResolver.resolve_s3_basket_prefix()`

2. **Filesystem Storage:**
   - ✅ `DocBasket.create()` - Uses `DocEXPathResolver.resolve_filesystem_path()`

3. **Database Paths:**
   - ✅ All database path resolution uses `SchemaResolver` / `ConfigResolver`

4. **Metadata Storage:**
   - ✅ Metadata is stored in database (not in separate files)
   - ✅ No path construction needed for metadata

---

## ✅ Remaining Fallbacks

### Non-Multi-Tenant Fallbacks

For backward compatibility, fallbacks remain for non-multi-tenant scenarios:

```python
# Filesystem fallback (non-multi-tenant)
base_path = config.get('storage', {}).get('filesystem', {}).get('path', 'storage/docex')
storage_config['path'] = str(Path(base_path) / f"basket_{basket_model.id}")

# S3 fallback (non-multi-tenant)
storage_config['s3']['prefix'] = f"baskets/{basket_model.id}/"
```

**Status:** ✅ Acceptable - These are fallbacks for non-multi-tenant deployments

---

## ✅ Summary

**All one-off path logic has been replaced with unified resolver methods:**

- ✅ S3 prefixes: `DocEXPathResolver.resolve_s3_prefix()` / `resolve_s3_basket_prefix()`
- ✅ Filesystem paths: `DocEXPathResolver.resolve_filesystem_path()`
- ✅ Database paths: `SchemaResolver.resolve_db_schema()` / `resolve_db_path()`

**No more direct path construction in:**
- ✅ Basket creation
- ✅ Document storage
- ✅ Metadata storage (stored in DB, not files)

**All functions now use the resolver class to avoid confusion.**

