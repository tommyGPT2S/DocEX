#!/usr/bin/env python3
"""
Simple test for DocEX initialization and tenant provisioning

Usage:
    python test_init_simple.py [tenant_id]

    If tenant_id is provided, it will be used for provisioning and testing.
    If not provided, defaults to 'test_tenant_001'.
"""

import sys
import os
import tempfile
import shutil
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from docex import DocEX
from docex.config.docex_config import DocEXConfig
from docex.context import UserContext
from docex.provisioning.bootstrap import BootstrapTenantManager
from docex.provisioning.tenant_provisioner import TenantProvisioner
from docex.db.tenant_registry_model import TenantRegistry
from docex.db.connection import Database

def main(tenant_id: str = None, db_type: str = 'sqlite'):
    print("=" * 70)
    print("Simple DocEX Initialization and Tenant Provisioning Test")
    print("=" * 70)
    print(f"Database type: {db_type}")
    
    # Create temporary directory for test (only used for SQLite)
    test_dir = tempfile.mkdtemp(prefix='docex_test_')
    print(f"\n📁 Test directory: {test_dir}")
    
    try:
        # Step 1: Initialize DocEX configuration
        print("\n" + "-" * 70)
        print("STEP 1: Initialize DocEX Configuration")
        print("-" * 70)
        
        config = DocEXConfig()
        
        if db_type == 'postgresql' or db_type == 'postgres':
            # PostgreSQL configuration
            config.setup(
                database={
                    'type': 'postgresql',
                    'postgres': {
                        'host': 'localhost',
                        'port': 5433,
                        'database': 'docex_test',
                        'user': 'docex_test',
                        'password': 'docex_test_password'
                    }
                },
                storage={
                    'type': 'filesystem',
                    'filesystem': {
                        'path': str(Path(test_dir) / 'storage')
                    }
                },
                multi_tenancy={
                    'enabled': True,
                    'isolation_strategy': 'schema',
                    'bootstrap_tenant': {
                        'id': '_docex_system_',
                        'display_name': 'DocEX System',
                        'schema': 'docex_system',
                        'database_path': None
                    }
                }
            )
        else:
            # SQLite configuration
            config.setup(
                database={
                    'type': 'sqlite',
                    'sqlite': {
                        'path': str(Path(test_dir) / 'docex.db')
                    }
                },
                storage={
                    'type': 'filesystem',
                    'filesystem': {
                        'path': str(Path(test_dir) / 'storage')
                    }
                },
                multi_tenancy={
                    'enabled': True,
                    'isolation_strategy': 'database',
                    'bootstrap_tenant': {
                        'id': '_docex_system_',
                        'display_name': 'DocEX System',
                        'schema': 'docex_system',
                        'database_path': str(Path(test_dir) / '_docex_system_' / 'docex.db')
                    }
                }
            )
        
        print("✅ DocEX configuration initialized")
        print(f"   Database type: {config.get('database', {}).get('type')}")
        
        # Step 2: Initialize bootstrap tenant
        print("\n" + "-" * 70)
        print("STEP 2: Initialize Bootstrap Tenant")
        print("-" * 70)
        
        # Clear any cached tenant database connections to ensure we use the test config
        from docex.db.tenant_database_manager import TenantDatabaseManager
        tenant_manager = TenantDatabaseManager()
        tenant_manager.close_all_connections()
        
        bootstrap_manager = BootstrapTenantManager(config=config)
        
        # Check if already initialized (in the test-specific location)
        is_initialized = bootstrap_manager.is_initialized()
        print(f"   Bootstrap tenant initialized: {is_initialized}")
        
        # Also check if the database file/schema exists at the expected location
        if config.get('database', {}).get('type') == 'sqlite':
            expected_db_path = config.get('multi_tenancy', {}).get('bootstrap_tenant', {}).get('database_path')
            if expected_db_path:
                if os.path.exists(expected_db_path):
                    print(f"   ✅ Bootstrap database file exists at expected location: {expected_db_path}")
                else:
                    print(f"   ⚠️  Bootstrap database file NOT at expected location: {expected_db_path}")
                    print(f"   (Will initialize in test-specific location)")
                    # Force re-initialization if file doesn't exist at expected location
                    is_initialized = False
        elif config.get('database', {}).get('type') in ['postgresql', 'postgres']:
            # For PostgreSQL, check if schema exists
            schema_name = config.get('multi_tenancy', {}).get('bootstrap_tenant', {}).get('schema', 'docex_system')
            try:
                from sqlalchemy import inspect
                inspector = inspect(bootstrap_manager.db.get_engine())
                schemas = inspector.get_schema_names()
                if schema_name in schemas:
                    print(f"   ✅ PostgreSQL schema '{schema_name}' exists")
                else:
                    print(f"   ⚠️  PostgreSQL schema '{schema_name}' NOT found")
                    print(f"   (Will force re-initialization)")
                    is_initialized = False
            except Exception as e:
                print(f"   ⚠️  Could not check PostgreSQL schema: {e}")
                is_initialized = False
        
        if not is_initialized:
            print("   Initializing bootstrap tenant...")
            print(f"   - Database type: {config.get('database', {}).get('type')}")
            if config.get('database', {}).get('type') in ['postgresql', 'postgres']:
                schema_name = config.get('multi_tenancy', {}).get('bootstrap_tenant', {}).get('schema', 'docex_system')
                print(f"   - Will create PostgreSQL schema: {schema_name}")
            elif config.get('database', {}).get('type') == 'sqlite':
                db_path = config.get('multi_tenancy', {}).get('bootstrap_tenant', {}).get('database_path')
                print(f"   - Will create SQLite database: {db_path}")
            bootstrap_manager.initialize(created_by='test_user')
            print("✅ Bootstrap tenant initialized")
            
            # Verify what was actually created
            if config.get('database', {}).get('type') == 'sqlite':
                db_path = config.get('multi_tenancy', {}).get('bootstrap_tenant', {}).get('database_path')
                if db_path and os.path.exists(db_path):
                    print(f"   ✅ Verified: SQLite database file exists at {db_path}")
                elif db_path:
                    print(f"   ⚠️  Warning: SQLite database file NOT found at {db_path}")
            elif config.get('database', {}).get('type') in ['postgresql', 'postgres']:
                schema_name = config.get('multi_tenancy', {}).get('bootstrap_tenant', {}).get('schema', 'docex_system')
                print(f"   ✅ Should have created PostgreSQL schema: {schema_name}")
                print(f"   (Check with: psql -d {config.get('database', {}).get('postgres', {}).get('database')} -c '\\dn')")
        else:
            print("✅ Bootstrap tenant already initialized")
        
        # Verify bootstrap tenant exists and show what was created
        bootstrap_db = Database(config=config, tenant_id='_docex_system_')
        
        # Print bootstrap database details
        print(f"\n   Bootstrap tenant database details:")
        print(f"   - Database type: {config.get('database', {}).get('type')}")
        if config.get('database', {}).get('type') == 'sqlite':
            bootstrap_db_path = config.get('multi_tenancy', {}).get('bootstrap_tenant', {}).get('database_path')
            if bootstrap_db_path:
                print(f"   - Expected database path: {bootstrap_db_path}")
                if os.path.exists(bootstrap_db_path):
                    file_size = os.path.getsize(bootstrap_db_path)
                    print(f"   - ✅ Database file EXISTS ({file_size} bytes)")
                else:
                    print(f"   - ❌ Database file does NOT exist at expected path")
                    # Check if it's in a different location
                    parent_dir = Path(bootstrap_db_path).parent
                    if parent_dir.exists():
                        print(f"   - Parent directory exists: {parent_dir}")
                        print(f"   - Files in parent: {list(parent_dir.iterdir())}")
        elif config.get('database', {}).get('type') in ['postgresql', 'postgres']:
            schema_name = config.get('multi_tenancy', {}).get('bootstrap_tenant', {}).get('schema', 'docex_system')
            print(f"   - Schema name: {schema_name}")
            print(f"   - Database: {config.get('database', {}).get('postgres', {}).get('database')}")
            print(f"   - Host: {config.get('database', {}).get('postgres', {}).get('host')}")
            print(f"   - Port: {config.get('database', {}).get('postgres', {}).get('port')}")
            print(f"   - To verify schema exists, run:")
            print(f"     psql -d {config.get('database', {}).get('postgres', {}).get('database')} -c '\\dn'")
        
        print(f"   - Engine URL: {bootstrap_db.engine.url if hasattr(bootstrap_db.engine, 'url') else 'N/A'}")
        
        with bootstrap_db.session() as session:
            bootstrap_tenant = session.query(TenantRegistry).filter_by(
                tenant_id='_docex_system_'
            ).first()
            assert bootstrap_tenant is not None, "Bootstrap tenant should exist"
            print(f"✅ Bootstrap tenant verified: {bootstrap_tenant.tenant_id}")
            print(f"   - Display name: {bootstrap_tenant.display_name}")
            print(f"   - Isolation strategy: {bootstrap_tenant.isolation_strategy}")
            print(f"   - Schema name: {bootstrap_tenant.schema_name}")
            print(f"   - Database path: {bootstrap_tenant.database_path}")
        
        # Step 3: Provision a new tenant
        print("\n" + "-" * 70)
        print("STEP 3: Provision New Tenant")
        print("-" * 70)
        
        # Clear any cached tenant database connections before provisioning
        tenant_manager.close_all_connections()
        
        provisioner = TenantProvisioner(config=config)
        
        # Use provided tenant_id or default
        if tenant_id is None:
            tenant_id = 'test_tenant_001'
        display_name = f'Test Tenant {tenant_id}'
        
        # Check if tenant already exists
        with bootstrap_db.session() as session:
            existing = session.query(TenantRegistry).filter_by(tenant_id=tenant_id).first()
            if existing:
                print(f"⚠️  Tenant '{tenant_id}' already exists, skipping provisioning")
                print(f"   (This is expected if running the test multiple times)")
            else:
                print(f"   Provisioning tenant: {tenant_id}")
                provisioner.create(
                    tenant_id=tenant_id,
                    display_name=display_name,
                    created_by='test_user'
                )
                print(f"✅ Tenant '{tenant_id}' provisioned successfully")
        
        # Verify tenant exists in registry
        with bootstrap_db.session() as session:
            tenant = session.query(TenantRegistry).filter_by(tenant_id=tenant_id).first()
            assert tenant is not None, f"Tenant '{tenant_id}' should exist in registry"
            print(f"✅ Tenant verified in registry:")
            print(f"   Tenant ID: {tenant.tenant_id}")
            print(f"   Display name: {tenant.display_name}")
        
        # Close bootstrap_db to ensure all transactions are committed
        bootstrap_db.close()
        
        # Step 4: Use the provisioned tenant
        print("\n" + "-" * 70)
        print("STEP 4: Use Provisioned Tenant")
        print("-" * 70)
        
        user_context = UserContext(user_id='test_user', tenant_id=tenant_id)
        
        # Initialize DocEX with tenant context
        print(f"   Initializing DocEX for tenant: {tenant_id}")
        try:
            docex = DocEX(user_context=user_context)
            print("✅ DocEX initialized for tenant")
        except ValueError as e:
            if "not provisioned" in str(e) or "not found" in str(e):
                print(f"⚠️  Tenant validation failed: {e}")
                print(f"   Re-verifying tenant exists in registry...")
                # Re-open bootstrap_db and verify tenant exists
                bootstrap_db = Database(config=config, tenant_id='_docex_system_')
                with bootstrap_db.session() as session:
                    tenant = session.query(TenantRegistry).filter_by(tenant_id=tenant_id).first()
                    if tenant:
                        print(f"   ✅ Tenant exists in registry, retrying DocEX initialization...")
                        # Retry with a fresh DocEX instance
                        DocEX.close()  # Reset singleton
                        docex = DocEX(user_context=user_context)
                        print("✅ DocEX initialized for tenant (after retry)")
                    else:
                        raise ValueError(f"Tenant '{tenant_id}' not found in registry after provisioning")
            else:
                raise
        
        # Create a basket (use unique name to avoid conflicts from previous runs)
        import time
        basket_name = f'test_basket_{int(time.time())}'
        print(f"\n   Creating basket in tenant '{tenant_id}'...")
        print(f"   Basket name: {basket_name}")
        try:
            basket = docex.create_basket(basket_name, 'Test basket description')
            print(f"✅ Basket created: {basket.id}")
            print(f"   Basket name: {basket.name}")
        except ValueError as e:
            if "already exists" in str(e):
                print(f"⚠️  Basket '{basket_name}' already exists, trying with different name...")
                # Try with a more unique name
                basket_name = f'test_basket_{int(time.time())}_{tenant_id}'
                basket = docex.create_basket(basket_name, 'Test basket description')
                print(f"✅ Basket created: {basket.id}")
                print(f"   Basket name: {basket.name}")
            else:
                print(f"❌ Failed to create basket: {e}")
                import traceback
                traceback.print_exc()
                raise
        except Exception as e:
            print(f"❌ Failed to create basket: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Skip cleanup - keep test directory for inspection
        print(f"\n📁 Test directory preserved for inspection: {test_dir}")
        db_type = config.get('database', {}).get('type')
        if db_type == 'sqlite':
            print(f"   Bootstrap tenant database should be at: {Path(test_dir) / '_docex_system_' / 'docex.db'}")
            print(f"   Tenant databases should be in: {Path(test_dir) / 'tenant_*' / 'docex.db'}")
        elif db_type in ['postgresql', 'postgres']:
            schema_name = config.get('multi_tenancy', {}).get('bootstrap_tenant', {}).get('schema', 'docex_system')
            db_name = config.get('database', {}).get('postgres', {}).get('database')
            print(f"   Bootstrap tenant schema: {schema_name}")
            print(f"   Database: {db_name}")
            print(f"   To inspect schemas, run:")
            print(f"     psql -h localhost -p 5433 -U docex_test -d {db_name} -c '\\dn'")
        print(f"   Storage files should be in: {Path(test_dir) / 'storage'}")
        print("\n   To clean up manually, run:")
        if db_type == 'sqlite':
            print(f"   rm -rf {test_dir}")
        else:
            print(f"   rm -rf {test_dir}  # (SQLite files only)")
            print(f"   # PostgreSQL data persists in Docker volume")
    
    return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Test DocEX initialization and tenant provisioning',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_init_simple.py                    # Uses default tenant 'test_tenant_001'
  python test_init_simple.py my_tenant          # Uses 'my_tenant' as tenant_id
  python test_init_simple.py acme_corp          # Uses 'acme_corp' as tenant_id
        """
    )
    parser.add_argument(
        'tenant_id',
        nargs='?',
        default=None,
        help='Tenant ID to provision and test (default: test_tenant_001)'
    )
    parser.add_argument(
        '--db-type',
        choices=['sqlite', 'postgresql', 'postgres'],
        default='sqlite',
        help='Database type to use (default: sqlite)'
    )
    
    args = parser.parse_args()
    
    tenant_id_display = args.tenant_id if args.tenant_id else 'test_tenant_001 (default)'
    print(f"Using tenant_id: {tenant_id_display}")
    print(f"Using database type: {args.db_type}")
    print()
    
    # Check PostgreSQL connection if using PostgreSQL
    if args.db_type in ['postgresql', 'postgres']:
        print("Checking PostgreSQL connection...")
        try:
            import psycopg2
            conn = psycopg2.connect(
                host='localhost',
                port=5433,
                database='docex_test',
                user='docex_test',
                password='docex_test_password'
            )
            conn.close()
            print("✅ PostgreSQL connection successful")
            print()
        except ImportError:
            print("❌ ERROR: psycopg2 not installed. Install with: pip install psycopg2-binary")
            sys.exit(1)
        except Exception as e:
            print(f"❌ ERROR: Cannot connect to PostgreSQL: {e}")
            print("   Make sure PostgreSQL is running (docker-compose -f docker-compose.test.yml up -d)")
            sys.exit(1)
    
    success = main(tenant_id=args.tenant_id, db_type=args.db_type)
    sys.exit(0 if success else 1)

