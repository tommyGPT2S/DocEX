# Runtime Tenant Setup Guide

This guide explains how developers should handle tenant setup and switching at runtime in DocEX 3.0.

## Overview

In DocEX 3.0, multi-tenancy is **explicit and mandatory** when enabled. Every operation requires a `UserContext` with a valid `tenant_id`. The `DocEX` singleton pattern automatically switches database connections when the `tenant_id` changes.

## Key Concepts

1. **UserContext**: Carries user identity and tenant information
2. **DocEX Singleton**: Automatically switches database connections based on `UserContext.tenant_id`
3. **Basket Objects**: Retain references to their tenant's database connection
4. **Tenant Isolation**: Each tenant has its own database schema (PostgreSQL) or database file (SQLite)

## Pattern 1: Single Tenant Operation

For operations within a single tenant, create `DocEX` once with the appropriate `UserContext`:

```python
from docex import DocEX, UserContext

# Create UserContext for tenant 'acme'
user_context = UserContext(
    user_id='user123',
    tenant_id='acme',
    roles=['user']
)

# Create DocEX instance (singleton pattern)
docex = DocEX(user_context=user_context)

# All operations now use tenant 'acme'
basket = docex.create_basket('my_basket')
doc = basket.add('/path/to/document.pdf')
```

## Pattern 2: Multiple Tenant Operations

When working with multiple tenants, **always close the current tenant connection before switching**:

```python
from docex import DocEX, UserContext

tenants = ['acme', 'contoso']

# Process each tenant completely before moving to the next
for tenant_id in tenants:
    # Create UserContext for this tenant
    user_context = UserContext(
        user_id='admin',
        tenant_id=tenant_id,
        roles=['admin']
    )
    
    # Create DocEX instance - singleton will use this tenant
    docex = DocEX(user_context=user_context)
    
    # Get tenant-aware storage config
    from docex.config.config_resolver import ConfigResolver
    resolver = ConfigResolver()
    storage_config = resolver.get_storage_config_for_tenant(tenant_id)
    
    # Create basket - will be created in this tenant's schema
    basket = docex.create_basket(f'{tenant_id}_basket', storage_config=storage_config)
    
    # Add documents immediately (process tenant completely)
    doc = basket.add('/path/to/document.pdf')
    
    # Close connection before moving to next tenant
    docex.close()  # Required: closes all DB connections
```

**IMPORTANT**: You **cannot** switch tenants without closing connections first:

```python
# ❌ WRONG: This will raise ValueError
docex_acme = DocEX(user_context=UserContext(user_id='u1', tenant_id='acme'))
# ... do work ...
docex_contoso = DocEX(user_context=UserContext(user_id='u1', tenant_id='contoso'))
# ValueError: Cannot switch tenant from 'acme' to 'contoso' without resetting

# ✅ CORRECT: Close first, then switch
docex_acme = DocEX(user_context=UserContext(user_id='u1', tenant_id='acme'))
# ... do work ...
docex_acme.close()  # Close all connections
docex_contoso = DocEX(user_context=UserContext(user_id='u1', tenant_id='contoso'))
```

## Pattern 3: Request-Based Tenant Switching (Web Applications)

In web applications, tenant context typically comes from the request (e.g., JWT token, subdomain, header):

```python
from docex import DocEX, UserContext
from flask import request, g

def get_tenant_from_request():
    """Extract tenant_id from request (e.g., JWT token, subdomain)"""
    # Example: Extract from JWT token
    token = request.headers.get('Authorization')
    # ... decode token and extract tenant_id ...
    return 'acme'  # Example

@app.route('/api/baskets', methods=['POST'])
def create_basket():
    # Extract tenant from request
    tenant_id = get_tenant_from_request()
    user_id = get_user_from_request()  # Extract from JWT or session
    
    # Create UserContext
    user_context = UserContext(
        user_id=user_id,
        tenant_id=tenant_id,
        roles=get_user_roles(user_id)
    )
    
    # Create DocEX instance with tenant context
    docex = DocEX(user_context=user_context)
    
    # All operations use this tenant's database
    basket = docex.create_basket(request.json['name'])
    return {'basket_id': basket.id}
```

## Pattern 4: Batch Processing Multiple Tenants

For batch jobs that process multiple tenants:

```python
from docex import DocEX, UserContext
from docex.provisioning.tenant_provisioner import TenantProvisioner

def process_all_tenants():
    """Process documents for all tenants"""
    config = DocEXConfig()
    provisioner = TenantProvisioner(config)
    
    # Get all tenants from registry
    from docex.db.connection import Database
    from docex.db.tenant_registry_model import TenantRegistry
    
    bootstrap_db = Database(config=config, tenant_id='_docex_system_')
    with bootstrap_db.session() as session:
        tenants = session.query(TenantRegistry).filter_by(is_system=False).all()
    
    # Process each tenant
    for tenant_record in tenants:
        tenant_id = tenant_record.tenant_id
        
        # Create UserContext for this tenant
        user_context = UserContext(
            user_id='batch_processor',
            tenant_id=tenant_id,
            roles=['system']
        )
        
        # Create DocEX instance - singleton switches to this tenant
        docex = DocEX(user_context=user_context)
        
        # Process this tenant's documents
        baskets = docex.list_baskets()
        for basket in baskets:
            # Process documents in this basket
            documents = basket.list_documents()
            for doc in documents:
                # Process document...
                pass
```

## Important Notes

### 1. Always Create DocEX with UserContext

**❌ WRONG:**
```python
docex = DocEX()  # No UserContext - will fail if multi-tenancy enabled
```

**✅ CORRECT:**
```python
user_context = UserContext(user_id='user123', tenant_id='acme')
docex = DocEX(user_context=user_context)
```

### 2. Basket Objects Retain Tenant Connection

Basket objects created with a tenant-aware database connection retain that connection. However, when performing operations, ensure `DocEX` singleton is also set to the correct tenant:

```python
# Create basket for tenant 'acme'
docex_acme = DocEX(user_context=UserContext(user_id='u1', tenant_id='acme'))
basket = docex_acme.create_basket('my_basket')

# Later, when adding documents, ensure DocEX is set to 'acme'
docex_acme = DocEX(user_context=UserContext(user_id='u1', tenant_id='acme'))
doc = basket.add('/path/to/doc.pdf')  # Uses basket's database connection
```

### 3. Singleton Pattern Behavior

The `DocEX` singleton automatically switches database connections when you create a new instance with a different `tenant_id`:

```python
# First tenant
docex1 = DocEX(user_context=UserContext(user_id='u1', tenant_id='acme'))
# docex1.db points to tenant_acme schema

# Second tenant (singleton switches)
docex2 = DocEX(user_context=UserContext(user_id='u2', tenant_id='contoso'))
# docex2.db now points to tenant_contoso schema
# docex1 and docex2 are the same object (singleton)
```

### 4. Storage Configuration

Always use `ConfigResolver.get_storage_config_for_tenant()` to get tenant-aware storage configuration:

```python
from docex.config.config_resolver import ConfigResolver

resolver = ConfigResolver()
storage_config = resolver.get_storage_config_for_tenant('acme')
# storage_config['s3']['prefix'] will be: 'acme-corp/production/tenant_acme'

basket = docex.create_basket('my_basket', storage_config=storage_config)
```

## Common Pitfalls

### Pitfall 1: Reusing Basket Across Tenants

**❌ WRONG:**
```python
# Create basket for tenant 'acme'
docex_acme = DocEX(user_context=UserContext(user_id='u1', tenant_id='acme'))
basket = docex_acme.create_basket('my_basket')

# Switch to tenant 'contoso'
docex_contoso = DocEX(user_context=UserContext(user_id='u2', tenant_id='contoso'))

# Try to use basket from 'acme' - WRONG!
doc = basket.add('/path/to/doc.pdf')  # Will fail - basket is in 'acme' schema
```

**✅ CORRECT:**
```python
# Always use basket with the tenant it was created for
docex_acme = DocEX(user_context=UserContext(user_id='u1', tenant_id='acme'))
basket = docex_acme.create_basket('my_basket')

# When using basket, ensure DocEX is set to same tenant
docex_acme = DocEX(user_context=UserContext(user_id='u1', tenant_id='acme'))
doc = basket.add('/path/to/doc.pdf')  # Correct - both use 'acme'
```

### Pitfall 2: Not Switching Tenants in Loops

**❌ WRONG:**
```python
tenants = ['acme', 'contoso']
for tenant_id in tenants:
    user_context = UserContext(user_id='u1', tenant_id=tenant_id)
    docex = DocEX(user_context=user_context)
    basket = docex.create_basket('basket')
    
    # Later in same loop, DocEX singleton may have switched
    doc = basket.add('/path/to/doc.pdf')  # May use wrong tenant
```

**✅ CORRECT:**
```python
tenants = ['acme', 'contoso']
baskets = {}

# Create baskets
for tenant_id in tenants:
    user_context = UserContext(user_id='u1', tenant_id=tenant_id)
    docex = DocEX(user_context=user_context)
    basket = docex.create_basket('basket')
    baskets[tenant_id] = basket

# Add documents - create fresh DocEX for each tenant
for tenant_id, basket in baskets.items():
    user_context = UserContext(user_id='u1', tenant_id=tenant_id)
    docex = DocEX(user_context=user_context)
    doc = basket.add('/path/to/doc.pdf')  # Correct - both use same tenant
```

## Summary

1. **Always create `DocEX` with `UserContext`** containing a valid `tenant_id`
2. **Cannot switch tenants without closing connections** - call `docex.close()` or `docex.reset()` first
3. **All database connections must be closed** before switching to a different tenant
4. **Use `ConfigResolver.get_storage_config_for_tenant()`** for tenant-aware storage config
5. **Process one tenant completely** before moving to the next tenant
6. **Basket objects retain their tenant connection** - don't reuse baskets across tenants

### Tenant Switching Rules

- ✅ **Allowed**: Create `DocEX` with a tenant, do work, close, then create new `DocEX` with different tenant
- ❌ **Not Allowed**: Create `DocEX` with tenant A, then try to create another `DocEX` with tenant B without closing first
- ✅ **Required**: Call `docex.close()` or `docex.reset()` before switching tenants

## Important Implementation Note

### Tenant Switching Enforcement

DocEX **enforces** that you cannot switch tenants without explicitly closing connections:

1. **If a current tenant is set**, you **cannot** use a different `tenant_id` without calling `close()` or `reset()`
2. **All database connections must be closed** before switching tenants
3. **Process each tenant completely** before moving to the next

```python
# ✅ CORRECT: Process each tenant completely, close before switching
for tenant_id in ['acme', 'contoso']:
    user_context = UserContext(user_id='u1', tenant_id=tenant_id)
    docex = DocEX(user_context=user_context)
    basket = docex.create_basket('basket')
    doc = basket.add('/path/to/doc.pdf')  # Process immediately
    docex.close()  # Required: close connections before next tenant

# ❌ WRONG: This will raise ValueError
docex_acme = DocEX(user_context=UserContext(user_id='u1', tenant_id='acme'))
basket_acme = docex_acme.create_basket('basket')
# Try to switch without closing - WILL FAIL
docex_contoso = DocEX(user_context=UserContext(user_id='u1', tenant_id='contoso'))
# ValueError: Cannot switch tenant from 'acme' to 'contoso' without resetting

# ✅ CORRECT: Close first, then switch
docex_acme = DocEX(user_context=UserContext(user_id='u1', tenant_id='acme'))
basket_acme = docex_acme.create_basket('basket')
docex_acme.close()  # Close connections
docex_contoso = DocEX(user_context=UserContext(user_id='u1', tenant_id='contoso'))
basket_contoso = docex_contoso.create_basket('basket')
```

By following these patterns, you ensure proper tenant isolation and avoid cross-tenant data access issues.

