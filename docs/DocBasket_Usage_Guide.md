# DocBasket Usage Guide

## Overview

`DocBasket` provides methods for managing document baskets and their documents. This guide explains the proper usage patterns, especially regarding the `list()` method which has both a classmethod and instance method.

## Listing Baskets vs Listing Documents

**Important:** Both `list()` methods (classmethod and instance) are **deprecated** due to:
- Method resolution conflicts between classmethod and instance method
- Ambiguity in the API
- Better alternatives available

### Recommended: Use DocEX.list_baskets() for Baskets

**The recommended way to list baskets is through DocEX:**

```python
from docex import DocEX
from docex.context import UserContext

# Initialize DocEX with tenant context (for multi-tenant setups)
user_context = UserContext(user_id='user123', tenant_id='acme_corp')
docex = DocEX(user_context=user_context)

# List all baskets (recommended)
baskets = docex.list_baskets()
for basket in baskets:
    print(f"Basket: {basket.name} (ID: {basket.id})")
```

**Why use `DocEX.list_baskets()`?**
- ✅ Always works correctly
- ✅ Automatically uses tenant-aware database
- ✅ No method resolution ambiguity
- ✅ Cleaner API

### Alternative: Direct DocBasket Usage (Advanced)

**Note:** `DocBasket.list()` classmethod is deprecated. Use one of these:

```python
from docex.docbasket import DocBasket
from docex.db.connection import Database

# Option 1: Use internal method directly (most reliable)
db = Database()
db.tenant_id = 'acme_corp'
baskets = DocBasket._list_all_baskets(db=db)  # ✅ Always works

# Option 2: Deprecated - may have method resolution issues
baskets = DocBasket.list()  # ⚠️ Deprecated, use DocEX.list_baskets() instead
```

**Important Notes:**
- `DocBasket.list()` is deprecated and may fail due to method resolution conflicts
- Always use `DocEX.list_baskets()` for listing baskets (recommended)
- `DocBasket._list_all_baskets(db=db)` is available for programmatic access

#### Listing Documents in a Basket

```python
from docex import DocEX
from docex.context import UserContext

# Get a basket
user_context = UserContext(user_id='user123', tenant_id='acme_corp')
docex = DocEX(user_context=user_context)
basket = docex.get_basket('my_basket_id')

# ✅ Recommended: Use list_documents() - explicit and supports filters
documents = basket.list_documents()

# With filters and pagination
documents = basket.list_documents(
    limit=10,
    offset=0,
    order_by='created_at',
    order_desc=True,
    status='active'
)

# ⚠️ Deprecated: basket.list() - kept for backward compatibility only
documents = basket.list()  # Will show deprecation warning
```

## Complete Usage Examples

### Example 1: Basic Basket Operations

```python
from docex import DocEX
from docex.context import UserContext

# Setup
user_context = UserContext(user_id='user123', tenant_id='acme_corp')
docex = DocEX(user_context=user_context)

# Create a basket
basket = docex.create_basket('invoices', description='Invoice documents')

# List all baskets (recommended way)
all_baskets = docex.list_baskets()
print(f"Total baskets: {len(all_baskets)}")

# List documents in a specific basket
documents = basket.list()  # or basket.list_documents()
print(f"Documents in basket: {len(documents)}")
```

### Example 2: Direct DocBasket Usage (Advanced)

```python
from docex.docbasket import DocBasket
from docex.db.connection import Database
from docex.context import UserContext

# Setup tenant-aware database
user_context = UserContext(user_id='user123', tenant_id='acme_corp')
docex = DocEX(user_context=user_context)
db = docex.db  # Get tenant-aware database

# List all baskets using internal method (most reliable)
baskets = DocBasket._list_all_baskets(db=db)

# Get a specific basket
basket = DocBasket.get('bas_123456', db=db)

# List documents in the basket
documents = basket.list()  # Instance method
```

### Example 3: Multi-Tenant Usage

```python
from docex import DocEX
from docex.context import UserContext

# Tenant 1
user_context_1 = UserContext(user_id='user123', tenant_id='acme_corp')
docex_1 = DocEX(user_context=user_context_1)
baskets_1 = docex_1.list_baskets()  # Lists baskets for acme_corp

# Tenant 2
user_context_2 = UserContext(user_id='user456', tenant_id='contoso')
docex_2 = DocEX(user_context=user_context_2)
baskets_2 = docex_2.list_baskets()  # Lists baskets for contoso
```

## Method Reference

### Class-Level Methods (List Baskets)

| Method | Description | Recommended Usage |
|--------|-------------|-------------------|
| `DocEX.list_baskets()` | List all baskets | ✅ **Recommended** - Use this |
| `DocBasket._list_all_baskets(db)` | List all baskets (internal) | Use when calling directly from code |
| `DocBasket.list()` | List all baskets (classmethod) | ⚠️ **Deprecated** - Use `DocEX.list_baskets()` |
| `DocBasket.create(name, ...)` | Create a new basket | ✅ Use directly |
| `DocBasket.get(basket_id, db)` | Get basket by ID | ✅ Use directly |
| `DocBasket.find_by_name(name, db)` | Find basket by name | ✅ Use directly |

### Instance Methods (List Documents)

| Method | Description | Recommended Usage |
|--------|-------------|-------------------|
| `basket.list_documents(...)` | List documents with filters | ✅ **Recommended** - Explicit and flexible |
| `basket.list()` | List documents in basket | ⚠️ **Deprecated** - Use `list_documents()` |
| `basket.add(file_path, ...)` | Add document to basket | ✅ Use directly |
| `basket.get_document(doc_id)` | Get document by ID | ✅ Use directly |
| `basket.count_documents(...)` | Count documents | ✅ Use directly |

## Best Practices

1. **Use DocEX API**: Always use `DocEX.list_baskets()` to list baskets - it's the recommended and most reliable method
2. **Use explicit methods**: Always use `basket.list_documents()` instead of `basket.list()` for clarity and features
3. **Avoid deprecated methods**: Both `DocBasket.list()` and `basket.list()` are deprecated - use the recommended alternatives
4. **For programmatic access**: Use `DocBasket._list_all_baskets(db)` when calling directly (internal API)
5. **Multi-tenant**: Always use tenant-aware database instances via `DocEX` or pass `db` parameter

## Troubleshooting

### Issue: "DocBasket.list() got an unexpected keyword argument 'db'"

**Cause**: Python's method resolution is selecting the instance method instead of the classmethod.

**Solution**: 
- Use `DocEX.list_baskets()` instead (recommended)
- Or use `DocBasket._list_all_baskets(db=db)` directly
- Or call `DocBasket.list()` without the `db` parameter

### Issue: "missing 1 required positional argument: 'self'"

**Cause**: Trying to call instance method as classmethod.

**Solution**: 
- Use `basket.list()` on an instance, not `DocBasket.list()` for documents
- Use `DocBasket.list()` or `DocBasket._list_all_baskets()` for baskets

## Summary

- **List baskets**: ✅ Use `DocEX.list_baskets()` (recommended and reliable)
- **List documents**: ✅ Use `basket.list_documents()` (recommended - explicit and feature-rich)
- **Avoid**: ⚠️ `DocBasket.list()` (deprecated, method resolution issues)
- **Avoid**: ⚠️ `basket.list()` (deprecated, use `list_documents()` instead)

## Migration Guide

If you're using deprecated methods, migrate to the recommended ones:

```python
# OLD (deprecated)
baskets = DocBasket.list()
documents = basket.list()

# NEW (recommended)
baskets = docex.list_baskets()  # or DocBasket._list_all_baskets(db)
documents = basket.list_documents()  # Supports filters, pagination, sorting
```

