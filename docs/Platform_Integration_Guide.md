# Platform Integration Guide: Bootstrapping DocEX from Your Platform

This guide explains how to integrate DocEX into your platform by programmatically constructing the configuration, initializing DocEX, bootstrapping the system tenant, and validating the setup.

## Overview

When integrating DocEX into your platform, you typically need to:

1. **Construct Configuration**: Build `config.yaml` from your platform's consolidated system settings
2. **Initialize DocEX**: Set up DocEX with the configuration
3. **Bootstrap System Tenant**: Initialize the system tenant (required for multi-tenancy)
4. **Validate Setup**: Confirm DocEX is properly configured and ready for use
5. **Provision Business Tenants**: Create tenants for your platform's customers/organizations
6. **Use DocEX**: Create baskets, add documents, and manage document operations

The `is_properly_setup()` method is a critical validation function that confirms DocEX is set up correctly and ready for operations. Use `get_setup_errors()` to get detailed error messages if validation fails.

## Use Case Flow

```
Platform System Settings
    ↓
Construct config.yaml
    ↓
DocEX.setup(config)
    ↓
BootstrapTenantManager.initialize()
    ↓
DocEX.is_properly_setup() / DocEX.get_setup_errors()
    ↓
TenantProvisioner.create() (for business tenants)
    ↓
DocEX(user_context=UserContext(user_id, tenant_id))
    ↓
docex.create_basket() → basket.add() → basket.list_documents()
    ↓
✅ DocEX Ready for Use
```

## Step-by-Step Integration

### Step 1: Construct Configuration from Platform Settings

Build the DocEX configuration dictionary from your platform's system settings. The configuration should match the structure expected by DocEX.

```python
from pathlib import Path
from docex.config.docex_config import DocEXConfig

def build_docex_config_from_platform(platform_settings):
    """
    Construct DocEX configuration from platform system settings.
    
    Args:
        platform_settings: Dictionary containing platform configuration
        
    Returns:
        Dictionary with DocEX configuration structure
    """
    # Extract database settings from platform
    db_type = platform_settings.get('database_type', 'sqlite')  # 'sqlite' or 'postgresql'
    
    config = {
        'database': {
            'type': db_type,
        },
        'storage': {
            'type': platform_settings.get('storage_type', 'filesystem'),
        },
        'logging': {
            'level': platform_settings.get('log_level', 'INFO'),
            'file': platform_settings.get('log_file', 'docex.log'),
        },
    }
    
    # Add database-specific configuration
    if db_type == 'sqlite':
        db_path = platform_settings.get('sqlite_path', 'docex.db')
        config['database']['sqlite'] = {
            'path': db_path,
        }
    elif db_type == 'postgresql':
        config['database']['postgres'] = {
            'host': platform_settings.get('db_host', 'localhost'),
            'port': platform_settings.get('db_port', 5432),
            'database': platform_settings.get('db_name', 'docex'),
            'user': platform_settings.get('db_user', 'postgres'),
            'password': platform_settings.get('db_password', ''),
        }
    
    # Add storage-specific configuration
    storage_type = config['storage']['type']
    if storage_type == 'filesystem':
        storage_path = platform_settings.get('storage_path', 'storage/docex')
        config['storage']['filesystem'] = {
            'path': storage_path,
        }
    elif storage_type == 's3':
        config['storage']['s3'] = {
            'bucket': platform_settings.get('s3_bucket'),
            'region': platform_settings.get('s3_region', 'us-east-1'),
            'path_namespace': platform_settings.get('s3_path_namespace', ''),
            'prefix': platform_settings.get('s3_prefix', 'production'),
            'access_key': platform_settings.get('aws_access_key'),
            'secret_key': platform_settings.get('aws_secret_key'),
        }
        # Note: S3 path structure uses three parts:
        # Part A (config_prefix): {tenant_id}/{path_namespace}/{prefix}/ - set automatically
        # Part B (basket_path): {basket_name}_{last_4_of_basket_id}/ - set when basket is created
        # Part C (document_path): {document_name}_{last_6_of_document_id}.{ext} - stored in document.path
        # Full path = Part A + Part B + Part C
    
    # Add multi-tenancy configuration if enabled
    if platform_settings.get('multi_tenancy_enabled', False):
        config['multi_tenancy'] = {
            'enabled': True,
            'isolation_strategy': 'schema' if db_type == 'postgresql' else 'database',
            'bootstrap_tenant': {
                'id': '_docex_system_',
                'display_name': 'DocEX System',
                'schema': 'docex_system',
                'database_path': 'storage/_docex_system_/docex.db' if db_type == 'sqlite' else None,
            },
        }
    
    return config
```

### Step 2: Initialize DocEX with Configuration

Use `DocEX.setup()` to initialize DocEX with your constructed configuration. This saves the configuration to `~/.docex/config.yaml` and prepares DocEX for use.

```python
from docex import DocEX

def initialize_docex(platform_settings):
    """
    Initialize DocEX from platform settings.
    
    Args:
        platform_settings: Dictionary containing platform configuration
        
    Returns:
        True if initialization successful, False otherwise
    """
    try:
        # Build configuration from platform settings
        config = build_docex_config_from_platform(platform_settings)
        
        # Initialize DocEX with configuration
        DocEX.setup(**config)
        
        print("✅ DocEX configuration initialized")
        return True
        
    except Exception as e:
        print(f"❌ Failed to initialize DocEX: {e}")
        return False
```

### Step 3: Bootstrap System Tenant

If multi-tenancy is enabled, you must initialize the bootstrap/system tenant. This tenant manages the tenant registry and system metadata.

```python
from docex.provisioning.bootstrap import BootstrapTenantManager

def bootstrap_system_tenant(created_by: str = "platform"):
    """
    Bootstrap the system tenant for DocEX.
    
    Args:
        created_by: User ID who is initializing the system
        
    Returns:
        True if bootstrap successful, False otherwise
    """
    try:
        bootstrap_manager = BootstrapTenantManager()
        
        # Check if already initialized
        if bootstrap_manager.is_initialized():
            print("✅ Bootstrap tenant already initialized")
            return True
        
        # Initialize bootstrap tenant
        bootstrap_manager.initialize(created_by=created_by)
        print("✅ Bootstrap tenant initialized")
        return True
        
    except Exception as e:
        print(f"❌ Failed to bootstrap system tenant: {e}")
        return False
```

### Step 4: Validate Setup

Use `DocEX.is_initialized()` or `DocEX.is_properly_setup()` to validate that DocEX is correctly configured and ready for use.

#### `DocEX.is_initialized()`

Checks if DocEX configuration is loaded and valid:

```python
def validate_docex_initialization():
    """
    Validate that DocEX is initialized.
    
    Returns:
        True if initialized, False otherwise
    """
    if DocEX.is_initialized():
        print("✅ DocEX is initialized")
        return True
    else:
        print("❌ DocEX is not initialized")
        return False
```

#### `DocEX.is_properly_setup()`

Performs comprehensive validation including:
- Configuration file exists and is valid
- Database is accessible
- Required tables exist
- Bootstrap tenant exists (if multi-tenancy enabled)

```python
def validate_docex_setup():
    """
    Validate that DocEX is properly set up and ready for use.
    
    Returns:
        True if properly set up, False otherwise
    """
    if DocEX.is_properly_setup():
        print("✅ DocEX is properly set up and ready for use")
        return True
    else:
        # Get detailed error messages
        errors = DocEX.get_setup_errors()
        print("❌ DocEX is not properly set up")
        for error in errors:
            print(f"   - {error}")
        return False
```

#### `DocEX.get_setup_errors()`

Returns a list of detailed error messages if setup validation fails:

```python
def get_setup_errors():
    """
    Get detailed setup error messages.
    
    Returns:
        List of error messages (empty if setup is valid)
    """
    errors = DocEX.get_setup_errors()
    if errors:
        print("Setup errors found:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✅ No setup errors")
    return errors
```

## Complete Integration Example (Basic)

Here's a basic integration example that covers initialization and validation:

```python
from docex import DocEX
from docex.provisioning.bootstrap import BootstrapTenantManager

def integrate_docex_into_platform(platform_settings):
    """
    Basic integration flow: configure, initialize, bootstrap, and validate DocEX.
    
    Args:
        platform_settings: Dictionary containing platform configuration
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Step 1: Build configuration from platform settings
        print("Step 1: Building DocEX configuration from platform settings...")
        config = build_docex_config_from_platform(platform_settings)
        
        # Step 2: Initialize DocEX
        print("Step 2: Initializing DocEX...")
        DocEX.setup(**config)
        print("✅ DocEX configuration initialized")
        
        # Step 3: Bootstrap system tenant (if multi-tenancy enabled)
        multi_tenancy_enabled = platform_settings.get('multi_tenancy_enabled', False)
        if multi_tenancy_enabled:
            print("Step 3: Bootstrapping system tenant...")
            bootstrap_manager = BootstrapTenantManager()
            
            if not bootstrap_manager.is_initialized():
                bootstrap_manager.initialize(created_by=platform_settings.get('admin_user', 'platform'))
                print("✅ Bootstrap tenant initialized")
            else:
                print("✅ Bootstrap tenant already initialized")
        
        # Step 4: Validate setup
        print("Step 4: Validating DocEX setup...")
        if not DocEX.is_initialized():
            return False, "DocEX configuration not initialized"
        
        if not DocEX.is_properly_setup():
            errors = DocEX.get_setup_errors()
            return False, f"DocEX is not properly set up: {', '.join(errors)}"
        
        print("✅ DocEX is properly initialized and ready for use")
        return True, "DocEX integration successful"
        
    except Exception as e:
        error_msg = f"Failed to integrate DocEX: {str(e)}"
        print(f"❌ {error_msg}")
        return False, error_msg
```

## Alternative: Loading Configuration from File

If your platform generates a `config.yaml` file, you can load it directly:

```python
import yaml
from pathlib import Path
from docex import DocEX
from docex.config.docex_config import DocEXConfig

def initialize_docex_from_config_file(config_file_path: Path):
    """
    Initialize DocEX from a configuration file.
    
    Args:
        config_file_path: Path to config.yaml file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Load configuration from file
        with open(config_file_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        # Initialize DocEX
        DocEX.setup(**config_dict)
        
        # Bootstrap system tenant if multi-tenancy enabled
        config = DocEXConfig()
        multi_tenancy_config = config.get('multi_tenancy', {})
        if multi_tenancy_config.get('enabled', False):
            bootstrap_manager = BootstrapTenantManager()
            if not bootstrap_manager.is_initialized():
                bootstrap_manager.initialize(created_by='platform')
        
        # Validate
        if DocEX.is_properly_setup():
            print("✅ DocEX initialized from config file")
            return True
        else:
            print("❌ DocEX setup validation failed")
            return False
            
    except Exception as e:
        print(f"❌ Failed to initialize from config file: {e}")
        return False
```

## Configuration File Structure

When constructing `config.yaml`, ensure it follows this structure:

```yaml
database:
  type: postgresql  # or 'sqlite'
  postgres:
    host: localhost
    port: 5432
    database: docex
    user: postgres
    password: password
  sqlite:
    path: docex.db

storage:
  type: s3  # or 'filesystem'
  filesystem:
    path: storage/docex
  s3:
    bucket: my-bucket
    region: us-east-1
    path_namespace: production
    prefix: prod

multi_tenancy:
  enabled: true
  isolation_strategy: schema  # or 'database'
  bootstrap_tenant:
    id: _docex_system_
    display_name: DocEX System
    schema: docex_system
    database_path: null  # Only for SQLite

logging:
  level: INFO
  file: docex.log
```

## Validation Methods Comparison

| Method | Checks | Use Case |
|--------|--------|----------|
| `DocEX.is_initialized()` | Configuration file exists and is valid | Quick check if config is loaded |
| `DocEX.is_properly_setup()` | Config + Database + Tables + Bootstrap tenant | Comprehensive validation before operations |
| `DocEX.get_setup_errors()` | Returns list of detailed error messages | Get specific issues when setup fails |
| `BootstrapTenantManager.is_initialized()` | Bootstrap tenant exists in registry | Check if system tenant is ready |
| `TenantProvisioner.tenant_exists(tenant_id)` | Check if a tenant is already provisioned | Verify tenant before provisioning |

**Recommendation**: Use `DocEX.is_properly_setup()` for platform integration validation. If it returns `False`, call `DocEX.get_setup_errors()` to get detailed error messages.

## Error Handling

Always wrap initialization in try-except blocks and handle common errors:

```python
def safe_docex_initialization(platform_settings):
    """Safely initialize DocEX with error handling."""
    try:
        # Build and apply configuration
        config = build_docex_config_from_platform(platform_settings)
        DocEX.setup(**config)
        
        # Bootstrap if needed
        if config.get('multi_tenancy', {}).get('enabled', False):
            bootstrap_manager = BootstrapTenantManager()
            if not bootstrap_manager.is_initialized():
                bootstrap_manager.initialize()
        
        # Validate
        if not DocEX.is_properly_setup():
            raise RuntimeError("DocEX setup validation failed")
        
        return True
        
    except FileNotFoundError as e:
        print(f"Configuration file error: {e}")
        return False
    except ConnectionError as e:
        print(f"Database connection error: {e}")
        return False
    except ValueError as e:
        print(f"Configuration validation error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False
```

## Best Practices

1. **Always Validate**: Use `DocEX.is_properly_setup()` after initialization to ensure everything is ready. Use `DocEX.get_setup_errors()` to get detailed error messages if validation fails.
2. **Idempotent Operations**: 
   - Check `BootstrapTenantManager.is_initialized()` before calling `initialize()` to avoid errors
   - Check `TenantProvisioner.tenant_exists(tenant_id)` before provisioning tenants
3. **UserContext Requirements**: When multi-tenancy is enabled, always provide `UserContext` with `user_id` (required) and `tenant_id` (required for multi-tenant operations)
4. **Error Handling**: Wrap initialization in try-except blocks and provide meaningful error messages. Handle `TenantExistsError` and `InvalidTenantIdError` when provisioning tenants.
5. **Configuration Validation**: Validate platform settings before constructing DocEX configuration
6. **Logging**: Enable appropriate logging levels to track initialization progress
7. **Storage Permissions**: Ensure storage directories/filesystem paths have proper write permissions
8. **Database Credentials**: Securely manage database credentials (use environment variables or secrets management)
9. **S3 Path Structure**: Understand the three-part S3 path structure (Part A: config, Part B: basket, Part C: document) for debugging and path verification
10. **Document Path Storage**: Documents store full paths in `document.path` for simplicity. For S3: full path = Part A + Part B + Part C. For filesystem: full relative path = Part B + Part C.
11. **Basket Storage Config**: Baskets store path components separately in `storage_config['s3']`:
    - `config_prefix`: Part A (config-based prefix)
    - `basket_path`: Part B (basket-specific path)
    - `prefix`: Combined A + B (for backward compatibility)

## Troubleshooting

### Configuration Not Found
```
Error: Configuration file not found at ~/.docex/config.yaml
```
**Solution**: Ensure `DocEX.setup()` is called before using DocEX, or manually create the config file.

### Database Connection Failed
```
Error: Database connectivity check failed
```
**Solution**: Verify database credentials, network connectivity, and that the database server is running.

### Bootstrap Tenant Not Initialized
```
Error: Multi-tenancy enabled but bootstrap tenant not initialized
```
**Solution**: Call `BootstrapTenantManager().initialize()` after `DocEX.setup()`.

### Missing Required Tables
```
Error: Missing required tables: ['docbasket', 'document', ...]
```
**Solution**: Ensure database schema is created. DocEX should create tables automatically, but verify database permissions.

## Step 5: Provision Business Tenants

After bootstrapping the system tenant, you can provision business tenants for your platform's customers or organizations.

```python
from docex.provisioning.tenant_provisioner import TenantProvisioner
from docex.provisioning.tenant_provisioner import TenantExistsError, InvalidTenantIdError

def provision_business_tenant(tenant_id: str, display_name: str, created_by: str):
    """
    Provision a new business tenant.
    
    Args:
        tenant_id: Unique identifier for the tenant (1-30 chars, letters/numbers/underscores only)
        display_name: Human-readable name for the tenant
        created_by: User ID who is creating the tenant
        
    Returns:
        TenantRegistry instance for the newly created tenant
    """
    try:
        provisioner = TenantProvisioner()
        
        # Check if tenant already exists
        if provisioner.tenant_exists(tenant_id):
            print(f"⚠️  Tenant '{tenant_id}' already exists")
            return None
        
        # Provision the tenant
        tenant_registry = provisioner.create(
            tenant_id=tenant_id,
            display_name=display_name,
            created_by=created_by
            # isolation_strategy is auto-detected based on database type
        )
        
        print(f"✅ Tenant '{tenant_id}' provisioned successfully")
        return tenant_registry
        
    except InvalidTenantIdError as e:
        print(f"❌ Invalid tenant ID: {e}")
        return None
    except TenantExistsError as e:
        print(f"❌ {e}")
        return None
    except Exception as e:
        print(f"❌ Failed to provision tenant: {e}")
        return None
```

### Tenant Provisioning Process

The `TenantProvisioner.create()` method performs the following steps:

1. **Validates tenant ID**: Ensures it's not reserved and follows naming rules
2. **Checks for existing tenant**: Prevents duplicate provisioning
3. **Creates isolation boundary**: 
   - PostgreSQL: Creates a schema (e.g., `tenant_acme_corp`)
   - SQLite: Creates a separate database file
4. **Initializes schema**: Creates all required tables in the tenant's schema/database
5. **Creates performance indexes**: Optimizes queries for the tenant
6. **Validates schema**: Verifies all tables and indexes are created correctly
7. **Registers tenant**: Adds tenant to the tenant registry

### Example: Provisioning Multiple Tenants

```python
def provision_platform_tenants(tenant_list):
    """
    Provision multiple tenants for your platform.
    
    Args:
        tenant_list: List of dicts with 'tenant_id', 'display_name', 'created_by'
    """
    provisioner = TenantProvisioner()
    results = []
    
    for tenant_info in tenant_list:
        tenant_id = tenant_info['tenant_id']
        display_name = tenant_info['display_name']
        created_by = tenant_info.get('created_by', 'platform')
        
        try:
            if provisioner.tenant_exists(tenant_id):
                print(f"⚠️  Tenant '{tenant_id}' already exists, skipping...")
                results.append({'tenant_id': tenant_id, 'status': 'exists'})
                continue
            
            tenant_registry = provisioner.create(
                tenant_id=tenant_id,
                display_name=display_name,
                created_by=created_by
            )
            results.append({'tenant_id': tenant_id, 'status': 'created', 'registry': tenant_registry})
            print(f"✅ Provisioned tenant: {tenant_id}")
            
        except Exception as e:
            results.append({'tenant_id': tenant_id, 'status': 'error', 'error': str(e)})
            print(f"❌ Failed to provision tenant '{tenant_id}': {e}")
    
    return results

# Example usage
tenants = [
    {'tenant_id': 'acme_corp', 'display_name': 'Acme Corporation', 'created_by': 'admin'},
    {'tenant_id': 'contoso', 'display_name': 'Contoso Ltd', 'created_by': 'admin'},
    {'tenant_id': 'fabrikam', 'display_name': 'Fabrikam Inc', 'created_by': 'admin'},
]

results = provision_platform_tenants(tenants)
```

## Step 6: Using DocEX with Provisioned Tenants

After provisioning tenants, you can use DocEX with tenant-specific operations.

### Creating DocEX Instance with UserContext

**Important**: When multi-tenancy is enabled, you **must** provide a `UserContext` with `user_id` and `tenant_id`:

```python
from docex import DocEX
from docex.context import UserContext

def create_docex_for_tenant(tenant_id: str, user_id: str):
    """
    Create a DocEX instance for a specific tenant.
    
    Args:
        tenant_id: Tenant identifier
        user_id: User identifier (required)
        
    Returns:
        DocEX instance configured for the tenant
    """
    # UserContext requires user_id (mandatory)
    # tenant_id is optional but required for multi-tenant setups
    user_context = UserContext(
        user_id=user_id,  # Required
        tenant_id=tenant_id  # Required for multi-tenant
    )
    
    docex = DocEX(user_context=user_context)
    return docex
```

### Creating Baskets

Baskets can be created with different storage types (S3 or filesystem):

```python
def create_baskets_for_tenant(docex: DocEX):
    """
    Create baskets for a tenant with different storage configurations.
    """
    # Create a filesystem basket (default)
    fs_basket = docex.create_basket(
        name="invoices_pending",
        description="Pending invoices awaiting processing"
    )
    print(f"✅ Created filesystem basket: {fs_basket.id}")
    
    # Create an S3 basket
    s3_storage_config = {
        'type': 's3',
        's3': {
            'bucket': 'my-documents-bucket',
            'region': 'us-east-1',
            'path_namespace': 'production',
            'prefix': 'prod',
            'access_key': 'AKIA...',
            'secret_key': '...'
        }
    }
    
    s3_basket = docex.create_basket(
        name="invoices_processed",
        description="Processed invoices archive",
        storage_config=s3_storage_config
    )
    print(f"✅ Created S3 basket: {s3_basket.id}")
    
    # Verify basket storage configuration
    print(f"Filesystem basket storage type: {fs_basket.storage_config.get('type')}")
    print(f"S3 basket storage type: {s3_basket.storage_config.get('type')}")
    
    # For S3 baskets, check path structure components
    if s3_basket.storage_config.get('type') == 's3':
        s3_config = s3_basket.storage_config.get('s3', {})
        print(f"S3 Config Prefix (Part A): {s3_config.get('config_prefix')}")
        print(f"S3 Basket Path (Part B): {s3_config.get('basket_path')}")
        print(f"S3 Full Prefix (A+B): {s3_config.get('prefix')}")
    
    return fs_basket, s3_basket
```

### Adding Documents to Baskets

Documents are added using the `basket.add()` method:

```python
from pathlib import Path

def add_documents_to_basket(basket, file_paths: list):
    """
    Add multiple documents to a basket.
    
    Args:
        basket: DocBasket instance
        file_paths: List of file paths to add
    """
    documents = []
    
    for file_path in file_paths:
        # Add document with optional metadata
        doc = basket.add(
            file_path=str(file_path),
            document_type='file',
            metadata={
                'source': 'platform_upload',
                'uploaded_by': 'user123',
                'category': 'invoice'
            }
        )
        documents.append(doc)
        print(f"✅ Added document: {doc.id} ({doc.name})")
        
        # Document path contains full storage path
        # For S3: Full path = Part A + Part B + Part C
        # For filesystem: Full relative path = Part B + Part C
        print(f"   Storage path: {doc.path}")
    
    return documents
```

### Retrieving Documents

```python
def retrieve_documents_from_basket(basket):
    """
    Retrieve documents from a basket using various methods.
    """
    # List all documents
    all_docs = basket.list_documents()
    print(f"📋 Total documents: {len(all_docs)}")
    
    # Get document by ID
    if all_docs:
        doc = basket.get_document(all_docs[0].id)
        print(f"✅ Retrieved document by ID: {doc.id}")
        
        # Get document content
        # For text files
        if doc.content_type and 'text' in doc.content_type:
            content = doc.get_content(mode='text')
            print(f"   Content length: {len(content)} characters")
        
        # For binary files
        else:
            content = doc.get_content(mode='bytes')
            print(f"   Content length: {len(content)} bytes")
    
    # Find documents by metadata
    invoice_docs = basket.find_documents_by_metadata({'category': 'invoice'})
    print(f"📋 Found {len(invoice_docs)} invoice documents")
    
    # Count documents
    doc_count = basket.count_documents()
    print(f"📊 Document count: {doc_count}")
    
    return all_docs
```

### S3 Path Structure

When using S3 storage, DocEX uses a three-part path structure:

- **Part A (Config Prefix)**: `{tenant_id}/{path_namespace}/{prefix}/`
  - Stored in: `basket.storage_config['s3']['config_prefix']`
- **Part B (Basket Path)**: `{basket_friendly_name}_{last_4_of_basket_id}/`
  - Stored in: `basket.storage_config['s3']['basket_path']`
- **Part C (Document Path)**: `{document_friendly_name}_{last_6_of_document_id}.{ext}`
  - Stored in: `document.path` (full path = A + B + C)

**Example S3 Path**:
```
s3://my-bucket/acme_corp/finance_dept/production/invoice_raw_2c03/invoice_001_585d29.pdf
```
- Part A: `acme_corp/finance_dept/production/`
- Part B: `invoice_raw_2c03/`
- Part C: `invoice_001_585d29.pdf`

See [S3_PATH_STRUCTURE.md](S3_PATH_STRUCTURE.md) for detailed documentation.

## Complete Integration Example

Here's a complete example that ties everything together:

```python
from docex import DocEX
from docex.provisioning.bootstrap import BootstrapTenantManager
from docex.provisioning.tenant_provisioner import TenantProvisioner
from docex.context import UserContext
from pathlib import Path

def complete_platform_integration(platform_settings):
    """
    Complete integration flow: configure, initialize, bootstrap, provision, and use DocEX.
    """
    try:
        # Step 1: Build configuration
        print("Step 1: Building DocEX configuration...")
        config = build_docex_config_from_platform(platform_settings)
        
        # Step 2: Initialize DocEX
        print("Step 2: Initializing DocEX...")
        DocEX.setup(**config)
        print("✅ DocEX configuration initialized")
        
        # Step 3: Bootstrap system tenant
        multi_tenancy_enabled = platform_settings.get('multi_tenancy_enabled', False)
        if multi_tenancy_enabled:
            print("Step 3: Bootstrapping system tenant...")
            bootstrap_manager = BootstrapTenantManager()
            if not bootstrap_manager.is_initialized():
                bootstrap_manager.initialize(created_by=platform_settings.get('admin_user', 'platform'))
                print("✅ Bootstrap tenant initialized")
        
        # Step 4: Validate setup
        print("Step 4: Validating DocEX setup...")
        if not DocEX.is_properly_setup():
            return False, "DocEX is not properly set up"
        print("✅ DocEX is properly set up")
        
        # Step 5: Provision business tenant
        if multi_tenancy_enabled:
            print("Step 5: Provisioning business tenant...")
            provisioner = TenantProvisioner()
            tenant_id = platform_settings.get('default_tenant_id', 'acme_corp')
            
            if not provisioner.tenant_exists(tenant_id):
                provisioner.create(
                    tenant_id=tenant_id,
                    display_name=platform_settings.get('default_tenant_name', 'Acme Corporation'),
                    created_by=platform_settings.get('admin_user', 'platform')
                )
                print(f"✅ Tenant '{tenant_id}' provisioned")
            else:
                print(f"✅ Tenant '{tenant_id}' already exists")
        
        # Step 6: Use DocEX with tenant
        print("Step 6: Using DocEX with tenant...")
        user_context = UserContext(
            user_id=platform_settings.get('admin_user', 'platform'),
            tenant_id=tenant_id if multi_tenancy_enabled else None
        )
        docex = DocEX(user_context=user_context)
        
        # Create a basket
        basket = docex.create_basket(
            name="test_basket",
            description="Test basket for integration"
        )
        print(f"✅ Created basket: {basket.id}")
        
        # Add a test document
        test_file = Path('/tmp/test_document.txt')
        test_file.write_text('Test document content')
        doc = basket.add(str(test_file), metadata={'test': True})
        print(f"✅ Added document: {doc.id}")
        
        # Verify document retrieval
        retrieved_doc = basket.get_document(doc.id)
        if retrieved_doc:
            print(f"✅ Retrieved document: {retrieved_doc.id}")
            print(f"   Document path: {retrieved_doc.path}")
        
        # Cleanup
        test_file.unlink()
        basket.delete()
        
        print("✅ Complete integration successful")
        return True, "Integration successful"
        
    except Exception as e:
        error_msg = f"Failed to integrate DocEX: {str(e)}"
        print(f"❌ {error_msg}")
        return False, error_msg
```

## Next Steps

After successful initialization and tenant provisioning:

1. **Provision Tenants**: Use `TenantProvisioner.create()` to create business tenants
2. **Create DocEX Instance**: Initialize `DocEX(user_context=UserContext(user_id='...', tenant_id='...'))`
3. **Create Baskets**: Use `docex.create_basket()` to create document baskets (S3 or filesystem)
4. **Add Documents**: Use `basket.add(file_path, metadata={...})` to add documents
5. **Retrieve Documents**: Use `basket.get_document(id)`, `basket.list_documents()`, or `basket.find_documents_by_metadata()`
6. **Get Document Content**: Use `document.get_content(mode='text'|'bytes'|'json')`

See [MULTI_TENANCY_GUIDE.md](MULTI_TENANCY_GUIDE.md) for more details on tenant management.
See [S3_PATH_STRUCTURE.md](S3_PATH_STRUCTURE.md) for details on S3 path structure.

