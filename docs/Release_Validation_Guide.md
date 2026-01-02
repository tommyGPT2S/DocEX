# Release Validation Guide

This guide explains how to validate a DocEX release to ensure it's properly set up and ready for use.

## Key Feature: Respects Existing Initialization

**The validation script respects your existing DocEX setup:**
- If DocEX is already initialized, it validates against the current configuration
- If DocEX is not initialized, it initializes with provided settings and then validates
- This allows you to validate your production setup without creating a new one

## Quick Start

Run the validation script:

```bash
# Validate existing DocEX setup (recommended)
python test_release_validation.py

# Validate with specific tenant
python test_release_validation.py --tenant-id acme_corp

# Initialize and validate new setup (only if not already initialized)
python test_release_validation.py --db-type postgresql --db-host localhost --db-name docex_test --db-user postgres --db-password your_password

# With S3 storage (only used if initializing)
python test_release_validation.py --storage-type s3 --s3-bucket my-bucket --s3-region us-east-1
```

## What Was Fixed

### 1. `is_properly_setup()` Now Returns Error Messages

**Before:**
- Only returned `True` or `False`
- Errors were logged at debug level only
- No way to know what was wrong

**After:**
- Added `get_setup_errors()` method that returns detailed error messages
- `is_properly_setup()` now uses `get_setup_errors()` internally
- All errors are clearly reported

**Usage:**
```python
from docex import DocEX

# Check if properly set up
if DocEX.is_properly_setup():
    print("✅ DocEX is ready")
else:
    # Get detailed error messages
    errors = DocEX.get_setup_errors()
    for error in errors:
        print(f"❌ {error}")
```

### 2. Fixed Multi-Tenancy Database Check

**Before:**
- `is_properly_setup()` always checked the default database
- For multi-tenancy, it should check the bootstrap tenant's database
- This caused false negatives when tenant was properly set up

**After:**
- Correctly detects if multi-tenancy is enabled
- Uses bootstrap tenant's database for validation when multi-tenancy is enabled
- Uses default database for single-tenant mode

## Validation Steps

The validation script performs these checks:

### Step 1: Configuration Check/Initialization
- **If DocEX is already initialized:**
  - Loads and displays current configuration
  - Validates configuration file exists and is valid
  - Shows database type, storage type, and multi-tenancy status
- **If DocEX is not initialized:**
  - Builds configuration from provided settings (or defaults)
  - Initializes DocEX with `DocEX.setup()`
  - Validates configuration file exists and is valid

### Step 2: Bootstrap Tenant Initialization
- Checks if multi-tenancy is enabled (from current config)
- Verifies bootstrap tenant exists
- Initializes bootstrap tenant if needed

### Step 3: Setup Validation
- Uses `DocEX.is_properly_setup()` to perform comprehensive checks:
  - Configuration file exists and is valid
  - Database is accessible
  - Required tables exist
  - Bootstrap tenant exists (if multi-tenancy enabled)
- Reports detailed error messages if any checks fail

### Step 4: Basic Operations Test
- Creates a DocEX instance (with tenant context if provided)
- Creates a test basket
- Adds a test document
- Retrieves the document
- Cleans up test data

## Command Line Options

```bash
python test_release_validation.py [OPTIONS]

Options:
  --tenant-id TENANT_ID        Tenant ID for multi-tenancy testing
  --db-type {sqlite,postgresql} Database type (only used if DocEX not initialized)
  --db-host HOST               PostgreSQL host (only used if DocEX not initialized)
  --db-port PORT               PostgreSQL port (only used if DocEX not initialized)
  --db-name NAME               PostgreSQL database name (only used if DocEX not initialized)
  --db-user USER               PostgreSQL user (only used if DocEX not initialized)
  --db-password PASSWORD       PostgreSQL password (only used if DocEX not initialized)
  --storage-type {filesystem,s3} Storage type (only used if DocEX not initialized)
  --storage-path PATH          Filesystem storage path (only used if DocEX not initialized)
  --s3-bucket BUCKET           S3 bucket name (only used if DocEX not initialized)
  --s3-region REGION           S3 region (only used if DocEX not initialized)
  --multi-tenancy              Enable multi-tenancy (only used if DocEX not initialized)
```

**Note:** All configuration options are only used if DocEX is not already initialized. If DocEX is already initialized, the script will use the existing configuration.

## Example Usage

### Validate Existing Setup (Recommended)
```bash
# Simply run without arguments - validates current DocEX setup
python test_release_validation.py

# With specific tenant
python test_release_validation.py --tenant-id acme_corp
```

### Initialize and Validate New Setup
```bash
# Single-tenant SQLite (only if not initialized)
python test_release_validation.py --db-type sqlite

# Multi-tenant SQLite (only if not initialized)
python test_release_validation.py --multi-tenancy
```

### PostgreSQL with Multi-Tenancy
```bash
python test_release_validation.py \
    --db-type postgresql \
    --db-host localhost \
    --db-port 5432 \
    --db-name docex_production \
    --db-user docex_user \
    --db-password secure_password \
    --multi-tenancy
```

### S3 Storage
```bash
python test_release_validation.py \
    --storage-type s3 \
    --s3-bucket my-documents-bucket \
    --s3-region us-east-1
```

### Full Multi-Tenant PostgreSQL with S3
```bash
python test_release_validation.py \
    --db-type postgresql \
    --db-host localhost \
    --db-name docex_prod \
    --db-user docex_user \
    --db-password password \
    --storage-type s3 \
    --s3-bucket my-bucket \
    --s3-region us-east-1 \
    --multi-tenancy \
    --tenant-id acme_corp
```

## Expected Output

### Successful Validation (Existing Setup)
```
======================================================================
 DocEX Release Validation Test
======================================================================
ℹ️  DocEX is already initialized - will validate existing setup

----------------------------------------------------------------------
 Step 1: Configuration Check
----------------------------------------------------------------------
✅ DocEX is already initialized
   Database Type: postgresql
   Storage Type: s3
   Multi-tenancy: Enabled
   PostgreSQL Host: localhost
   PostgreSQL Database: docex_production
✅ Using existing DocEX configuration

----------------------------------------------------------------------
 Step 2: Bootstrap Tenant Initialization
----------------------------------------------------------------------
✅ Bootstrap tenant already initialized

----------------------------------------------------------------------
 Step 3: Setup Validation
----------------------------------------------------------------------
✅ DocEX is properly set up

----------------------------------------------------------------------
 Step 4: Basic Operations Test
----------------------------------------------------------------------
✅ DocEX instance created for tenant: acme_corp
✅ Basket created: bas_abc123 (test_basket_xyz)
✅ Document added: doc_def456 (test_document.txt)
✅ Document retrieved: doc_def456
✅ Test basket deleted (cleanup)

======================================================================
 Validation Summary
======================================================================
ℹ️  Validated against existing DocEX configuration
✅ ALL VALIDATION TESTS PASSED

DocEX is properly set up and ready for use!
```

### Successful Validation (New Initialization)
```
======================================================================
 DocEX Release Validation Test
======================================================================
ℹ️  DocEX is not initialized - will initialize with provided settings
   Test Directory: /tmp/docex_validation_xyz123

----------------------------------------------------------------------
 Step 1: Configuration Check
----------------------------------------------------------------------
ℹ️  DocEX not initialized, initializing with provided settings...
✅ DocEX configuration initialized
✅ Configuration file validated

----------------------------------------------------------------------
 Step 2: Bootstrap Tenant Initialization
----------------------------------------------------------------------
⚠️  Bootstrap tenant not initialized, initializing now...
✅ Bootstrap tenant initialized

----------------------------------------------------------------------
 Step 3: Setup Validation
----------------------------------------------------------------------
✅ DocEX is properly set up

----------------------------------------------------------------------
 Step 4: Basic Operations Test
----------------------------------------------------------------------
✅ DocEX instance created (single-tenant mode)
✅ Basket created: bas_abc123 (test_basket_xyz)
✅ Document added: doc_def456 (test_document.txt)
✅ Document retrieved: doc_def456
✅ Test basket deleted (cleanup)

======================================================================
 Validation Summary
======================================================================
✅ ALL VALIDATION TESTS PASSED

DocEX is properly set up and ready for use!
```

### Failed Validation
```
======================================================================
 DocEX Release Validation Test
======================================================================

----------------------------------------------------------------------
 Step 3: Setup Validation
----------------------------------------------------------------------
❌ DocEX is not properly set up

Errors found:
  1. Missing required tables: docbasket, document
  2. Multi-tenancy enabled but bootstrap tenant not initialized. Run BootstrapTenantManager().initialize() to set up the system tenant.

======================================================================
 Validation Summary
======================================================================
❌ VALIDATION FAILED

Errors found:
  1. Step 3: Missing required tables: docbasket, document
  2. Step 3: Multi-tenancy enabled but bootstrap tenant not initialized. Run BootstrapTenantManager().initialize() to set up the system tenant.

Please fix the errors above and run the validation again.
```

## Programmatic Usage

You can also use the validation functions programmatically:

```python
from docex import DocEX
from docex.provisioning.bootstrap import BootstrapTenantManager

# Check if properly set up
if DocEX.is_properly_setup():
    print("✅ DocEX is ready")
else:
    # Get detailed errors
    errors = DocEX.get_setup_errors()
    print("❌ Setup errors:")
    for error in errors:
        print(f"  - {error}")

# Check bootstrap tenant
bootstrap_manager = BootstrapTenantManager()
if bootstrap_manager.is_initialized():
    print("✅ Bootstrap tenant is initialized")
else:
    print("⚠️  Bootstrap tenant not initialized")
    bootstrap_manager.initialize(created_by="admin")
```

## Troubleshooting

### Error: "Configuration not initialized"
**Solution:** Run `DocEX.setup()` first or ensure `~/.docex/config.yaml` exists.

### Error: "Database connectivity failed"
**Solution:** 
- Check database credentials
- Ensure database server is running
- Verify network connectivity (for PostgreSQL)

### Error: "Missing required tables"
**Solution:** 
- Tables should be created automatically during initialization
- Check database permissions
- Verify database schema was created

### Error: "Bootstrap tenant not initialized"
**Solution:** 
```python
from docex.provisioning.bootstrap import BootstrapTenantManager
bootstrap_manager = BootstrapTenantManager()
bootstrap_manager.initialize(created_by="admin")
```

## Integration with CI/CD

You can integrate this validation script into your CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
- name: Validate DocEX Setup
  run: |
    python test_release_validation.py \
      --db-type postgresql \
      --db-host ${{ secrets.DB_HOST }} \
      --db-name ${{ secrets.DB_NAME }} \
      --db-user ${{ secrets.DB_USER }} \
      --db-password ${{ secrets.DB_PASSWORD }} \
      --multi-tenancy
```

## Next Steps

After successful validation:
1. **Provision Tenants**: Use `TenantProvisioner` to create business tenants
2. **Create DocEX Instances**: Initialize `DocEX(user_context=UserContext(tenant_id='...'))`
3. **Start Using DocEX**: Create baskets, add documents, etc.

See [Platform_Integration_Guide.md](Platform_Integration_Guide.md) for more details on platform integration.

