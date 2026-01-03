# PostgreSQL Testing Setup

This document describes how to set up and run PostgreSQL integration tests for DocEX 3.0.

## Prerequisites

- Docker running on your local machine
- `docker-compose` installed
- Python virtual environment with dependencies installed

## Setup

1. **Start PostgreSQL container:**
   ```bash
   docker-compose -f docker-compose.test.yml up -d
   ```

2. **Verify PostgreSQL is running:**
   ```bash
   docker-compose -f docker-compose.test.yml ps
   ```

3. **Test connection:**
   ```bash
   python -c "import psycopg2; conn = psycopg2.connect(host='localhost', port=5433, database='docex_test', user='docex_test', password='docex_test_password'); print('✅ Connected'); conn.close()"
   ```

## Running Tests

The PostgreSQL integration tests are in `test_docex3_postgres.py`. However, there are some configuration issues that need to be resolved:

### Current Issues

1. **Config Validation**: The `DocEXConfig` class validates configuration when loading from file, which conflicts with test setup
2. **Tenant Registry Location**: The tenant registry table is being created in tenant schemas instead of only in the bootstrap schema

### Fixed Issues

1. ✅ **SSL Mode**: Changed from `require` to `prefer` to work with local Docker PostgreSQL
2. ✅ **Bootstrap Schema Resolution**: Bootstrap tenant now uses configured schema name (`docex_system`) instead of template (`tenant__docex_system_`)
3. ✅ **Schema Exclusion**: Tenant schemas now exclude `tenant_registry` table (it only exists in bootstrap schema)

## Cleanup

To clean up test data:

```bash
# Stop and remove containers
docker-compose -f docker-compose.test.yml down

# Remove volumes (deletes all data)
docker-compose -f docker-compose.test.yml down -v
```

## Database Connection Details

- **Host**: localhost
- **Port**: 5433 (to avoid conflict with local PostgreSQL on 5432)
- **Database**: docex_test
- **User**: docex_test
- **Password**: docex_test_password

## Schema Structure

- **Bootstrap Schema**: `docex_system` (contains tenant_registry table)
- **Tenant Schemas**: `tenant_{tenant_id}` (e.g., `tenant_acme`, `tenant_contoso`)

## Next Steps

To complete PostgreSQL testing:

1. Fix config validation in test setup
2. Ensure tenant registry is only created in bootstrap schema
3. Verify all tests pass with PostgreSQL

