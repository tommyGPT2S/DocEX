# Tenant Provisioning Guide

This guide explains how to provision (create) a new tenant in DocEX with database-level multi-tenancy.

## Overview

When database-level multi-tenancy is enabled, each tenant gets its own isolated:
- **PostgreSQL**: Separate schema (e.g., `tenant_acme_corp`)
- **SQLite**: Separate database file (e.g., `storage/tenant_acme_corp/docex.db`)

## Prerequisites

1. **PostgreSQL is running** (if using PostgreSQL)
   ```bash
   docker-compose up -d postgres
   ```

2. **DocEX is configured** for PostgreSQL
   ```python
   from docex import DocEX
   
   DocEX.setup(
       database={
           'type': 'postgres',
           'postgres': {
               'host': 'localhost',
               'port': 5432,
               'database': 'docex_db',
               'user': 'docex',
               'password': 'docex_password'
           }
       }
   )
   ```

3. **Multi-tenancy is enabled** in configuration

## Provisioning Methods

### Method 1: Using CLI Command (Recommended)

```bash
# Provision a tenant
docex provision-tenant --tenant-id acme-corp

# Provision with verification (creates test basket)
docex provision-tenant --tenant-id acme-corp --verify

# Enable multi-tenancy and provision
docex provision-tenant --tenant-id acme-corp --enable-multi-tenancy
```

### Method 2: Using Python Script

```bash
# Provision a tenant
python scripts/provision_tenant.py --tenant-id acme-corp

# Provision with verification
python scripts/provision_tenant.py --tenant-id acme-corp --verify

# Enable multi-tenancy and provision
python scripts/provision_tenant.py --tenant-id acme-corp --enable-multi-tenancy
```

### Method 3: Automatic Provisioning (On First Access)

Tenants are automatically created when first accessed if multi-tenancy is enabled:

```python
from docex import DocEX
from docex.context import UserContext

# First access automatically creates tenant schema/database
user_context = UserContext(user_id="user1", tenant_id="acme-corp")
docex = DocEX(user_context=user_context)

# This will automatically provision the tenant if it doesn't exist
basket = docex.create_basket("my_basket")
```

## Configuration

### Enable Multi-Tenancy

If multi-tenancy is not enabled, you can enable it:

#### Option 1: Using CLI

```bash
docex provision-tenant --tenant-id test --enable-multi-tenancy
```

#### Option 2: Manual Configuration

Edit `~/.docex/config.yaml`:

```yaml
security:
  multi_tenancy_model: database_level
  tenant_database_routing: true

database:
  type: postgres
  postgres:
    host: localhost
    port: 5432
    database: docex_db
    user: docex
    password: docex_password
    schema_template: "tenant_{tenant_id}"  # Optional: customize schema name pattern
```

### Schema Name Pattern

For PostgreSQL, you can customize the schema name pattern:

```yaml
database:
  postgres:
    schema_template: "tenant_{tenant_id}"  # Default: tenant_acme-corp
    # Or custom:
    # schema_template: "acme_{tenant_id}"  # Result: acme_acme-corp
```

## What Gets Created

When you provision a tenant, the following is created:

### PostgreSQL

1. **Schema**: `tenant_{tenant_id}` (e.g., `tenant_acme-corp`)
2. **All Tables**:
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
3. **All Indexes**: Performance indexes from `schema.sql`

### SQLite

1. **Database File**: `storage/tenant_{tenant_id}/docex.db`
2. **All Tables**: Same as PostgreSQL
3. **All Indexes**: Same as PostgreSQL

## Verification

### Verify Tenant Exists (PostgreSQL)

```bash
# Connect to database
docker exec -it docex-postgres psql -U docex -d docex_db

# List all tenant schemas
\dn tenant_*

# Or query
SELECT schema_name 
FROM information_schema.schemata 
WHERE schema_name LIKE 'tenant_%';

# Check tables in tenant schema
\dt tenant_acme-corp.*
```

### Verify Tenant Exists (SQLite)

```bash
# Check if database file exists
ls -la storage/tenant_acme-corp/docex.db

# Or using sqlite3
sqlite3 storage/tenant_acme-corp/docex.db ".tables"
```

### Verify Using DocEX

```python
from docex import DocEX
from docex.context import UserContext

user_context = UserContext(user_id="test", tenant_id="acme-corp")
docex = DocEX(user_context=user_context)

# Create a test basket
basket = docex.create_basket("test_basket")
print(f"✅ Tenant verified! Basket ID: {basket.id}")

# List baskets
baskets = docex.list_baskets()
print(f"✅ Tenant has {len(baskets)} basket(s)")
```

## Usage After Provisioning

Once a tenant is provisioned, use it like this:

```python
from docex import DocEX
from docex.context import UserContext

# Create user context with tenant_id
user_context = UserContext(
    user_id="alice",
    user_email="alice@acme-corp.com",
    tenant_id="acme-corp",
    roles=["admin"]
)

# Initialize DocEX with tenant context
docex = DocEX(user_context=user_context)

# All operations automatically use tenant's isolated database/schema
basket = docex.create_basket("invoices")
document = basket.add("invoice.pdf")

# Only this tenant's data is accessible
baskets = docex.list_baskets()  # Only acme-corp baskets
```

## Multiple Tenants

You can provision multiple tenants:

```bash
# Provision multiple tenants
docex provision-tenant --tenant-id acme-corp
docex provision-tenant --tenant-id globex-corp
docex provision-tenant --tenant-id initech-corp
```

Each tenant is completely isolated:

```python
# Tenant 1
user_context1 = UserContext(user_id="alice", tenant_id="acme-corp")
docex1 = DocEX(user_context=user_context1)
basket1 = docex1.create_basket("invoices")

# Tenant 2 (completely isolated)
user_context2 = UserContext(user_id="bob", tenant_id="globex-corp")
docex2 = DocEX(user_context=user_context2)
basket2 = docex2.create_basket("invoices")

# Each tenant only sees their own data
baskets1 = docex1.list_baskets()  # Only acme-corp baskets
baskets2 = docex2.list_baskets()  # Only globex-corp baskets
```

## Troubleshooting

### Error: Multi-tenancy not enabled

**Solution**: Enable multi-tenancy:
```bash
docex provision-tenant --tenant-id test --enable-multi-tenancy
```

### Error: Tenant already exists

**Solution**: The tenant schema/database already exists. You can:
1. Use the existing tenant
2. Drop and recreate (will lose data):
   ```bash
   # For PostgreSQL
   docker exec -it docex-postgres psql -U docex -d docex_db -c "DROP SCHEMA IF EXISTS tenant_acme-corp CASCADE;"
   
   # Then provision again
   docex provision-tenant --tenant-id acme-corp
   ```

### Error: Connection refused

**Solution**: Ensure PostgreSQL is running:
```bash
docker-compose ps
docker-compose up -d postgres
```

### Error: Permission denied

**Solution**: Check database user permissions:
```sql
-- Grant schema creation permission
GRANT CREATE ON DATABASE docex_db TO docex;
```

## Best Practices

1. **Use meaningful tenant IDs**: Use company names or identifiers (e.g., `acme-corp`, `customer-123`)

2. **Provision before use**: Explicitly provision tenants for better control:
   ```bash
   docex provision-tenant --tenant-id acme-corp --verify
   ```

3. **Verify after provisioning**: Always verify tenant works:
   ```bash
   docex provision-tenant --tenant-id acme-corp --verify
   ```

4. **Monitor tenant schemas**: Regularly check tenant schemas:
   ```sql
   SELECT schema_name, 
          (SELECT COUNT(*) FROM information_schema.tables 
           WHERE table_schema = schema_name) as table_count
   FROM information_schema.schemata 
   WHERE schema_name LIKE 'tenant_%';
   ```

5. **Backup per tenant**: Backup each tenant separately:
   ```bash
   # PostgreSQL
   pg_dump -h localhost -U docex -d docex_db -n tenant_acme-corp > acme-corp_backup.sql
   
   # SQLite
   cp storage/tenant_acme-corp/docex.db acme-corp_backup.db
   ```

## Next Steps

1. ✅ Provision your first tenant
2. ✅ Verify it works
3. ✅ Start using it in your application
4. ✅ Provision additional tenants as needed

For more information, see:
- [Multi-Tenancy Guide](MULTI_TENANCY_GUIDE.md)
- [Docker Setup](DOCKER_SETUP.md)
- [Document Query Optimizations](DOCUMENT_QUERY_OPTIMIZATIONS.md)

