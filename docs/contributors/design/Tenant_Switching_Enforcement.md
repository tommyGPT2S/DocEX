# Tenant Switching Enforcement

## Overview

DocEX 3.0 enforces strict tenant isolation by requiring explicit connection closure before switching tenants. This prevents accidental cross-tenant data access and ensures all database connections are properly closed and re-initialized.

## Enforcement Rules

### Rule 1: Cannot Switch Tenants Without Reset

If a `DocEX` instance is currently using a tenant, you **cannot** switch to a different tenant without explicitly closing connections:

```python
# ❌ This will raise ValueError
docex_acme = DocEX(user_context=UserContext(user_id='u1', tenant_id='acme'))
# ... do work ...
docex_contoso = DocEX(user_context=UserContext(user_id='u1', tenant_id='contoso'))
# ValueError: Cannot switch tenant from 'acme' to 'contoso' without resetting
```

### Rule 2: Must Close Connections Before Switching

All database connections must be closed before switching tenants:

```python
# ✅ Correct approach
docex_acme = DocEX(user_context=UserContext(user_id='u1', tenant_id='acme'))
# ... do work ...
docex_acme.close()  # Required: closes all DB connections
docex_contoso = DocEX(user_context=UserContext(user_id='u1', tenant_id='contoso'))
```

### Rule 3: Process Each Tenant Completely

Process all operations for one tenant before moving to the next:

```python
# ✅ Correct: Process tenant completely
for tenant_id in ['acme', 'contoso']:
    docex = DocEX(user_context=UserContext(user_id='u1', tenant_id=tenant_id))
    basket = docex.create_basket('basket')
    doc = basket.add('/path/to/doc.pdf')
    docex.close()  # Close before next tenant
```

## Implementation Details

### DocEX.close() Method

The `close()` method:
1. Closes the current database connection (`self.db.close()`)
2. Closes tenant-specific connections in `TenantDatabaseManager`
3. Resets `user_context` to `None`
4. Allows creation of a new `DocEX` instance with a different tenant

### DocEX.reset() Method

Alias for `close()` - provides semantic clarity when resetting state.

### Error Message

When attempting to switch tenants without closing, you'll receive:

```
ValueError: Cannot switch tenant from '{current_tenant}' to '{new_tenant}' without resetting. 
All database connections must be closed before switching tenants. 
Call DocEX.reset() or DocEX.close() first, then create a new DocEX instance with the new tenant_id.
```

## Benefits

1. **Security**: Prevents accidental cross-tenant data access
2. **Isolation**: Ensures clean separation between tenants
3. **Resource Management**: Properly closes database connections
4. **Clarity**: Makes tenant switching explicit and intentional
5. **Debugging**: Clear error messages when rules are violated

## Migration Guide

If you have existing code that switches tenants:

**Before (v2.x behavior - no enforcement):**
```python
docex_acme = DocEX(user_context=UserContext(user_id='u1', tenant_id='acme'))
# ... work ...
docex_contoso = DocEX(user_context=UserContext(user_id='u1', tenant_id='contoso'))
```

**After (v3.0 - enforced):**
```python
docex_acme = DocEX(user_context=UserContext(user_id='u1', tenant_id='acme'))
# ... work ...
docex_acme.close()  # Add this line
docex_contoso = DocEX(user_context=UserContext(user_id='u1', tenant_id='contoso'))
```

## Best Practices

1. **Always close before switching**: Call `close()` or `reset()` before creating a new `DocEX` instance with a different tenant
2. **Process tenants sequentially**: Complete all work for one tenant before moving to the next
3. **Use context managers**: Consider wrapping tenant operations in try/finally to ensure cleanup:

```python
docex = DocEX(user_context=UserContext(user_id='u1', tenant_id='acme'))
try:
    # Do work
    basket = docex.create_basket('basket')
finally:
    docex.close()  # Always close, even on error
```

4. **Single tenant per request**: In web applications, process one tenant per request - don't switch tenants within a single request

## Testing

The enforcement is tested and verified:

```python
from docex import DocEX
from docex.context import UserContext

# Test: Cannot switch without closing
docex_acme = DocEX(user_context=UserContext(user_id='u1', tenant_id='acme'))
try:
    docex_contoso = DocEX(user_context=UserContext(user_id='u1', tenant_id='contoso'))
    assert False, "Should have raised ValueError"
except ValueError:
    pass  # Expected

# Test: Can switch after closing
docex_acme.close()
docex_contoso = DocEX(user_context=UserContext(user_id='u1', tenant_id='contoso'))
# Success!
```

