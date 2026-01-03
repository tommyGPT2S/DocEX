#!/usr/bin/env python3
"""
Test DocEX Initialization and Tenant Provisioning

Tests the complete flow:
1. DocEX initialization
2. Bootstrap tenant setup
3. Tenant provisioning
4. Using provisioned tenant

Usage:
    python test_initialization_and_provisioning.py [tenant_id]

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

def test_sqlite_initialization_and_provisioning(tenant_id: str = None):
    """Test SQLite initialization and tenant provisioning"""
    print("=" * 70)
    print("TEST: SQLite Initialization and Tenant Provisioning")
    print("=" * 70)
    
    # Create temporary directory for test
    test_dir = tempfile.mkdtemp(prefix='docex_test_')
    print(f"\n📁 Test directory: {test_dir}")
    
    try:
        # Step 1: Initialize DocEX configuration
        print("\n" + "-" * 70)
        print("STEP 1: Initialize DocEX Configuration")
        print("-" * 70)
        
        config = DocEXConfig()
        config.setup(
            database={
                'type': 'sqlite',
                'sqlite': {
                    'path': str(Path(test_dir) / 'docex.db')
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
        
        # Step 2: Initialize bootstrap tenant
        print("\n" + "-" * 70)
        print("STEP 2: Initialize Bootstrap Tenant")
        print("-" * 70)
        
        bootstrap_manager = BootstrapTenantManager()
        
        # Check if already initialized
        is_initialized = bootstrap_manager.is_initialized()
        print(f"   Bootstrap tenant initialized: {is_initialized}")
        
        if not is_initialized:
            print("   Initializing bootstrap tenant...")
            bootstrap_manager.initialize(created_by='test_user')
            print("✅ Bootstrap tenant initialized")
        else:
            print("✅ Bootstrap tenant already initialized")
        
        # Verify bootstrap tenant exists
        bootstrap_db = Database(config=config, tenant_id='_docex_system_')
        with bootstrap_db.session() as session:
            bootstrap_tenant = session.query(TenantRegistry).filter_by(
                tenant_id='_docex_system_'
            ).first()
            assert bootstrap_tenant is not None, "Bootstrap tenant should exist"
            print(f"✅ Bootstrap tenant verified: {bootstrap_tenant.tenant_id}")
            print(f"   Display name: {bootstrap_tenant.display_name}")
            print(f"   Is system: {bootstrap_tenant.is_system}")
            print(f"   Isolation strategy: {bootstrap_tenant.isolation_strategy}")
        
        # Step 3: Provision a new tenant
        print("\n" + "-" * 70)
        print("STEP 3: Provision New Tenant")
        print("-" * 70)
        
        provisioner = TenantProvisioner()
        
        # Use provided tenant_id or default
        if tenant_id is None:
            tenant_id = 'test_tenant_001'
        display_name = f'Test Tenant {tenant_id}'
        
        # Check if tenant already exists
        with bootstrap_db.session() as session:
            existing = session.query(TenantRegistry).filter_by(tenant_id=tenant_id).first()
            if existing:
                print(f"⚠️  Tenant '{tenant_id}' already exists, skipping provisioning")
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
            print(f"   Isolation strategy: {tenant.isolation_strategy}")
            print(f"   Database path: {tenant.database_path}")
        
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
                    else:
                        raise ValueError(f"Tenant '{tenant_id}' not found in registry after provisioning")
            else:
                raise
        print("✅ DocEX initialized for tenant")
        
        # Verify DocEX is properly set up
        is_setup = DocEX.is_properly_setup()
        print(f"   DocEX properly set up: {is_setup}")
        
        # Create a basket
        print(f"   Creating basket in tenant '{tenant_id}'...")
        basket = docex.create_basket('test_basket', 'Test basket description')
        print(f"✅ Basket created: {basket.id}")
        print(f"   Basket name: {basket.name}")
        
        # List tenants
        print("\n" + "-" * 70)
        print("STEP 5: List All Tenants")
        print("-" * 70)
        
        with bootstrap_db.session() as session:
            all_tenants = session.query(TenantRegistry).all()
            print(f"✅ Found {len(all_tenants)} tenant(s) in registry:")
            for t in all_tenants:
                print(f"   - {t.tenant_id}: {t.display_name} (system: {t.is_system})")
        
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        print(f"\n🧹 Cleaning up test directory: {test_dir}")
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        print("✅ Cleanup complete")

def test_postgres_initialization_and_provisioning(tenant_id: str = None):
    """Test PostgreSQL initialization and tenant provisioning"""
    print("\n" + "=" * 70)
    print("TEST: PostgreSQL Initialization and Tenant Provisioning")
    print("=" * 70)
    
    try:
        # Step 1: Initialize DocEX configuration for PostgreSQL
        print("\n" + "-" * 70)
        print("STEP 1: Initialize DocEX Configuration (PostgreSQL)")
        print("-" * 70)
        
        config = DocEXConfig()
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
        print("✅ DocEX configuration initialized for PostgreSQL")
        
        # Step 2: Initialize bootstrap tenant
        print("\n" + "-" * 70)
        print("STEP 2: Initialize Bootstrap Tenant (PostgreSQL)")
        print("-" * 70)
        
        bootstrap_manager = BootstrapTenantManager()
        
        # Check if already initialized
        is_initialized = bootstrap_manager.is_initialized()
        print(f"   Bootstrap tenant initialized: {is_initialized}")
        
        if not is_initialized:
            print("   Initializing bootstrap tenant...")
            bootstrap_manager.initialize(created_by='test_user')
            print("✅ Bootstrap tenant initialized")
        else:
            print("✅ Bootstrap tenant already initialized")
        
        # Step 3: Provision a new tenant
        print("\n" + "-" * 70)
        print("STEP 3: Provision New Tenant (PostgreSQL)")
        print("-" * 70)
        
        provisioner = TenantProvisioner()
        
        # Use provided tenant_id or default
        if tenant_id is None:
            tenant_id = 'test_tenant_pg_001'
        display_name = f'Test Tenant {tenant_id}'
        
        # Check if tenant already exists
        bootstrap_db = Database(config=config, tenant_id='_docex_system_')
        with bootstrap_db.session() as session:
            existing = session.query(TenantRegistry).filter_by(tenant_id=tenant_id).first()
            if existing:
                print(f"⚠️  Tenant '{tenant_id}' already exists, skipping provisioning")
            else:
                print(f"   Provisioning tenant: {tenant_id}")
                provisioner.create(
                    tenant_id=tenant_id,
                    display_name=display_name,
                    created_by='test_user'
                )
                print(f"✅ Tenant '{tenant_id}' provisioned successfully")
        
        # Step 4: Use the provisioned tenant
        print("\n" + "-" * 70)
        print("STEP 4: Use Provisioned Tenant (PostgreSQL)")
        print("-" * 70)
        
        user_context = UserContext(user_id='test_user', tenant_id=tenant_id)
        
        # Initialize DocEX with tenant context
        print(f"   Initializing DocEX for tenant: {tenant_id}")
        docex = DocEX(user_context=user_context)
        print("✅ DocEX initialized for tenant")
        
        # Create a basket
        print(f"   Creating basket in tenant '{tenant_id}'...")
        basket = docex.create_basket('test_basket_pg', 'Test basket description')
        print(f"✅ Basket created: {basket.id}")
        
        print("\n" + "=" * 70)
        print("✅ POSTGRESQL TESTS PASSED")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ POSTGRESQL TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("DocEX Initialization and Tenant Provisioning Test Suite")
    print("=" * 70)
    
    results = []
    
    # Test SQLite
    try:
        result = test_sqlite_initialization_and_provisioning()
        results.append(('SQLite', result))
    except Exception as e:
        print(f"\n❌ SQLite test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(('SQLite', False))
    
    # Test PostgreSQL (if available)
    try:
        # Check if PostgreSQL is available
        from docex.db.connection import Database
        test_config = DocEXConfig()
        test_config.setup(
            database={
                'type': 'postgresql',
                'postgres': {
                    'host': 'localhost',
                    'port': 5433,
                    'database': 'docex_test',
                    'user': 'docex_test',
                    'password': 'docex_test_password'
                }
            }
        )
        
        # Try to connect
        try:
            test_db = Database(config=test_config)
            test_db.close()
            print("\n✅ PostgreSQL is available, running PostgreSQL tests...")
            result = test_postgres_initialization_and_provisioning(tenant_id=args.tenant_id)
            results.append(('PostgreSQL', result))
        except Exception as e:
            print(f"\n⚠️  PostgreSQL not available: {e}")
            print("   Skipping PostgreSQL tests")
            results.append(('PostgreSQL', None))
    except Exception as e:
        print(f"\n⚠️  PostgreSQL test setup failed: {e}")
        results.append(('PostgreSQL', None))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    for db_type, result in results:
        if result is True:
            print(f"  ✅ {db_type}: PASSED")
        elif result is False:
            print(f"  ❌ {db_type}: FAILED")
        else:
            print(f"  ⚠️  {db_type}: SKIPPED")
    
    # Exit with error if any test failed
    if any(result is False for _, result in results):
        sys.exit(1)
    else:
        print("\n✅ All tests completed successfully!")

