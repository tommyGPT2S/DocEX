# Platform Integration Guide: Bootstrapping DocEX from Your Platform

This guide explains how to integrate DocEX into your platform by programmatically constructing the configuration, initializing DocEX, bootstrapping the system tenant, and validating the setup.

## Overview

When integrating DocEX into your platform, you typically need to:

1. **Construct Configuration**: Build `config.yaml` from your platform's consolidated system settings
2. **Initialize DocEX**: Set up DocEX with the configuration
3. **Bootstrap System Tenant**: Initialize the system tenant (required for multi-tenancy)
4. **Validate Setup**: Confirm DocEX is properly configured and ready for use

The `is_initialized()` method is a critical validation function that confirms DocEX is set up correctly and ready for operations.

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
DocEX.is_initialized() / DocEX.is_properly_setup()
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
        print("❌ DocEX is not properly set up")
        return False
```

## Complete Integration Example

Here's a complete example that ties everything together:

```python
from docex import DocEX
from docex.provisioning.bootstrap import BootstrapTenantManager
from pathlib import Path

def integrate_docex_into_platform(platform_settings):
    """
    Complete integration flow: configure, initialize, bootstrap, and validate DocEX.
    
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
            return False, "DocEX is not properly set up"
        
        print("✅ DocEX is properly initialized and ready for use")
        return True, "DocEX integration successful"
        
    except Exception as e:
        error_msg = f"Failed to integrate DocEX: {str(e)}"
        print(f"❌ {error_msg}")
        return False, error_msg


# Example usage
if __name__ == "__main__":
    # Example platform settings
    platform_settings = {
        'database_type': 'postgresql',
        'db_host': 'localhost',
        'db_port': 5432,
        'db_name': 'docex_production',
        'db_user': 'docex_user',
        'db_password': 'secure_password',
        'storage_type': 's3',
        's3_bucket': 'my-platform-documents',
        's3_region': 'us-east-1',
        's3_path_namespace': 'production',
        's3_prefix': 'prod',
        'aws_access_key': 'AKIA...',
        'aws_secret_key': '...',
        'multi_tenancy_enabled': True,
        'log_level': 'INFO',
        'admin_user': 'platform_admin',
    }
    
    success, message = integrate_docex_into_platform(platform_settings)
    if success:
        print(f"\n✅ Integration successful: {message}")
    else:
        print(f"\n❌ Integration failed: {message}")
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
| `BootstrapTenantManager.is_initialized()` | Bootstrap tenant exists in registry | Check if system tenant is ready |

**Recommendation**: Use `DocEX.is_properly_setup()` for platform integration validation as it performs the most comprehensive checks.

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

1. **Always Validate**: Use `DocEX.is_properly_setup()` after initialization to ensure everything is ready
2. **Idempotent Operations**: Check `BootstrapTenantManager.is_initialized()` before calling `initialize()` to avoid errors
3. **Error Handling**: Wrap initialization in try-except blocks and provide meaningful error messages
4. **Configuration Validation**: Validate platform settings before constructing DocEX configuration
5. **Logging**: Enable appropriate logging levels to track initialization progress
6. **Storage Permissions**: Ensure storage directories/filesystem paths have proper write permissions
7. **Database Credentials**: Securely manage database credentials (use environment variables or secrets management)

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

## Next Steps

After successful initialization:

1. **Provision Tenants**: Use `TenantProvisioner` to create business tenants
2. **Create DocEX Instance**: Initialize `DocEX(user_context=UserContext(tenant_id='...'))`
3. **Create Baskets**: Use `docex.create_basket()` to create document baskets
4. **Add Documents**: Use `basket.add()` to add documents

See [MULTI_TENANCY_GUIDE.md](MULTI_TENANCY_GUIDE.md) for more details on tenant management.

