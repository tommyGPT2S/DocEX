# Multi-Tenancy Guide

## Overview

DocEX supports **database-level multi-tenancy** (Model B), where each tenant has its own isolated database (SQLite) or schema (PostgreSQL). This provides the strongest data isolation and is ideal for compliance requirements.

## Architecture

### Database-Level Isolation

When `multi_tenancy_model: database_level` is configured, DocEX automatically:
1. Routes database operations to tenant-specific database/schema based on `UserContext.tenant_id`
2. Creates tenant schemas/databases automatically on first access
3. Maintains separate connection pools per tenant
4. Ensures complete data isolation between tenants

### Connection Management

The `TenantDatabaseManager` (singleton) manages all tenant connections:
- **Connection Pooling**: Each tenant has its own connection pool
- **Thread-Safe**: Concurrent access to different tenants is safe
- **Lazy Initialization**: Tenant databases/schemas created on first access
- **Automatic Cleanup**: Connections can be closed per tenant or all at once

## Configuration

### PostgreSQL (Schema per Tenant)

```yaml
# ~/.docex/config.yaml
security:
  multi_tenancy_model: database_level
  tenant_database_routing: true

database:
  type: postgresql
  postgres:
    host: localhost
    port: 5432
    database: docex
    user: postgres
    password: postgres
    schema_template: "tenant_{tenant_id}"  # Schema name pattern
```

**Result**: Each tenant gets its own schema:
- `tenant_tenant1` schema
- `tenant_tenant2` schema
- etc.

### SQLite (Database File per Tenant)

```yaml
# ~/.docex/config.yaml
security:
  multi_tenancy_model: database_level
  tenant_database_routing: true

database:
  type: sqlite
  sqlite:
    path_template: "storage/tenant_{tenant_id}/docex.db"
```

**Result**: Each tenant gets its own database file:
- `storage/tenant_tenant1/docex.db`
- `storage/tenant_tenant2/docex.db`
- etc.

## Usage

### Basic Usage

```python
from docex import DocEX
from docex.context import UserContext

# Initialize DocEX with tenant context
user_context = UserContext(
    user_id="alice",
    tenant_id="tenant1",
    user_email="alice@example.com"
)

docEX = DocEX(user_context=user_context)

# All operations automatically use tenant1's database/schema
basket = docEX.create_basket("invoices")
document = basket.add("invoice.pdf")
```

### Multiple Tenants

```python
# Tenant 1
user_context1 = UserContext(user_id="alice", tenant_id="tenant1")
docEX1 = DocEX(user_context=user_context1)
basket1 = docEX1.create_basket("invoices")
doc1 = basket1.add("invoice1.pdf")

# Tenant 2 (completely isolated)
user_context2 = UserContext(user_id="bob", tenant_id="tenant2")
docEX2 = DocEX(user_context=user_context2)
basket2 = docEX2.create_basket("invoices")
doc2 = basket2.add("invoice2.pdf")

# Each tenant only sees their own data
baskets1 = docEX1.list_baskets()  # Only tenant1 baskets
baskets2 = docEX2.list_baskets()  # Only tenant2 baskets
```

### Tenant Database Management

```python
from docex.db.tenant_database_manager import TenantDatabaseManager

# Get tenant database manager
manager = TenantDatabaseManager()

# List all active tenant connections
tenant_ids = manager.list_tenant_databases()
print(f"Active tenants: {tenant_ids}")

# Close connection for specific tenant
manager.close_tenant_connection("tenant1")

# Close all tenant connections
manager.close_all_connections()
```

## Schema Initialization

Tenant schemas/databases are automatically created on first access. The initialization process:

1. **PostgreSQL**: Creates schema if it doesn't exist, then creates all tables
2. **SQLite**: Creates database file and directory if needed, then creates all tables

All tables from the DocEX schema are created in each tenant's database/schema:
- `docbasket`
- `document`
- `document_metadata`
- `file_history`
- `operations`
- `operation_dependencies`
- `doc_events`
- `transport_routes`
- `route_operations`
- `processors`
- `processing_operations`

## Best Practices

### 1. Always Provide UserContext

```python
# ✅ Good: Always provide UserContext with tenant_id
user_context = UserContext(user_id="alice", tenant_id="tenant1")
docEX = DocEX(user_context=user_context)

# ❌ Bad: Missing tenant_id will fail in database-level mode
docEX = DocEX()  # Will raise error if multi_tenancy_model: database_level
```

### 2. Tenant ID Validation

Validate tenant_id before creating DocEX instance:

```python
def get_docex_for_user(user_id: str, tenant_id: str):
    # Validate tenant_id
    if not tenant_id or not tenant_id.isalnum():
        raise ValueError("Invalid tenant_id")
    
    user_context = UserContext(user_id=user_id, tenant_id=tenant_id)
    return DocEX(user_context=user_context)
```

### 3. Connection Pool Management

For applications with many tenants, monitor connection pool usage:

```python
from docex.db.tenant_database_manager import TenantDatabaseManager

manager = TenantDatabaseManager()

# Periodically close idle tenant connections
active_tenants = manager.list_tenant_databases()
for tenant_id in active_tenants:
    # Check if tenant is still active (your logic)
    if not is_tenant_active(tenant_id):
        manager.close_tenant_connection(tenant_id)
```

### 4. Error Handling

```python
from docex import DocEX
from docex.context import UserContext

try:
    user_context = UserContext(user_id="alice", tenant_id="tenant1")
    docEX = DocEX(user_context=user_context)
    basket = docEX.create_basket("invoices")
except ValueError as e:
    # Handle missing tenant_id
    print(f"Tenant context required: {e}")
except RuntimeError as e:
    # Handle database connection errors
    print(f"Database error: {e}")
```

## Migration from Single-Tenant

To migrate from single-tenant to multi-tenant:

1. **Backup existing data**:
   ```bash
   # PostgreSQL
   pg_dump -h localhost -U postgres docex > backup.sql
   
   # SQLite
   cp docex.db backup.db
   ```

2. **Update configuration**:
   ```yaml
   security:
     multi_tenancy_model: database_level
     tenant_database_routing: true
   ```

3. **Migrate data to tenant schemas**:
   ```python
   # Create migration script to move data to tenant schemas
   # This is application-specific
   ```

4. **Test with multiple tenants**:
   ```python
   # Verify tenant isolation
   # Test that tenant1 cannot access tenant2 data
   ```

## Troubleshooting

### Issue: "tenant_id is required"

**Cause**: Database-level multi-tenancy is enabled but `UserContext.tenant_id` is missing.

**Solution**: Always provide `UserContext` with `tenant_id`:
```python
user_context = UserContext(user_id="alice", tenant_id="tenant1")
docEX = DocEX(user_context=user_context)
```

### Issue: Schema creation fails (PostgreSQL)

**Cause**: Database user doesn't have CREATE SCHEMA permission.

**Solution**: Grant permissions:
```sql
GRANT CREATE ON DATABASE docex TO postgres;
```

### Issue: Too many database connections

**Cause**: Many active tenants with open connections.

**Solution**: Close idle tenant connections:
```python
manager = TenantDatabaseManager()
manager.close_tenant_connection("tenant_id")
```

## Performance Considerations

1. **Connection Pooling**: Each tenant has its own connection pool (default: 5 connections)
2. **Schema Creation**: First access to a tenant creates schema (one-time overhead)
3. **Query Performance**: Queries are isolated per tenant, no cross-tenant filtering needed
4. **Scalability**: Can scale individual tenants independently

## Security Considerations

1. **Physical Isolation**: Data is physically separated (strongest isolation)
2. **No Cross-Tenant Access**: Impossible to query wrong tenant (database-level isolation)
3. **Compliance**: Meets requirements for HIPAA, GDPR, SOX
4. **Audit Trail**: All operations logged with tenant context

## Examples

See `examples/test_multi_tenancy.py` for complete working examples.

