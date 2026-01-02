#!/usr/bin/env python3
"""
Release Validation Test Script for DocEX

This script validates that DocEX is properly set up and ready for use.
It respects existing DocEX initialization - if DocEX is already initialized,
it will validate against the current setup. Otherwise, it will initialize
with provided settings and then validate.

It tests:
1. Configuration check/initialization
2. Bootstrap tenant (if multi-tenancy enabled)
3. Setup validation (database, tables, bootstrap tenant)
4. Basic operations (create basket, add document)

Usage:
    # Validate existing setup
    python test_release_validation.py
    
    # Validate with specific tenant
    python test_release_validation.py --tenant-id acme_corp
    
    # Initialize and validate (if not already initialized)
    python test_release_validation.py --db-type postgresql --db-host localhost
"""

import argparse
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from docex import DocEX
from docex.config.docex_config import DocEXConfig
from docex.provisioning.bootstrap import BootstrapTenantManager
from docex.context import UserContext


def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def print_section(title: str):
    """Print a formatted section"""
    print("\n" + "-" * 70)
    print(f" {title}")
    print("-" * 70)


def test_configuration_initialization(platform_settings: Optional[dict] = None) -> Tuple[bool, str, bool]:
    """
    Test Step 1: Configuration Initialization
    
    Returns:
        Tuple of (success, message, was_already_initialized)
    """
    print_section("Step 1: Configuration Check")
    
    try:
        # Check if DocEX is already initialized
        if DocEX.is_initialized():
            print("✅ DocEX is already initialized")
            
            # Load and display current configuration
            config = DocEXConfig()
            db_type = config.get('database', {}).get('type', 'unknown')
            storage_type = config.get('storage', {}).get('type', 'unknown')
            multi_tenancy = config.get('multi_tenancy', {}).get('enabled', False)
            
            print(f"   Database Type: {db_type}")
            print(f"   Storage Type: {storage_type}")
            print(f"   Multi-tenancy: {'Enabled' if multi_tenancy else 'Disabled'}")
            
            if db_type == 'sqlite':
                db_path = config.get('database', {}).get('sqlite', {}).get('path', 'unknown')
                print(f"   SQLite Path: {db_path}")
            elif db_type == 'postgresql':
                db_config = config.get('database', {}).get('postgres', {})
                print(f"   PostgreSQL Host: {db_config.get('host', 'unknown')}")
                print(f"   PostgreSQL Database: {db_config.get('database', 'unknown')}")
            
            print("✅ Using existing DocEX configuration")
            return True, "Using existing DocEX configuration", True
        
        # Not initialized - initialize if settings provided
        if platform_settings is None:
            return False, "DocEX not initialized and no configuration provided. Please initialize DocEX first or provide configuration settings.", False
        
        print("ℹ️  DocEX not initialized, initializing with provided settings...")
        
        # Build configuration from platform settings
        config = build_docex_config(platform_settings)
        
        # Initialize DocEX
        DocEX.setup(**config)
        print("✅ DocEX configuration initialized")
        
        # Verify configuration is loaded
        if DocEX.is_initialized():
            print("✅ Configuration file validated")
            return True, "Configuration initialized successfully", False
        else:
            return False, "Configuration file not found or invalid", False
            
    except Exception as e:
        return False, f"Configuration initialization failed: {str(e)}", False


def test_bootstrap_tenant(admin_user: str = "test_user") -> Tuple[bool, str]:
    """Test Step 2: Bootstrap Tenant Initialization"""
    print_section("Step 2: Bootstrap Tenant Initialization")
    
    try:
        config = DocEXConfig()
        multi_tenancy_enabled = config.get('multi_tenancy', {}).get('enabled', False)
        
        if not multi_tenancy_enabled:
            print("ℹ️  Multi-tenancy not enabled, skipping bootstrap tenant check")
            return True, "Multi-tenancy not enabled"
        
        bootstrap_manager = BootstrapTenantManager()
        
        if bootstrap_manager.is_initialized():
            print("✅ Bootstrap tenant already initialized")
            return True, "Bootstrap tenant exists"
        else:
            print("⚠️  Bootstrap tenant not initialized, initializing now...")
            bootstrap_manager.initialize(created_by=admin_user)
            print("✅ Bootstrap tenant initialized")
            return True, "Bootstrap tenant initialized successfully"
            
    except Exception as e:
        return False, f"Bootstrap tenant initialization failed: {str(e)}"


def test_setup_validation() -> Tuple[bool, list[str]]:
    """Test Step 3: Setup Validation"""
    print_section("Step 3: Setup Validation")
    
    # Check if properly set up
    is_setup = DocEX.is_properly_setup()
    
    if is_setup:
        print("✅ DocEX is properly set up")
        return True, []
    else:
        # Get detailed error messages
        errors = DocEX.get_setup_errors()
        print("❌ DocEX is not properly set up")
        print("\nErrors found:")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
        return False, errors


def test_basic_operations(tenant_id: Optional[str] = None) -> Tuple[bool, str]:
    """Test Step 4: Basic Operations"""
    print_section("Step 4: Basic Operations Test")
    
    # Store tenant_id in a local variable to avoid any scoping issues
    test_tenant_id = tenant_id
    
    try:
        # Check if multi-tenancy is enabled
        config = DocEXConfig()
        multi_tenancy_enabled = config.get('multi_tenancy', {}).get('enabled', False)
        
        # Create DocEX instance
        # If tenant_id is provided, always create UserContext with tenant_id
        if test_tenant_id:
            user_context = UserContext(
                user_id='validation_test_user',
                tenant_id=test_tenant_id
            )
            docex = DocEX(user_context=user_context)
            print(f"✅ DocEX instance created for tenant: {test_tenant_id}")
        elif multi_tenancy_enabled:
            # Multi-tenancy enabled but no tenant_id provided
            return False, "Multi-tenancy is enabled but no tenant_id provided. Use --tenant-id to specify a tenant."
        else:
            # Single-tenant mode - try without UserContext first (backward compatibility)
            try:
                docex = DocEX()
                print("✅ DocEX instance created (single-tenant mode, no UserContext)")
            except (ValueError, RuntimeError) as e:
                # If that fails, try with UserContext
                user_context = UserContext(user_id='validation_test_user')
                docex = DocEX(user_context=user_context)
                print("✅ DocEX instance created (single-tenant mode, with UserContext)")
        
        # Create a test basket
        basket_name = f"test_basket_{Path(tempfile.mkdtemp()).name[-8:]}"
        basket = docex.create_basket(basket_name, "Test basket for validation")
        print(f"✅ Basket created: {basket.id} ({basket.name})")
        
        # Add a test document
        test_content = b"Test document content for validation"
        doc = basket.add(
            content=test_content,
            name="test_document.txt",
            content_type="text/plain"
        )
        print(f"✅ Document added: {doc.id} ({doc.name})")
        
        # Retrieve the document
        retrieved_doc = basket.get_document(doc.id)
        if retrieved_doc:
            print(f"✅ Document retrieved: {retrieved_doc.id}")
        else:
            return False, "Failed to retrieve document"
        
        # Clean up test basket
        basket.delete()
        print("✅ Test basket deleted (cleanup)")
        
        return True, "Basic operations test passed"
        
    except Exception as e:
        # Include tenant_id in error message if it was provided
        error_msg = f"Basic operations test failed: {str(e)}"
        if test_tenant_id:
            error_msg += f" (tenant_id: {test_tenant_id})"
        return False, error_msg


def build_docex_config(platform_settings: dict) -> dict:
    """Build DocEX configuration from platform settings"""
    db_type = platform_settings.get('database_type', 'sqlite')
    
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
        }
        if platform_settings.get('aws_access_key'):
            config['storage']['s3']['access_key'] = platform_settings.get('aws_access_key')
        if platform_settings.get('aws_secret_key'):
            config['storage']['s3']['secret_key'] = platform_settings.get('aws_secret_key')
    
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


def main():
    """Main validation function"""
    parser = argparse.ArgumentParser(
        description='Validate DocEX release setup. If DocEX is already initialized, uses existing configuration. Otherwise, initializes with provided settings.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate existing DocEX setup
  python test_release_validation.py
  
  # Validate with specific tenant
  python test_release_validation.py --tenant-id acme_corp
  
  # Initialize and validate new setup (if not already initialized)
  python test_release_validation.py --db-type postgresql --db-host localhost --db-name docex_test
        """
    )
    parser.add_argument('--tenant-id', type=str, help='Tenant ID for multi-tenancy testing')
    parser.add_argument('--db-type', type=str, choices=['sqlite', 'postgresql'], 
                       help='Database type (only used if DocEX not initialized)')
    parser.add_argument('--db-host', type=str, help='PostgreSQL host (only used if DocEX not initialized)')
    parser.add_argument('--db-port', type=int, help='PostgreSQL port (only used if DocEX not initialized)')
    parser.add_argument('--db-name', type=str, help='PostgreSQL database name (only used if DocEX not initialized)')
    parser.add_argument('--db-user', type=str, help='PostgreSQL user (only used if DocEX not initialized)')
    parser.add_argument('--db-password', type=str, help='PostgreSQL password (only used if DocEX not initialized)')
    parser.add_argument('--storage-type', type=str, choices=['filesystem', 's3'], 
                       help='Storage type (only used if DocEX not initialized)')
    parser.add_argument('--storage-path', type=str, help='Filesystem storage path (only used if DocEX not initialized)')
    parser.add_argument('--s3-bucket', type=str, help='S3 bucket name (only used if DocEX not initialized)')
    parser.add_argument('--s3-region', type=str, help='S3 region (only used if DocEX not initialized)')
    parser.add_argument('--multi-tenancy', action='store_true', 
                       help='Enable multi-tenancy (only used if DocEX not initialized)')
    
    args = parser.parse_args()
    
    print_header("DocEX Release Validation Test")
    
    # Check if DocEX is already initialized
    already_initialized = DocEX.is_initialized()
    
    if already_initialized:
        print("ℹ️  DocEX is already initialized - will validate existing setup")
        platform_settings = None  # Don't initialize, use existing
    else:
        print("ℹ️  DocEX is not initialized - will initialize with provided settings")
        
        # Build platform settings from arguments (with defaults)
        if args.db_type == 'sqlite' or args.db_type is None:
            test_dir = tempfile.mkdtemp(prefix='docex_validation_')
            db_path = str(Path(test_dir) / 'docex.db')
            storage_path = str(Path(test_dir) / 'storage')
            db_type = 'sqlite'
        else:
            test_dir = None
            db_path = None
            storage_path = args.storage_path or 'storage/docex'
            db_type = 'postgresql'
        
        platform_settings = {
            'database_type': db_type,
            'sqlite_path': db_path,
            'db_host': args.db_host or 'localhost',
            'db_port': args.db_port or 5432,
            'db_name': args.db_name or 'docex_test',
            'db_user': args.db_user or 'postgres',
            'db_password': args.db_password or '',
            'storage_type': args.storage_type or 'filesystem',
            'storage_path': storage_path,
            's3_bucket': args.s3_bucket,
            's3_region': args.s3_region or 'us-east-1',
            'multi_tenancy_enabled': args.multi_tenancy,
            'log_level': 'INFO',
            'admin_user': 'validation_test',
        }
        
        if db_type == 'sqlite':
            print(f"   Test Directory: {test_dir}")
    
    all_passed = True
    errors = []
    was_already_initialized = False
    
    # Step 1: Configuration Check/Initialization
    success, message, was_already_initialized = test_configuration_initialization(platform_settings)
    if not success:
        all_passed = False
        errors.append(f"Step 1: {message}")
        print(f"❌ {message}")
        print("\n⚠️  Cannot continue without configuration. Please fix configuration issues.")
        return 1
    
    # Step 2: Bootstrap Tenant (check if multi-tenancy is enabled in current config)
    config = DocEXConfig()
    multi_tenancy_enabled = config.get('multi_tenancy', {}).get('enabled', False)
    
    if multi_tenancy_enabled:
        success, message = test_bootstrap_tenant(admin_user='validation_test')
        if not success:
            all_passed = False
            errors.append(f"Step 2: {message}")
            print(f"❌ {message}")
    
    # Step 3: Setup Validation
    success, setup_errors = test_setup_validation()
    if not success:
        all_passed = False
        errors.extend([f"Step 3: {e}" for e in setup_errors])
    
    # Step 4: Basic Operations
    success, message = test_basic_operations(args.tenant_id)
    if not success:
        all_passed = False
        errors.append(f"Step 4: {message}")
        print(f"❌ {message}")
    
    # Summary
    print_header("Validation Summary")
    
    if was_already_initialized:
        print("ℹ️  Validated against existing DocEX configuration")
    
    if all_passed:
        print("✅ ALL VALIDATION TESTS PASSED")
        print("\nDocEX is properly set up and ready for use!")
        return 0
    else:
        print("❌ VALIDATION FAILED")
        print("\nErrors found:")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
        print("\nPlease fix the errors above and run the validation again.")
        return 1


if __name__ == '__main__':
    sys.exit(main())

