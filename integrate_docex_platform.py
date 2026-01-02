#!/usr/bin/env python3
"""
DocEX Platform Integration Script

This script integrates DocEX into the LlamaSee-DP platform by:
1. Constructing configuration from platform settings
2. Initializing DocEX with the configuration
3. Bootstrapping the system tenant
4. Validating the setup

Based on the DocEX Platform Integration Guide.
"""

import os
import sys
import yaml
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

def build_docex_config_from_platform(platform_settings):
    """
    Construct DocEX configuration from platform system settings.

    Args:
        platform_settings: Dictionary containing platform configuration

    Returns:
        Dictionary with DocEX configuration structure
    """
    # Extract database settings from platform
    db_type = platform_settings.get('database_type', 'postgresql')  # 'sqlite' or 'postgresql'

    config = {
        'database': {
            'type': db_type,
        },
        'storage': {
            'type': platform_settings.get('storage_type', 's3'),
        },
        'logging': {
            'level': platform_settings.get('log_level', 'INFO'),
            'file': platform_settings.get('log_file', 'docex.log'),
        },
        'security': {
            'context_match_fields': platform_settings.get('context_match_fields', ['tenant_id']),
            'enforce_user_context': platform_settings.get('enforce_user_context', False),
            'multi_tenancy_model': 'database_level' if platform_settings.get('multi_tenancy_enabled', True) else 'row_level',
            'tenant_database_routing': platform_settings.get('multi_tenancy_enabled', True),
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
            'database': platform_settings.get('db_name', 'LlamaSee-DP'),
            'user': platform_settings.get('db_user', 'LlamaSee-DP-admin'),
            'password': platform_settings.get('db_password', 'L1@m@s33dp!'),
            'schema_template': platform_settings.get('schema_template', 'tenant_{tenant_id}'),
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
            'bucket': platform_settings.get('s3_bucket', 'llamasee-docex-dev'),
            'region': platform_settings.get('s3_region', 'us-east-2'),
            'application_name': platform_settings.get('application_name', 'llamasee-dp-dev'),
            'prefix': platform_settings.get('s3_prefix', ''),
            'access_key': platform_settings.get('aws_access_key'),
            'secret_key': platform_settings.get('aws_secret_key'),
        }

    # Multi-tenancy configuration is now in security section

    return config

def initialize_docex(platform_settings):
    """
    Initialize DocEX from platform settings.

    Args:
        platform_settings: Dictionary containing platform configuration

    Returns:
        True if initialization successful, False otherwise
    """
    try:
        from docex import DocEX

        # Build configuration from platform settings
        config = build_docex_config_from_platform(platform_settings)

        print("🔧 Initializing DocEX with configuration...")
        print(f"   Database: {config['database']['type']}")
        print(f"   Storage: {config['storage']['type']}")
        print(f"   Multi-tenancy: {platform_settings.get('multi_tenancy_enabled', True)}")

        # Initialize DocEX with configuration
        DocEX.setup(**config)

        print("✅ DocEX configuration initialized")
        return True

    except Exception as e:
        print(f"❌ Failed to initialize DocEX: {e}")
        import traceback
        traceback.print_exc()
        return False

def provision_system_tenant(tenant_id: str = "system", created_by: str = "platform"):
    """
    Provision the system tenant for DocEX.

    Args:
        tenant_id: System tenant ID
        created_by: User ID who is initializing the system

    Returns:
        True if provisioning successful, False otherwise
    """
    try:
        from docex.context import UserContext
        from docex.db.tenant_database_manager import TenantDatabaseManager
        from docex.config.docex_config import DocEXConfig

        print(f"🔧 Provisioning system tenant: {tenant_id}")

        # Check if multi-tenancy is properly configured
        config = DocEXConfig()
        security_config = config.get('security', {})
        multi_tenancy_model = security_config.get('multi_tenancy_model', 'row_level')
        tenant_database_routing = security_config.get('tenant_database_routing', False)

        if multi_tenancy_model != 'database_level':
            print("❌ Database-level multi-tenancy not enabled")
            return False

        if not tenant_database_routing:
            print("❌ Tenant database routing not enabled")
            return False

        # Initialize tenant database manager
        tenant_manager = TenantDatabaseManager()

        # Check if tenant already exists
        db_config = config.get('database', {})
        db_type = db_config.get('type', 'sqlite')

        tenant_exists = False
        if db_type in ['postgresql', 'postgres']:
            # For PostgreSQL, check if schema exists
            from sqlalchemy import inspect, text
            try:
                engine = tenant_manager.get_tenant_engine(tenant_id)
                postgres_config = db_config.get('postgres', {})
                schema_template = postgres_config.get('schema_template', 'tenant_{tenant_id}')
                schema_name = schema_template.format(tenant_id=tenant_id)

                # Check if schema exists
                with engine.connect() as conn:
                    result = conn.execute(text(
                        "SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema_name"
                    ), {"schema_name": schema_name})
                    tenant_exists = result.fetchone() is not None
            except:
                tenant_exists = False

        if tenant_exists:
            print(f"✅ System tenant {tenant_id} already provisioned")
            return True

        # Provision the tenant
        print(f"📦 Creating tenant database/schema for {tenant_id}...")
        tenant_manager.initialize_tenant(tenant_id, created_by=created_by)

        print(f"✅ System tenant {tenant_id} provisioned successfully")
        return True

    except Exception as e:
        print(f"❌ Failed to provision system tenant: {e}")
        import traceback
        traceback.print_exc()
        return False

def validate_docex_setup():
    """
    Validate that DocEX is properly set up and ready for use.

    Returns:
        True if properly set up, False otherwise
    """
    try:
        from docex import DocEX

        print("🔍 Validating DocEX setup...")

        # Check basic initialization
        if not DocEX.is_initialized():
            print("❌ DocEX is not initialized")
            return False

        print("   ✅ DocEX configuration loaded")
        print("   ✅ DocEX is ready for use")
        return True

    except Exception as e:
        print(f"❌ Setup validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def integrate_docex_into_platform(platform_settings):
    """
    Complete integration flow: configure, initialize, bootstrap, and validate DocEX.

    Args:
        platform_settings: Dictionary containing platform configuration

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        print("🚀 Starting DocEX Platform Integration")
        print("=" * 50)

        # Step 1: Build configuration from platform settings
        print("\n📋 Step 1: Building DocEX configuration from platform settings...")
        config = build_docex_config_from_platform(platform_settings)
        print(f"   Config built for {platform_settings.get('database_type', 'postgresql')} + {platform_settings.get('storage_type', 's3')}")

        # Debug: Print config structure
        print("   Config structure:")
        print(f"     database.type: {config.get('database', {}).get('type')}")
        print(f"     database.postgres: {config.get('database', {}).get('postgres', {})}")
        print(f"     storage.type: {config.get('storage', {}).get('type')}")
        print(f"     storage.s3: {config.get('storage', {}).get('s3', {})}")

        # Step 2: Initialize DocEX
        print("\n📋 Step 2: Initializing DocEX...")
        if not initialize_docex(platform_settings):
            return False, "DocEX initialization failed"

        # Step 3: Provision system tenant (if multi-tenancy enabled)
        multi_tenancy_enabled = platform_settings.get('multi_tenancy_enabled', True)
        if multi_tenancy_enabled:
            print("\n📋 Step 3: Provisioning system tenant...")
            if not provision_system_tenant("system", platform_settings.get('admin_user', 'platform')):
                return False, "System tenant provisioning failed"
        else:
            print("\n📋 Step 3: Multi-tenancy disabled, skipping bootstrap")

        # Step 4: Validate setup
        print("\n📋 Step 4: Validating DocEX setup...")
        if not validate_docex_setup():
            return False, "DocEX setup validation failed"

        print("\n🎉 DocEX integration successful!")
        return True, "DocEX integration successful"

    except Exception as e:
        error_msg = f"Failed to integrate DocEX: {str(e)}"
        print(f"\n❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return False, error_msg

def main():
    """Main integration function with LlamaSee-DP platform settings."""

    # LlamaSee-DP Platform Settings
    platform_settings = {
        'database_type': 'postgresql',
        'db_host': 'llamaseedevstack-llamaseedatabasef937a522-bxqrfp4gndaw.c38mmc8i03jb.us-east-2.rds.amazonaws.com',
        'db_port': 5432,
        'db_name': 'LlamaSee-DP',
        'db_user': 'LlamaSee-DP-admin',
        'db_password': 'L1@m@s33dp!',
        'schema_template': 'tenant_{tenant_id}',

        'storage_type': 's3',
        's3_bucket': 'llamasee-docex-dev',
        's3_region': 'us-east-2',
        'application_name': 'llamasee-dp-dev',
        's3_prefix': '',  # Will be built dynamically

        # AWS credentials will be loaded from ~/.aws/credentials
        'aws_access_key': None,
        'aws_secret_key': None,

        'multi_tenancy_enabled': True,
        'log_level': 'INFO',
        'log_file': 'docex.log',
        'admin_user': 'platform_admin',

        'context_match_fields': ['tenant_id'],
        'enforce_user_context': False,
    }

    print("🔧 LlamaSee-DP DocEX Integration Script")
    print("Using platform settings:")
    print(f"   Database: {platform_settings['db_host']}:{platform_settings['db_port']}/{platform_settings['db_name']}")
    print(f"   Storage: s3://{platform_settings['s3_bucket']} (region: {platform_settings['s3_region']})")
    print(f"   Application: {platform_settings['application_name']}")
    print(f"   Multi-tenancy: {platform_settings['multi_tenancy_enabled']}")
    print()

    success, message = integrate_docex_into_platform(platform_settings)

    if success:
        print(f"\n✅ Integration successful: {message}")
        print("\n📋 Next Steps:")
        print("   1. Provision business tenants using TenantProvisioner")
        print("   2. Create DocEX instances with UserContext")
        print("   3. Create baskets and add documents")
        print("   4. Test tenant isolation")
        return 0
    else:
        print(f"\n❌ Integration failed: {message}")
        return 1

if __name__ == "__main__":
    sys.exit(main())