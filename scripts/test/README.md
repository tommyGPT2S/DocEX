# Integration and Validation Test Scripts

This directory contains integration tests, validation scripts, and comprehensive test suites for DocEX.

## Test Scripts

### Core Integration Tests

- **`test_docex3_postgres.py`** - Comprehensive PostgreSQL integration tests including tenant provisioning, schema validation, and runtime usage
- **`test_docex3_simple.py`** - Simple DocEX 3.0 tests
- **`test_docex3_manual.py`** - Manual testing scripts

### Basket and Document Operations

- **`test_basket_file_operations.py`** - Comprehensive basket, file, and route operations including moving files between baskets
- **`test_docbasket_comprehensive.py`** - Comprehensive DocBasket method tests
- **`test_acme_corp_comprehensive.py`** - Comprehensive tests for acme_corp tenant

### Storage Tests

- **`test_storage_comparison.py`** - Compare filesystem vs S3 storage
- **`test_postgres_s3_paths.py`** - PostgreSQL with S3 path tests
- **`test_s3_*.py`** - Various S3-specific tests:
  - `test_s3_basket_subdirs.py` - S3 basket subdirectory tests
  - `test_s3_multi_tenant_comparison.py` - S3 multi-tenant comparison
  - `test_s3_quick.py` - Quick S3 tests
  - `test_s3_tenant_002.py` - S3 tenant tests
  - `test_s3_with_application_name.py` - S3 with application name

### Performance and Validation

- **`test_performance_improvements.py`** - Performance improvements validation
- **`test_release_validation.py`** - Release validation tests
- **`test_issue_36_fixes.py`** - Tests for GitHub Issue #36 fixes

### Initialization and Provisioning

- **`test_initialization_and_provisioning.py`** - Initialization and provisioning tests
- **`test_init_simple.py`** - Simple initialization tests
- **`init_docex_postgres_test.py`** - Initialize DocEX with PostgreSQL test database

### Utility and Helper Tests

- **`test_name_sanitization.py`** - Name sanitization tests
- **`test_id_centric_operations.py`** - ID-centric operation tests
- **`test_tenant_registry_fix.py`** - Tenant registry fix validation
- **`integrate_docex_platform.py`** - Platform integration example

## Running Tests

### From Project Root

```bash
# Run a specific test
python scripts/test/test_performance_improvements.py --tenant-id acme_corp --user-id test_user

# Run with verbose output
python scripts/test/test_basket_file_operations.py --tenant-id acme_corp --verbose
```

### From This Directory

```bash
cd scripts/test

# Run a specific test
python test_performance_improvements.py --tenant-id acme_corp --user-id test_user

# Run with verbose output
python test_basket_file_operations.py --tenant-id acme_corp --verbose
```

## Common Test Arguments

Most test scripts support these common arguments:

- `--tenant-id <tenant_id>` - Tenant ID for multi-tenant mode
- `--user-id <user_id>` - User ID (default: test_user)
- `--verbose` or `-v` - Verbose output
- `--db-type <type>` - Database type (postgresql, sqlite)
- `--skip-setup` - Skip DocEX setup (assume already initialized)

## Test Categories

### Unit Tests
Unit tests are located in the `tests/` directory and use pytest:
```bash
pytest tests/
```

### Integration Tests
Integration tests are in this directory (`scripts/test/`) and can be run directly:
```bash
python scripts/test/test_docex3_postgres.py
```

### Example Scripts
Example scripts demonstrating usage are in the `examples/` directory:
```bash
python examples/basic_usage.py
```

## Notes

- These scripts are integration/validation tests, not unit tests
- They may require database setup (PostgreSQL or SQLite)
- Some tests require S3 configuration (with mocking support via moto)
- Tests should be run in a virtual environment with all dependencies installed
- See `docs/Test_Scripts_Summary.md` (if available) for more details

