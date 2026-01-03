# DocEX 3.0 Design Review

**Review Date:** 2026-01-01  
**Reviewer:** AI Assistant  
**Status:** Review Complete

---

## Executive Summary

The proposed DocEX 3.0 multi-tenancy architecture is **well-designed and aligns with best practices** for secure, library-first document execution engines. The design correctly prioritizes **explicitness over convenience** and establishes clear security boundaries.

**Overall Assessment:** ✅ **APPROVED with Recommendations**

The design is sound, but several implementation details and migration considerations need clarification before proceeding.

---

## 1. Strengths of the Design

### 1.1 Clear Separation of Concerns
- ✅ **System Bootstrap** vs **Tenant Provisioning** vs **Runtime Execution** are well-separated
- ✅ **Bootstrap tenant** concept provides clean system metadata ownership
- ✅ **No implicit behaviors** - all boundaries are explicit

### 1.2 Security-First Approach
- ✅ **Fail-fast** on missing tenant context
- ✅ **No cross-tenant access** by design
- ✅ **Explicit UserContext** requirement prevents accidental leaks

### 1.3 Library-First Philosophy
- ✅ No global state assumptions
- ✅ No middleware coupling
- ✅ Embeddable in various contexts (SaaS, tools, agents)

### 1.4 PostgreSQL & SQLite Limitation
- ✅ **Appropriate scope** for v3.0 initial release
- ✅ Both databases support schema-level isolation well
- ✅ Reduces complexity and maintenance burden

---

## 2. Alignment with Current Codebase

### 2.1 Existing Multi-Tenancy Support

**Current State:**
- ✅ `TenantDatabaseManager` exists and handles schema-per-tenant (PostgreSQL) and database-per-tenant (SQLite)
- ✅ `UserContext` class exists with `tenant_id` field
- ✅ Database-level isolation is already implemented

**Gap Analysis:**
- ❌ **Lazy tenant creation** - schemas/databases are auto-created on first access
- ❌ **No bootstrap tenant** - system metadata lives in default schema/database
- ❌ **No tenant registry** - no central record of provisioned tenants
- ❌ **No explicit provisioning API** - `TenantProvisioner` doesn't exist
- ⚠️ **Optional tenant_id** - UserContext allows `tenant_id=None`

### 2.2 Configuration Management

**Current State:**
- ✅ Configuration in `~/.docex/config.yaml` or `default_config.yaml`
- ✅ `DocEXConfig` singleton manages configuration
- ✅ Supports both SQLite and PostgreSQL

**Gap Analysis:**
- ❌ **No `config_version` field** - versioning not implemented
- ❌ **No `docex.yaml` in project root** - design proposes canonical config file
- ⚠️ **Multi-tenancy config** exists but uses different structure than proposed

**Current Config Structure:**
```yaml
security:
  multi_tenancy_model: database_level
  tenant_database_routing: true
```

**Proposed Config Structure:**
```yaml
config_version: 1
multi_tenancy:
  enabled: true
  isolation_strategy: schema
  bootstrap_tenant:
    id: system
    schema: docex_system
```

**Recommendation:** Need migration path for existing configs.

### 2.3 Initialization Process

**Current State:**
- ✅ `docex init` CLI command exists
- ✅ Creates database and tables
- ✅ Validates storage connectivity

**Gap Analysis:**
- ❌ **No bootstrap tenant creation** in init
- ❌ **No tenant registry initialization**
- ⚠️ **Schema creation happens lazily** - needs to be explicit

---

## 3. Critical Gaps & Concerns

### 3.1 Bootstrap Tenant Implementation

**Issue:** The design requires a bootstrap tenant for system metadata, but:
- No tenant registry table/model exists
- No clear definition of what "system metadata" includes
- No enforcement that bootstrap tenant is never used for business operations

**Recommendations:**
1. **Define Tenant Registry Schema:**
   ```sql
   CREATE TABLE tenant_registry (
       tenant_id VARCHAR(255) PRIMARY KEY,
       display_name VARCHAR(255) NOT NULL,
       is_system BOOLEAN NOT NULL DEFAULT FALSE,
       isolation_strategy VARCHAR(50) NOT NULL,  -- 'schema' or 'database'
       schema_name VARCHAR(255),  -- For PostgreSQL
       database_path VARCHAR(500),  -- For SQLite
       
       -- Standard audit fields
       created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
       created_by VARCHAR(255) NOT NULL,
       last_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
       last_updated_by VARCHAR(255)
   );
   ```
   
   **Note:** See `Tenant_Registry_Schema.md` for complete schema definition with SQLAlchemy model and usage examples.

2. **Bootstrap Tenant Rules:**
   - Must be created during `docex init`
   - Must have `is_system = true`
   - Must be stored in tenant registry
   - Runtime operations should reject UserContext with bootstrap tenant_id

3. **System Metadata Scope:**
   - Tenant registry itself
   - Processor registry (if global)
   - System-level configuration
   - Audit logs (if cross-tenant)

### 3.2 Tenant Provisioning API

**Issue:** `TenantProvisioner.create()` is proposed but not defined.

**Recommendations:**
1. **Create `docex/provisioning/tenant_provisioner.py`:**
   ```python
   class TenantProvisioner:
       @staticmethod
       def create(
           tenant_id: str,
           display_name: str,
           isolation_strategy: str = "schema"
       ) -> Tenant:
           """
           Provision a new tenant.
           
           Raises:
               TenantExistsError: If tenant_id already exists
               ProvisioningError: If provisioning fails
           """
   ```

2. **Provisioning Steps:**
   - Validate tenant_id uniqueness (check registry)
   - Create isolation boundary (schema or database)
   - Initialize schema (create all tables)
   - Register tenant in tenant registry
   - Return Tenant object

3. **Idempotency:**
   - Should be idempotent (check if exists first)
   - Or fail-fast on conflict (as design states)

### 3.3 UserContext Enforcement

**Issue:** Current `UserContext` allows `tenant_id=None`, but design requires it when multi-tenancy is enabled.

**Recommendations:**
1. **Add validation to DocEX.__init__():**
   ```python
   def __init__(self, user_context: Optional[UserContext] = None):
       config = DocEXConfig()
       multi_tenancy_enabled = config.get('multi_tenancy.enabled', False)
       
       if multi_tenancy_enabled:
           if not user_context:
               raise ValueError("UserContext required when multi-tenancy is enabled")
           if not user_context.tenant_id:
               raise ValueError("tenant_id required in UserContext when multi-tenancy is enabled")
   ```

2. **Validate tenant exists:**
   - Check tenant registry on initialization
   - Reject bootstrap tenant for business operations

### 3.4 Configuration File Location

**Issue:** Design proposes `docex.yaml` in project root, but current code uses `~/.docex/config.yaml`.

**Recommendations:**
1. **Support both locations** (for backward compatibility):
   - Check `./docex.yaml` first (project-scoped)
   - Fall back to `~/.docex/config.yaml` (user-scoped)
   - Environment variable override: `DOCEX_CONFIG_PATH`

2. **Migration Strategy:**
   - v3.0 can read both formats
   - `docex init` creates `docex.yaml` in current directory
   - Document migration path for existing users

### 3.5 SQLite Schema Isolation

**Issue:** SQLite doesn't support schemas like PostgreSQL. Current implementation uses separate database files per tenant.

**Clarification Needed:**
- Design mentions "schema-per-tenant" as default
- For SQLite, this means "database-per-tenant" (separate .db files)
- Need to clarify terminology in docs

**Recommendation:**
- Use term "isolation boundary" instead of "schema"
- Document that:
  - PostgreSQL: schema-per-tenant
  - SQLite: database-per-tenant (separate files)

---

## 4. Implementation Recommendations

### 4.1 Phase 1: Foundation (Week 1-2)

1. **Create Tenant Registry:**
   - Add `TenantRegistry` model to `docex/db/models.py`
   - Create migration script
   - Store in bootstrap tenant schema

2. **Implement Bootstrap Tenant:**
   - Create bootstrap tenant during `docex init`
   - Store in tenant registry with `is_system=true`
   - Use bootstrap tenant for system metadata

3. **Update Configuration:**
   - Add `config_version` field
   - Add `multi_tenancy` section with new structure
   - Maintain backward compatibility

### 4.2 Phase 2: Provisioning (Week 2-3)

1. **Create TenantProvisioner:**
   - Implement `create()` method
   - Support PostgreSQL (schema) and SQLite (database file)
   - Register in tenant registry
   - Validate uniqueness

2. **Update `docex init`:**
   - Create bootstrap tenant
   - Initialize tenant registry
   - Validate storage connectivity

3. **Add CLI Command:**
   ```bash
   docex tenant create --tenant-id acme --display-name "Acme Corp"
   ```

### 4.3 Phase 3: Runtime Enforcement (Week 3-4)

1. **Enforce UserContext:**
   - Require UserContext when multi-tenancy enabled
   - Validate tenant_id exists in registry
   - Reject bootstrap tenant for business ops

2. **Update Database Access:**
   - Remove lazy tenant creation
   - Fail-fast if tenant not provisioned
   - Use tenant registry to resolve isolation boundary

3. **Update TenantDatabaseManager:**
   - Check tenant registry before creating engine
   - Remove auto-creation logic
   - Use explicit provisioning

### 4.4 Phase 4: Migration & Testing (Week 4-5)

1. **Migration Script:**
   - Convert existing v2.x configs to v3.0 format
   - Migrate existing tenant schemas to tenant registry
   - Create bootstrap tenant from existing system data

2. **Testing:**
   - Unit tests for provisioning
   - Integration tests for multi-tenant isolation
   - Migration tests for v2.x → v3.0

---

## 5. PostgreSQL & SQLite Considerations

### 5.1 PostgreSQL Schema Isolation

**Current Implementation:** ✅ Already supports schema-per-tenant

**Recommendations:**
- Use `search_path` setting (already implemented)
- Ensure ENUM types are schema-qualified (already handled)
- Use quoted identifiers for schema names (handles special chars)

**No changes needed** - current implementation is solid.

### 5.2 SQLite Database Isolation

**Current Implementation:** ✅ Already supports database-per-tenant

**Recommendations:**
- Use path templates: `storage/tenant_{tenant_id}/docex.db`
- Ensure directory permissions are correct
- Handle concurrent access (already using connection pooling)

**No changes needed** - current implementation is solid.

### 5.3 Limitation Scope

**Question:** Should we support other databases in the future?

**Recommendation:**
- ✅ **Limit to PostgreSQL and SQLite for v3.0**
- Document that other databases can be added via isolation strategy plugins
- Keep database factory extensible for future additions

---

## 6. Migration Path from v2.x

### 6.1 Breaking Changes

**Required Changes for Users:**
1. Run `docex init` to create bootstrap tenant
2. Provision existing tenants explicitly:
   ```python
   # For each existing tenant
   TenantProvisioner.create(
       tenant_id="existing_tenant",
       display_name="Existing Tenant"
   )
   ```
3. Update code to pass UserContext:
   ```python
   # v2.x (deprecated)
   doc_ex = DocEX()
   
   # v3.0 (required)
   user_context = UserContext(
       user_id="u123",
       tenant_id="acme",
       roles=["user"]
   )
   doc_ex = DocEX(user_context=user_context)
   ```

### 6.2 Migration Script

**Recommendation:** Create `docex migrate-v2-to-v3` command:

```python
@cli.command()
def migrate_v2_to_v3():
    """
    Migrate from DocEX v2.x to v3.0
    
    Steps:
    1. Detect existing tenant schemas/databases
    2. Create bootstrap tenant
    3. Register existing tenants in tenant registry
    4. Convert configuration format
    5. Validate migration
    """
```

### 6.3 Backward Compatibility

**Recommendation:**
- v2.x code should continue working (with deprecation warnings)
- Provide opt-in flag: `multi_tenancy.enabled: false` for single-tenant mode
- Document deprecation timeline (remove in v4.0)

---

## 7. Open Questions from RFC

### 7.1 Tenant Deletion

**RFC Question:** "Should tenant deletion be supported?"

**Recommendation:**
- ✅ **Yes, but with safeguards:**
  - Soft delete (mark as deleted, don't remove data)
  - Require explicit confirmation
  - Archive tenant data before deletion
  - Provide `docex tenant delete --tenant-id X --confirm`

### 7.2 System Tenant Configuration

**RFC Question:** "Should system tenant be configurable?"

**Recommendation:**
- ⚠️ **Partially configurable:**
  - Tenant ID should be configurable (default: "system")
  - Schema/database path should be configurable
  - `is_system` flag should NOT be configurable (always true)
  - Display name should be configurable (default: "System")

---

## 8. Documentation Needs

### 8.1 Required Documentation

1. **Migration Guide:**
   - Step-by-step v2.x → v3.0 migration
   - Code examples for common scenarios
   - Troubleshooting common issues

2. **Provisioning Guide:**
   - How to provision tenants
   - Best practices for tenant IDs
   - Isolation strategy selection

3. **Security Guide:**
   - Tenant isolation guarantees
   - UserContext best practices
   - Audit and compliance considerations

4. **API Reference:**
   - TenantProvisioner API
   - UserContext API
   - Configuration reference

### 8.2 Code Examples

**Recommendation:** Add to `examples/`:
- `examples/multi_tenant_basic.py`
- `examples/tenant_provisioning.py`
- `examples/migration_v2_to_v3.py`

---

## 9. Testing Strategy

### 9.1 Unit Tests

- TenantProvisioner.create()
- Tenant registry operations
- UserContext validation
- Configuration migration

### 9.2 Integration Tests

- Multi-tenant isolation (PostgreSQL)
- Multi-tenant isolation (SQLite)
- Bootstrap tenant operations
- Cross-tenant access prevention

### 9.3 Migration Tests

- v2.x → v3.0 migration
- Config format conversion
- Existing tenant registration

---

## 10. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Breaking changes for v2.x users | High | Clear migration guide, deprecation warnings |
| Tenant registry corruption | Medium | Backup before provisioning, transaction safety |
| Performance impact of tenant registry lookups | Low | Cache tenant registry, index tenant_id |
| SQLite concurrent access issues | Low | Already handled with connection pooling |
| Configuration migration failures | Medium | Validation, rollback capability |

---

## 11. Final Recommendations

### 11.1 Proceed with Implementation

✅ **The design is sound and ready for implementation.**

### 11.2 Priority Actions

1. **Immediate (Before Implementation):**
   - Define tenant registry schema
   - Clarify SQLite terminology (schema vs database)
   - Create detailed migration plan

2. **During Implementation:**
   - Implement bootstrap tenant first
   - Add tenant registry
   - Create TenantProvisioner
   - Update runtime enforcement

3. **Before Release:**
   - Complete migration script
   - Write comprehensive documentation
   - Test migration from v2.x
   - Performance testing

### 11.3 Success Criteria

- ✅ All tenants must be explicitly provisioned
- ✅ Bootstrap tenant created during init
- ✅ UserContext required when multi-tenancy enabled
- ✅ No lazy tenant creation
- ✅ Clear migration path from v2.x
- ✅ Full test coverage for provisioning and isolation

---

## 12. Conclusion

The DocEX 3.0 multi-tenancy design is **well-architected and ready for implementation**. The focus on explicitness, security, and library-first principles aligns perfectly with DocEX's goals.

**Key Strengths:**
- Clear separation of concerns
- Security-first approach
- Appropriate scope (PostgreSQL + SQLite)

**Key Actions:**
- Implement tenant registry and bootstrap tenant
- Create TenantProvisioner API
- Enforce UserContext at runtime
- Provide migration path from v2.x

**Recommendation:** ✅ **Proceed with implementation following the phased approach outlined above.**

---

**Next Steps:**
1. Review this document with the team
2. Address open questions (tenant deletion, system tenant config)
3. Create detailed implementation plan
4. Begin Phase 1 implementation

