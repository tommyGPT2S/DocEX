#!/usr/bin/env python3
"""
Script to provision a new tenant in DocEX.

This script creates a new tenant with its own isolated database (SQLite) or schema (PostgreSQL).
All tables and indexes are automatically created.

Usage:
    python scripts/provision_tenant.py --tenant-id acme-corp
    python scripts/provision_tenant.py --tenant-id acme-corp --verify
    python scripts/provision_tenant.py --tenant-id acme-corp --enable-multi-tenancy
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from docex.context import UserContext
from docex.db.tenant_database_manager import TenantDatabaseManager
from docex.config.docex_config import DocEXConfig
from docex import DocEX
import yaml
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def provision_tenant(tenant_id: str, verify: bool = False, enable_multi_tenancy: bool = False):
    """
    Provision a new tenant.
    
    Args:
        tenant_id: Tenant identifier
        verify: If True, verify tenant by creating a test basket
        enable_multi_tenancy: If True, enable multi-tenancy in config if not already enabled
    """
    print(f"🚀 Provisioning tenant: {tenant_id}")
    
    # Check if multi-tenancy is enabled
    config = DocEXConfig()
    security_config = config.get('security', {})
    multi_tenancy_model = security_config.get('multi_tenancy_model', 'row_level')
    tenant_database_routing = security_config.get('tenant_database_routing', False)
    
    if multi_tenancy_model != 'database_level' or not tenant_database_routing:
        if enable_multi_tenancy:
            print("📝 Enabling database-level multi-tenancy in configuration...")
            # Update config file
            config_path = Path.home() / '.docex' / 'config.yaml'
            if not config_path.exists():
                config_path.parent.mkdir(parents=True, exist_ok=True)
                current_config = {}
            else:
                with open(config_path, 'r') as f:
                    current_config = yaml.safe_load(f) or {}
            
            if 'security' not in current_config:
                current_config['security'] = {}
            current_config['security']['multi_tenancy_model'] = 'database_level'
            current_config['security']['tenant_database_routing'] = True
            
            with open(config_path, 'w') as f:
                yaml.dump(current_config, f, default_flow_style=False)
            
            print(f"✅ Updated configuration at {config_path}")
            # Reload config
            config = DocEXConfig()
        else:
            print("❌ Error: Database-level multi-tenancy is not enabled.")
            print("   Run with --enable-multi-tenancy to enable it automatically.")
            print("   Or update your config file manually:")
            print("   security:")
            print("     multi_tenancy_model: database_level")
            print("     tenant_database_routing: true")
            return False
    
    # Get tenant database manager
    manager = TenantDatabaseManager()
    
    # Check if tenant already exists
    db_config = config.get('database', {})
    db_type = db_config.get('type', 'sqlite')
    
    if db_type in ['postgresql', 'postgres']:
        # For PostgreSQL, check if schema exists
        from sqlalchemy import inspect, text
        engine = manager.get_tenant_engine(tenant_id)
        inspector = inspect(engine)
        
        # Get schema name
        postgres_config = db_config.get('postgres', {})
        schema_template = postgres_config.get('schema_template', 'tenant_{tenant_id}')
        schema_name = schema_template.format(tenant_id=tenant_id)
        
        # Check if schema exists
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema_name"
            ), {"schema_name": schema_name})
            schema_exists = result.fetchone() is not None
        
        if schema_exists:
            print(f"⚠️  Tenant schema '{schema_name}' already exists.")
            response = input('Do you want to reinitialize it? This will drop all existing data. (y/N): ')
            if response.lower() != 'y':
                print("Aborted.")
                return False
            
            # Drop and recreate schema
            print(f"🗑️  Dropping existing schema...")
            with engine.connect() as conn:
                conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
                conn.commit()
            print(f"✅ Dropped schema '{schema_name}'")
    
    # Provision tenant (this will create schema/database and tables)
    print(f"📦 Creating tenant database/schema...")
    engine = manager.get_tenant_engine(tenant_id)
    
    # Initialize schema (creates tables and indexes)
    if db_type in ['postgresql', 'postgres']:
        postgres_config = db_config.get('postgres', {})
        schema_template = postgres_config.get('schema_template', 'tenant_{tenant_id}')
        schema_name = schema_template.format(tenant_id=tenant_id)
        manager._initialize_tenant_schema(engine, tenant_id, schema_name)
    else:
        manager._initialize_tenant_schema(engine, tenant_id)
    
    print(f"✅ Tenant '{tenant_id}' provisioned successfully!")
    
    # Verify tenant
    if verify:
        print(f"🔍 Verifying tenant...")
        user_context = UserContext(
            user_id="system",
            tenant_id=tenant_id
        )
        docex = DocEX(user_context=user_context)
        
        # Create a test basket
        test_basket_name = f"test_basket_{tenant_id}"
        basket = docex.create_basket(test_basket_name, "Test basket for tenant verification")
        print(f"✅ Created test basket: {basket.id}")
        
        # List baskets to verify
        baskets = docex.list_baskets()
        print(f"✅ Tenant has {len(baskets)} basket(s)")
    
    print(f"\n✅ Tenant '{tenant_id}' is ready to use!")
    print(f"\nUsage:")
    print(f"  from docex import DocEX")
    print(f"  from docex.context import UserContext")
    print(f"  ")
    print(f"  user_context = UserContext(user_id='user1', tenant_id='{tenant_id}')")
    print(f"  docex = DocEX(user_context=user_context)")
    print(f"  basket = docex.create_basket('my_basket')")
    
    return True


def main():
    parser = argparse.ArgumentParser(description='Provision a new tenant in DocEX')
    parser.add_argument('--tenant-id', required=True, help='Tenant ID to provision')
    parser.add_argument('--verify', action='store_true', help='Verify tenant by creating a test basket')
    parser.add_argument('--enable-multi-tenancy', action='store_true', 
                       help='Enable database-level multi-tenancy in config if not already enabled')
    
    args = parser.parse_args()
    
    try:
        success = provision_tenant(
            tenant_id=args.tenant_id,
            verify=args.verify,
            enable_multi_tenancy=args.enable_multi_tenancy
        )
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error: {str(e)}", file=sys.stderr)
        logger.exception("Tenant provisioning failed")
        sys.exit(1)


if __name__ == '__main__':
    main()

