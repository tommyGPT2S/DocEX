# Path Resolver Audit - One-Off Path Logic Scan

## Issues Found

### ❌ Issue 1: Direct Basket Path Construction in `docbasket.py`

**Location:** `docex/docbasket.py:163`
```python
storage_config['path'] = str(Path(base_path) / f"basket_{basket_model.id}")
```

**Problem:** Direct path construction without using `DocEXPathResolver`

**Should use:** `DocEXPathResolver.resolve_filesystem_path(tenant_id, basket_id)`

---

### ❌ Issue 2: Direct S3 Prefix Construction in `docbasket.py`

**Location:** `docex/docbasket.py:175`
```python
storage_config['s3']['prefix'] = f"baskets/{basket_model.id}/"
```

**Problem:** Direct S3 prefix construction without using `DocEXPathResolver`

**Should use:** `DocEXPathResolver.resolve_s3_prefix(tenant_id)` + basket suffix

---

### ❌ Issue 3: Direct Config Path Access in `docbasket.py`

**Location:** `docex/docbasket.py:162`
```python
base_path = config.get('storage.filesystem.path', 'storage/docex')
```

**Problem:** Direct config access instead of using path resolver

**Should use:** `DocEXPathResolver.resolve_filesystem_path(tenant_id)`

---

## ✅ Good Practices Found

### ✅ S3Storage._get_full_key() - Uses ConfigResolver
**Location:** `docex/storage/s3_storage.py:165-169`
```python
if tenant_id:
    from docex.config.config_resolver import ConfigResolver
    resolver = ConfigResolver()
    tenant_prefix = resolver.resolve_s3_prefix(tenant_id)
    return f"{tenant_prefix}{path}" if tenant_prefix else path
```
**Status:** ✅ Correctly uses ConfigResolver

---

### ✅ ConfigResolver.resolve_s3_prefix() - Centralized Logic
**Location:** `docex/config/config_resolver.py:31-83`
**Status:** ✅ All S3 prefix resolution goes through this method

---

## Recommendations

1. **Update `DocBasket.create()`** to use `DocEXPathResolver` for all path construction
2. **Ensure tenant_id is available** when creating baskets (from DocEX context)
3. **Create helper methods** in `DocEXPathResolver` for basket-specific paths
4. **Update all path construction** to go through the resolver

