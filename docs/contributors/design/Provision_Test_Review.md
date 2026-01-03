# Tenant Provisioning Test Review

This document reviews existing tenant provisioning tests and provides recommendations for a comprehensive provisioning test.

## Existing Test Scripts

### 1. `test_docex3_integration.py` - `test_tenant_provisioning()`

**Location:** Lines 100-177

**Strengths:**
- ✅ Tests basic provisioning flow
- ✅ Tests duplicate tenant rejection (`TenantExistsError`)
- ✅ Tests multiple tenant creation
- ✅ Uses SQLite (fast, no external dependencies)
- ✅ Clear step-by-step output

**Weaknesses:**
- ❌ Doesn't validate tenant schema/database was actually created
- ❌ Doesn't test tenant ID validation (invalid IDs, reserved IDs)
- ❌ Doesn't verify tenant can be used after provisioning
- ❌ Doesn't test error handling (partial provisioning cleanup)
- ❌ Doesn't verify tenant registry entry details

**Test Coverage:**
- Basic provisioning: ✅
- Duplicate prevention: ✅
- Multiple tenants: ✅
- Schema validation: ❌
- Error handling: ❌
- Tenant usage: ❌

---

### 2. `test_docex3_postgres.py` - `test_tenant_provisioning_postgres()`

**Location:** Lines 137-235

**Strengths:**
- ✅ Tests PostgreSQL provisioning (schema isolation)
- ✅ Handles existing tenants gracefully (idempotent)
- ✅ Validates schema name in registry
- ✅ Uses docker-compose.test.yml database
- ✅ Tests duplicate tenant rejection

**Weaknesses:**
- ❌ Doesn't verify schema actually exists in PostgreSQL
- ❌ Doesn't verify tables were created in tenant schema
- ❌ Doesn't test tenant ID validation
- ❌ Doesn't verify tenant can be used after provisioning
- ❌ Doesn't test error scenarios

**Test Coverage:**
- Basic provisioning: ✅
- Duplicate prevention: ✅
- Multiple tenants: ✅
- Schema validation: ⚠️ (partial - checks registry, not actual schema)
- Error handling: ❌
- Tenant usage: ❌

---

### 3. `test_docex3_s3_multitenant.py` - Provisioning Section

**Location:** Lines 270-295

**Strengths:**
- ✅ Tests provisioning with S3 storage
- ✅ Handles existing tenants gracefully
- ✅ Tests multiple tenants
- ✅ Integrates with S3 storage configuration

**Weaknesses:**
- ❌ Very minimal - only checks if tenant exists before creating
- ❌ Doesn't validate provisioning details
- ❌ Doesn't test error cases
- ❌ Doesn't verify tenant can be used

**Test Coverage:**
- Basic provisioning: ✅
- Duplicate prevention: ⚠️ (implicit, not explicit)
- Multiple tenants: ✅
- Schema validation: ❌
- Error handling: ❌
- Tenant usage: ⚠️ (tested later, but not in provisioning section)

---

## Recommended Comprehensive Provision Test

Based on the review, here's a recommended comprehensive provisioning test that covers all important scenarios:

### Test Structure

```python
def test_comprehensive_tenant_provisioning():
    """
    Comprehensive tenant provisioning test covering:
    1. Basic provisioning (SQLite and PostgreSQL)
    2. Tenant ID validation
    3. Duplicate prevention
    4. Schema/database creation verification
    5. Tenant registry validation
    6. Error handling and cleanup
    7. Post-provisioning usage verification
    """
```

### Test Cases to Include

#### 1. **Basic Provisioning**
- ✅ Create tenant with valid ID
- ✅ Verify tenant registry entry
- ✅ Verify isolation boundary created (schema/database)
- ✅ Verify tables created in tenant schema/database

#### 2. **Tenant ID Validation**
- ✅ Reject invalid tenant IDs (empty, None, special characters)
- ✅ Reject reserved tenant IDs (`_docex_system_`, etc.)
- ✅ Accept valid tenant IDs (alphanumeric, underscores, hyphens)

#### 3. **Duplicate Prevention**
- ✅ Reject duplicate tenant ID
- ✅ Verify `TenantExistsError` is raised
- ✅ Verify no partial provisioning occurred

#### 4. **Schema/Database Verification**
- ✅ **SQLite**: Verify database file exists at correct path
- ✅ **PostgreSQL**: Verify schema exists in database
- ✅ Verify tables exist in tenant schema/database
- ✅ Verify tenant_registry table NOT in tenant schema (only in bootstrap)

#### 5. **Tenant Registry Validation**
- ✅ Verify all fields populated correctly
- ✅ Verify `is_system=False` for business tenants
- ✅ Verify `created_at` and `created_by` are set
- ✅ Verify `isolation_strategy` matches config

#### 6. **Error Handling**
- ✅ Test provisioning failure scenarios
- ✅ Verify partial provisioning cleanup
- ✅ Test database connection failures
- ✅ Test permission errors

#### 7. **Post-Provisioning Usage**
- ✅ Create DocEX instance with provisioned tenant
- ✅ Create basket in provisioned tenant
- ✅ Add document to basket
- ✅ Verify data isolation (tenant can't access other tenant's data)

#### 8. **Multiple Tenants**
- ✅ Provision multiple tenants
- ✅ Verify each tenant has separate isolation boundary
- ✅ Verify tenants can't access each other's data

---

## Recommended Test Implementation

### For SQLite (Fast, No Dependencies)

```python
def test_comprehensive_provisioning_sqlite():
    """Comprehensive provisioning test for SQLite"""
    # 1. Setup
    # 2. Basic provisioning
    # 3. Validation checks
    # 4. Duplicate prevention
    # 5. Multiple tenants
    # 6. Post-provisioning usage
    # 7. Error scenarios
```

### For PostgreSQL (Production-Like)

```python
def test_comprehensive_provisioning_postgres():
    """Comprehensive provisioning test for PostgreSQL"""
    # Same structure as SQLite but with:
    # - Schema verification (not database file)
    # - PostgreSQL-specific error handling
    # - Connection to docker-compose.test.yml database
```

---

## Key Improvements Needed

### 1. **Schema/Database Verification**

**Current:** Tests only check tenant registry entry exists

**Recommended:** Verify actual schema/database was created:

```python
# PostgreSQL
from sqlalchemy import inspect
inspector = inspect(engine)
schemas = inspector.get_schema_names()
assert 'tenant_acme' in schemas

# SQLite
assert Path(tenant_registry.database_path).exists()
```

### 2. **Table Verification**

**Current:** No verification that tables exist in tenant schema

**Recommended:** Verify all required tables exist:

```python
# Switch to tenant schema and verify tables
with engine.connect() as conn:
    conn.execute(text(f"SET search_path TO tenant_acme"))
    tables = inspector.get_table_names()
    assert 'docbasket' in tables
    assert 'document' in tables
    # etc.
```

### 3. **Tenant ID Validation**

**Current:** Not tested

**Recommended:** Test invalid tenant IDs:

```python
# Test invalid tenant IDs
invalid_ids = ['', None, '_docex_system_', 'tenant with spaces', 'tenant@invalid']
for invalid_id in invalid_ids:
    with pytest.raises(InvalidTenantIdError):
        provisioner.create(tenant_id=invalid_id, ...)
```

### 4. **Post-Provisioning Usage**

**Current:** Not tested in provisioning test

**Recommended:** Verify tenant can be used:

```python
# After provisioning, verify tenant can be used
user_context = UserContext(user_id='test_user', tenant_id='acme')
docex = DocEX(user_context=user_context)
basket = docex.create_basket('test_basket')
# Verify basket was created in tenant's schema
```

### 5. **Error Handling**

**Current:** Not tested

**Recommended:** Test error scenarios:

```python
# Test partial provisioning cleanup
# Mock a failure during schema creation
# Verify cleanup occurred
```

---

## Best Test Script Recommendation

**For a good provision test, I recommend using `test_docex3_postgres.py` as a base** because:

1. ✅ Uses PostgreSQL (production-like)
2. ✅ Handles existing tenants gracefully
3. ✅ Tests with docker-compose.test.yml database
4. ✅ Validates schema name in registry
5. ✅ Tests duplicate prevention

**But enhance it with:**

1. ✅ Schema existence verification
2. ✅ Table existence verification
3. ✅ Tenant ID validation tests
4. ✅ Post-provisioning usage verification
5. ✅ Error handling tests

---

## Example Enhanced Test

Here's an example of how to enhance the existing test:

```python
def test_comprehensive_tenant_provisioning_postgres():
    """Comprehensive tenant provisioning test with PostgreSQL"""
    
    # 1. Setup (existing)
    # ... setup code ...
    
    # 2. Basic Provisioning
    tenant_registry = provisioner.create(
        tenant_id='acme',
        display_name='Acme Corporation',
        created_by='test_user'
    )
    
    # 3. Verify Schema Exists
    from sqlalchemy import inspect, text
    bootstrap_db = Database(config=config, tenant_id='_docex_system_')
    engine = bootstrap_db.get_engine()
    inspector = inspect(engine)
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name = 'tenant_acme'
        """))
        assert result.fetchone() is not None, "Schema 'tenant_acme' should exist"
    
    # 4. Verify Tables Exist in Tenant Schema
    tenant_db = Database(config=config, tenant_id='acme')
    tenant_engine = tenant_db.get_engine()
    tenant_inspector = inspect(tenant_engine)
    tables = tenant_inspector.get_table_names()
    
    required_tables = ['docbasket', 'document', 'document_metadata']
    for table in required_tables:
        assert table in tables, f"Table '{table}' should exist in tenant schema"
    
    # 5. Verify tenant_registry NOT in tenant schema
    assert 'tenant_registry' not in tables, "tenant_registry should NOT be in tenant schema"
    
    # 6. Verify Tenant Can Be Used
    from docex import DocEX
    from docex.context import UserContext
    
    user_context = UserContext(user_id='test_user', tenant_id='acme')
    docex = DocEX(user_context=user_context)
    basket = docex.create_basket('test_basket')
    assert basket is not None, "Should be able to create basket in provisioned tenant"
    
    # 7. Test Duplicate Prevention
    with pytest.raises(TenantExistsError):
        provisioner.create(tenant_id='acme', ...)
    
    # 8. Test Invalid Tenant IDs
    from docex.provisioning.tenant_provisioner import InvalidTenantIdError
    
    invalid_ids = ['_docex_system_', '', 'tenant with spaces']
    for invalid_id in invalid_ids:
        with pytest.raises(InvalidTenantIdError):
            provisioner.create(tenant_id=invalid_id, ...)
```

---

## Summary

**Best Existing Test:** `test_docex3_postgres.py` - `test_tenant_provisioning_postgres()`

**Why:**
- Uses PostgreSQL (production-like)
- Handles existing tenants
- Tests duplicate prevention
- Uses docker-compose.test.yml database

**Enhancements Needed:**
1. Schema existence verification
2. Table existence verification
3. Tenant ID validation
4. Post-provisioning usage verification
5. Error handling tests

**Recommendation:** Use `test_docex3_postgres.py` as the base and enhance it with the improvements listed above for a comprehensive provisioning test.

