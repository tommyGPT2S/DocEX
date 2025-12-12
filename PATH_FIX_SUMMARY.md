# DocEX Path Issue Fix Summary

## Issue Description

In production, both `./storage/docex` and `./storage/docex/docex` directories were being created, causing a double "docex" path issue.

## Root Cause

The bug was in `docex/docbasket.py` at line 423, where the document path was hardcoded with a "docex/" prefix:

```python
document_path = f"docex/basket_{self.id}/{document.id}"
```

However, the storage configuration already includes "docex" in the base path:
- Default config: `storage/docex` (from `default_config.yaml`)
- Basket storage path: `storage/docex/basket_{id}` (created in `DocBasket.create()`)

When storing a document:
1. Base storage path: `storage/docex/basket_{id}`
2. Document path (old): `docex/basket_{id}/{doc_id}`
3. Final path: `storage/docex/basket_{id}/docex/basket_{id}/{doc_id}` ❌

This created the nested `storage/docex/docex` structure.

## Fix

Changed line 423 in `docex/docbasket.py` to use only the document ID as the path, since it's relative to the basket's storage root:

```python
# Document path should be relative to the basket's storage root
# The basket storage path already includes the base path (e.g., storage/docex/basket_{id})
# So we only need the document ID as the path
document_path = str(document.id)
```

Now the path structure is correct:
1. Base storage path: `storage/docex/basket_{id}`
2. Document path (new): `{doc_id}`
3. Final path: `storage/docex/basket_{id}/{doc_id}` ✅

## Files Modified

- `docex/docbasket.py` (line 423-427)

## Testing Recommendations

1. Create a new basket and add documents
2. Verify the storage structure is: `storage/docex/basket_{id}/{doc_id}`
3. Ensure no `storage/docex/docex` directory is created
4. Verify document retrieval still works correctly

## Impact

- **Breaking Change**: Documents stored with the old path structure will need to be migrated
- **Backward Compatibility**: Existing documents in the database will still reference the old paths
- **Migration**: Consider creating a migration script to update document paths in the database if needed

## Related Code Review

Reviewed other path-related code:
- ✅ Database paths (`docex.db`) - correct
- ✅ Config paths (`~/.docex/`) - correct  
- ✅ Default storage path (`storage/docex`) - correct
- ✅ Tenant database paths - correct
- ✅ No other similar issues found

