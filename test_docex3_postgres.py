#!/usr/bin/env python3
"""
PostgreSQL Integration Test for DocEX 3.0 Multi-Tenancy

Tests the complete flow against a real PostgreSQL database:
1. Bootstrap tenant initialization
2. Tenant provisioning (5-step process)
3. Tenant registry queries
4. Runtime usage with UserContext
5. Setup validation

Prerequisites:
- Docker running
- docker-compose installed

Run this script to test with PostgreSQL:
    docker-compose -f docker-compose.test.yml up -d
    python test_docex3_postgres.py
    docker-compose -f docker-compose.test.yml down
"""

import sys
import tempfile
import shutil
import time
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))


def check_postgres_connection():
    """Check if PostgreSQL is accessible"""
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
        return True
    except Exception as e:
        print(f"   ⚠️  PostgreSQL connection failed: {e}")
        print("   💡 Make sure Docker PostgreSQL is running:")
        print("      docker-compose -f docker-compose.test.yml up -d")
        return False


def test_bootstrap_tenant_initialization_postgres():
    """Test bootstrap tenant initialization with PostgreSQL"""
    print("\n" + "="*60)
    print("TEST 1: Bootstrap Tenant Initialization (PostgreSQL)")
    print("="*60)
    
    test_dir = None
    try:
        from docex.provisioning.bootstrap import BootstrapTenantManager
        from docex.config.docex_config import DocEXConfig
        
        # Create temporary test directory for storage
        test_dir = tempfile.mkdtemp()
        
        # Set up PostgreSQL test config using setup() method
        # This properly initializes config and saves it to file
        DocEXConfig.setup(
            database={
                'type': 'postgres',
                'postgres': {
                    'host': 'localhost',
                    'port': 5433,
                    'database': 'docex_test',
                    'user': 'docex_test',
                    'password': 'docex_test_password',
                    'schema_template': 'tenant_{tenant_id}'
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
                    'schema': 'docex_system'
                }
            }
        )
        
        # Get the configured instance
        config = DocEXConfig()
        
        print("\n1.1 Creating BootstrapTenantManager...")
        bootstrap_manager = BootstrapTenantManager(config)
        print("   ✅ BootstrapTenantManager created")
        
        print("\n1.2 Checking if bootstrap tenant is initialized...")
        is_initialized = bootstrap_manager.is_initialized()
        print(f"   Initialized: {is_initialized}")
        
        if not is_initialized:
            print("\n1.3 Initializing bootstrap tenant...")
            tenant_registry = bootstrap_manager.initialize(created_by='test_user')
            print(f"   ✅ Bootstrap tenant initialized: {tenant_registry.tenant_id}")
            print(f"   Display name: {tenant_registry.display_name}")
            print(f"   Is system: {tenant_registry.is_system}")
            print(f"   Isolation strategy: {tenant_registry.isolation_strategy}")
            print(f"   Schema name: {tenant_registry.schema_name}")
        else:
            print("   ✅ Bootstrap tenant already initialized")
            # Get the bootstrap tenant from the registry
            tenant_registry = bootstrap_manager.initialize(created_by='test_user')
            if tenant_registry:
                print(f"   Tenant ID: {tenant_registry.tenant_id}")
                print(f"   Display name: {tenant_registry.display_name}")
                print(f"   Schema name: {tenant_registry.schema_name}")
            else:
                print("   ⚠️  Could not retrieve bootstrap tenant from registry")
        
        print("\n   ✅ Bootstrap tenant initialization test passed!")
        return True, test_dir
        
    except Exception as e:
        print(f"\n   ❌ Bootstrap tenant initialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, test_dir


def test_tenant_provisioning_postgres(test_dir):
    """Test tenant provisioning with PostgreSQL"""
    print("\n" + "="*60)
    print("TEST 2: Tenant Provisioning (PostgreSQL)")
    print("="*60)
    
    try:
        from docex.provisioning.tenant_provisioner import TenantProvisioner, TenantExistsError
        from docex.config.docex_config import DocEXConfig
        
        # Set up PostgreSQL test config using setup() method
        DocEXConfig.setup(
            database={
                'type': 'postgres',
                'postgres': {
                    'host': 'localhost',
                    'port': 5433,
                    'database': 'docex_test',
                    'user': 'docex_test',
                    'password': 'docex_test_password',
                    'schema_template': 'tenant_{tenant_id}'
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
                    'schema': 'docex_system'
                }
            }
        )
        
        # Get the configured instance
        config = DocEXConfig()
        
        print("\n2.1 Creating TenantProvisioner...")
        provisioner = TenantProvisioner(config)
        print("   ✅ TenantProvisioner created")
        
        print("\n2.2 Provisioning test tenant 'acme'...")
        # Check if tenant already exists (from previous test run)
        from docex.db.connection import Database
        from docex.db.tenant_registry_model import TenantRegistry
        bootstrap_db = Database(config=config, tenant_id='_docex_system_')
        with bootstrap_db.session() as session:
            existing = session.query(TenantRegistry).filter_by(tenant_id='acme').first()
            if existing:
                print("   ℹ️  Tenant 'acme' already exists, skipping creation")
                tenant_registry = existing
            else:
                tenant_registry = provisioner.create(
                    tenant_id='acme',
                    display_name='Acme Corporation',
                    created_by='test_user'
                )
        print(f"   ✅ Tenant provisioned: {tenant_registry.tenant_id}")
        print(f"   Display name: {tenant_registry.display_name}")
        print(f"   Isolation strategy: {tenant_registry.isolation_strategy}")
        print(f"   Schema name: {tenant_registry.schema_name}")
        
        print("\n2.3 Attempting to provision duplicate tenant...")
        try:
            provisioner.create(
                tenant_id='acme',
                display_name='Acme Corp Duplicate',
                created_by='test_user'
            )
            print("   ❌ Should have raised TenantExistsError")
            return False
        except TenantExistsError:
            print("   ✅ Correctly rejected duplicate tenant")
        
        print("\n2.4 Provisioning another tenant 'contoso'...")
        # Check if tenant already exists (from previous test run)
        bootstrap_db = Database(config=config, tenant_id='_docex_system_')
        with bootstrap_db.session() as session:
            existing = session.query(TenantRegistry).filter_by(tenant_id='contoso').first()
            if existing:
                print("   ℹ️  Tenant 'contoso' already exists, skipping creation")
                tenant_registry2 = existing
            else:
                tenant_registry2 = provisioner.create(
                    tenant_id='contoso',
                    display_name='Contoso Ltd',
                    created_by='test_user'
                )
        print(f"   ✅ Second tenant provisioned: {tenant_registry2.tenant_id}")
        print(f"   Schema name: {tenant_registry2.schema_name}")
        
        print("\n   ✅ Tenant provisioning test passed!")
        return True
        
    except Exception as e:
        print(f"\n   ❌ Tenant provisioning test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tenant_registry_queries_postgres(test_dir):
    """Test tenant registry queries with PostgreSQL"""
    print("\n" + "="*60)
    print("TEST 3: Tenant Registry Queries (PostgreSQL)")
    print("="*60)
    
    try:
        from docex.db.connection import Database
        from docex.db.tenant_registry_model import TenantRegistry
        from docex.config.docex_config import DocEXConfig
        
        # Set up PostgreSQL test config
        # Create config with test values directly
        config = DocEXConfig.__new__(DocEXConfig)
        config.config = {}
        config.config['database'] = {
            'type': 'postgres',
            'postgres': {
                'host': 'localhost',
                'port': 5433,
                'database': 'docex_test',
                'user': 'docex_test',
                'password': 'docex_test_password',
                'schema_template': 'tenant_{tenant_id}'
            }
        }
        config.config['multi_tenancy'] = {
            'enabled': True,
            'bootstrap_tenant': {
                'id': '_docex_system_'
            }
        }
        
        print("\n3.1 Querying tenant registry...")
        bootstrap_db = Database(config=config, tenant_id='_docex_system_')
        
        with bootstrap_db.session() as session:
            # Get all tenants
            all_tenants = session.query(TenantRegistry).all()
            print(f"   Found {len(all_tenants)} tenants in registry:")
            for tenant in all_tenants:
                print(f"     - {tenant.tenant_id}: {tenant.display_name} (system: {tenant.is_system})")
                if tenant.schema_name:
                    print(f"       Schema: {tenant.schema_name}")
            
            # Get bootstrap tenant
            bootstrap = session.query(TenantRegistry).filter_by(
                tenant_id='_docex_system_'
            ).first()
            if bootstrap:
                assert bootstrap.is_system, "Bootstrap tenant should be marked as system"
                print(f"\n   ✅ Bootstrap tenant found: {bootstrap.tenant_id}")
                print(f"   Schema: {bootstrap.schema_name}")
            else:
                print(f"\n   ⚠️  Bootstrap tenant not in registry")
            
            # Get business tenant
            acme = session.query(TenantRegistry).filter_by(
                tenant_id='acme'
            ).first()
            assert acme is not None, "Acme tenant should exist"
            assert not acme.is_system, "Acme tenant should not be system tenant"
            print(f"   ✅ Business tenant found: {acme.tenant_id}")
            print(f"   Schema: {acme.schema_name}")
            
            # Get second business tenant
            contoso = session.query(TenantRegistry).filter_by(
                tenant_id='contoso'
            ).first()
            assert contoso is not None, "Contoso tenant should exist"
            print(f"   ✅ Second business tenant found: {contoso.tenant_id}")
            print(f"   Schema: {contoso.schema_name}")
        
        print("\n   ✅ Tenant registry queries test passed!")
        return True
        
    except Exception as e:
        print(f"\n   ❌ Tenant registry queries test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_runtime_usage_postgres(test_dir):
    """Test runtime usage with UserContext and PostgreSQL"""
    print("\n" + "="*60)
    print("TEST 4: Runtime Usage with UserContext (PostgreSQL)")
    print("="*60)
    
    try:
        from docex import DocEX
        from docex.context import UserContext
        from docex.config.docex_config import DocEXConfig
        
        # Set up PostgreSQL test config
        # Create config with test values directly
        config = DocEXConfig.__new__(DocEXConfig)
        config.config = {}
        config.config['database'] = {
            'type': 'postgres',
            'postgres': {
                'host': 'localhost',
                'port': 5433,
                'database': 'docex_test',
                'user': 'docex_test',
                'password': 'docex_test_password',
                'schema_template': 'tenant_{tenant_id}'
            }
        }
        config.config['storage'] = {
            'type': 'filesystem',
            'filesystem': {
                'path': str(Path(test_dir) / 'storage')
            }
        }
        config.config['multi_tenancy'] = {
            'enabled': True,
            'isolation_strategy': 'schema'
        }
        # Mark as initialized to skip validation
        config.initialized = True
        
        # Initialize DocEX config
        DocEXConfig.setup(**config.config)
        
        print("\n4.1 Testing DocEX initialization without UserContext (should fail)...")
        try:
            doc_ex = DocEX()
            print("   ❌ Should have raised ValueError")
            return False
        except ValueError as e:
            print(f"   ✅ Correctly rejected: {e}")
        
        print("\n4.2 Testing DocEX initialization with bootstrap tenant (should fail)...")
        try:
            user_context = UserContext(
                user_id='test_user',
                tenant_id='_docex_system_',
                roles=['admin']
            )
            doc_ex = DocEX(user_context=user_context)
            print("   ❌ Should have raised ValueError (bootstrap tenant not for business)")
            return False
        except ValueError as e:
            print(f"   ✅ Correctly rejected bootstrap tenant: {e}")
        
        print("\n4.3 Testing DocEX initialization with valid business tenant...")
        user_context = UserContext(
            user_id='test_user',
            tenant_id='acme',
            roles=['user']
        )
        doc_ex = DocEX(user_context=user_context)
        print(f"   ✅ DocEX initialized for tenant: {user_context.tenant_id}")
        print(f"   User ID: {user_context.user_id}")
        
        print("\n   ✅ Runtime usage test passed!")
        return True
        
    except Exception as e:
        print(f"\n   ❌ Runtime usage test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all PostgreSQL integration tests"""
    print("\n" + "="*60)
    print("DocEX 3.0 Multi-Tenancy - PostgreSQL Integration Test")
    print("="*60)
    
    print("\n📋 Prerequisites Check:")
    print("   1. Checking PostgreSQL connection...")
    if not check_postgres_connection():
        print("\n❌ PostgreSQL is not accessible.")
        print("\n💡 To start PostgreSQL:")
        print("   docker-compose -f docker-compose.test.yml up -d")
        print("\n💡 To stop PostgreSQL:")
        print("   docker-compose -f docker-compose.test.yml down")
        return 1
    
    print("   ✅ PostgreSQL is accessible")
    
    results = []
    test_dir = None
    
    try:
        # Test 1: Bootstrap Tenant Initialization
        result, test_dir = test_bootstrap_tenant_initialization_postgres()
        results.append(("Bootstrap Tenant Initialization", result))
        
        if not result:
            print("\n⚠️  Skipping remaining tests due to bootstrap failure")
        else:
            # Test 2: Tenant Provisioning
            result = test_tenant_provisioning_postgres(test_dir)
            results.append(("Tenant Provisioning", result))
            
            # Test 3: Tenant Registry Queries
            result = test_tenant_registry_queries_postgres(test_dir)
            results.append(("Tenant Registry Queries", result))
            
            # Test 4: Runtime Usage
            result = test_runtime_usage_postgres(test_dir)
            results.append(("Runtime Usage", result))
        
    finally:
        # Cleanup
        if test_dir and Path(test_dir).exists():
            print(f"\nCleaning up test directory: {test_dir}")
            shutil.rmtree(test_dir, ignore_errors=True)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All PostgreSQL integration tests passed!")
        print("\n💡 To clean up PostgreSQL container:")
        print("   docker-compose -f docker-compose.test.yml down")
        print("   docker-compose -f docker-compose.test.yml down -v  # Remove volumes")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())

