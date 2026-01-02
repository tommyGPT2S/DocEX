# DocEX Release Notes

## Version 2.8.0 (Pre-Release of 3.0)

**Release Date:** 2026-01-01

**⚠️ Important:** Version 2.8.0 is a **pre-release of DocEX 3.0** that introduces the new multi-tenancy architecture and tenant switching enforcement. This version includes breaking changes and new features that will be finalized in 3.0.

### 🎯 Major Features

#### Multi-Tenancy Architecture (DocEX 3.0 Preview)

- **Explicit Multi-Tenancy**: DocEX 3.0 introduces explicit, library-first multi-tenancy with strong isolation guarantees
- **Bootstrap Tenant**: System-owned tenant (`_docex_system_`) for metadata and provisioning
- **Tenant Provisioning**: Explicit, deterministic process for creating new tenants
- **Tenant Registry**: Centralized registry for all tenants with audit fields
- **Schema-per-Tenant**: PostgreSQL isolation strategy (database-per-tenant for SQLite)

#### Tenant Switching Enforcement

- **Strict Tenant Isolation**: Cannot switch tenants without explicitly closing database connections
- **Connection Management**: `DocEX.close()` and `DocEX.reset()` methods for proper connection cleanup
- **Error Prevention**: Clear error messages when attempting to switch tenants incorrectly

#### S3 Storage Improvements

- **Unified Path Resolution**: `DocEXPathResolver` for consistent path resolution across S3, filesystem, and database
- **Application-Level Namespace**: `app_name` configuration for better S3 organization
- **Tenant-Aware Prefixes**: Automatic tenant isolation in S3 paths
- **Removed One-Off Logic**: All path building now uses unified resolver

#### Configuration Management

- **Config-File-Only**: Configuration is now primarily file-based (`config.yaml`)
- **Runtime Parameters**: Only `tenant_id` is resolved at runtime
- **Explicit Resolvers**: `ConfigResolver` and `SchemaResolver` for explicit configuration resolution

### 🔧 Breaking Changes

1. **Tenant Switching**: Must call `docex.close()` or `docex.reset()` before switching tenants
2. **S3Storage API**: Removed `tenant_id` parameter from `_get_full_key()` - prefix must be pre-resolved
3. **Multi-Tenancy Required**: When `multi_tenancy.enabled: true`, `UserContext` with `tenant_id` is mandatory

### ✨ New Features

- `DocEX.close()` and `DocEX.reset()` methods for connection management
- `DocEX.is_properly_setup()` for comprehensive setup validation
- `TenantProvisioner` for explicit tenant creation
- `BootstrapTenantManager` for system initialization
- `DocEXPathResolver` for unified path resolution
- `ConfigResolver` for tenant-aware configuration resolution
- `SchemaResolver` for database schema resolution

### 📚 Documentation

- **Runtime Tenant Setup Guide**: Comprehensive guide for handling tenants at runtime
- **Tenant Switching Enforcement**: Detailed explanation of tenant switching rules
- **S3 Storage Path Resolution**: Design documentation for S3 path resolution
- **Prefix Preservation Explanation**: Details on the prefix preservation fix

### 🐛 Bug Fixes

- Fixed prefix preservation in `DocBasket.create()` hybrid format handler
- Fixed `DocEX` singleton tenant switching for v3.0 multi-tenancy
- Fixed PostgreSQL schema isolation for tenant databases
- Fixed S3 prefix duplication when using `ConfigResolver`

### ⚠️ Migration Notes

If upgrading from 2.7.x or earlier:

1. **Review Multi-Tenancy Configuration**: Update `config.yaml` to include `multi_tenancy` section if using v3.0 features
2. **Update Tenant Switching Code**: Add `docex.close()` calls before switching tenants
3. **Review S3 Storage Code**: Ensure S3 prefixes are pre-resolved using `ConfigResolver` or `DocEXPathResolver`
4. **Test Thoroughly**: This is a pre-release - test all multi-tenant operations before production use

### 🔮 What's Next (3.0)

- Finalization of multi-tenancy architecture
- Additional isolation strategies (row-level isolation)
- Enhanced audit and compliance features
- Performance optimizations
- Migration tools from v2.x to v3.0

### 📦 Installation

```bash
pip install docex==2.8.0
```

### 📖 Documentation

See `docs/Runtime_Tenant_Setup_Guide.md` for detailed information on using multi-tenancy features.

---

## Previous Releases

### Version 2.7.0

- Initial multi-tenancy foundation
- S3 storage improvements
- Configuration management enhancements

### Version 2.6.0

- Lightweight installation options
- Optimized dependencies
- Enhanced query performance with pagination and filtering

