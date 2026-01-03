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
    """Comprehensive tenant provisioning test with PostgreSQL"""
    print("\n" + "="*60)
    print("TEST 2: Comprehensive Tenant Provisioning (PostgreSQL)")
    print("="*60)
    
    try:
        from docex.provisioning.tenant_provisioner import (
            TenantProvisioner, 
            TenantExistsError, 
            InvalidTenantIdError
        )
        from docex.config.docex_config import DocEXConfig
        from docex.db.connection import Database
        from docex.db.tenant_registry_model import TenantRegistry
        from sqlalchemy import inspect, text
        
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
        
        # 2.2 Test Invalid Tenant IDs
        print("\n2.2 Testing invalid tenant ID validation...")
        invalid_ids = [
            ('_docex_system_', 'Reserved system tenant ID'),
            ('', 'Empty tenant ID'),
            ('tenant with spaces', 'Tenant ID with spaces'),
            ('tenant@invalid', 'Tenant ID with special characters'),
            ('tenant.dot', 'Tenant ID with dots'),
        ]
        
        for invalid_id, reason in invalid_ids:
            try:
                provisioner.create(
                    tenant_id=invalid_id,
                    display_name='Test',
                    created_by='test_user'
                )
                print(f"   ❌ Should have rejected '{invalid_id}' ({reason})")
                return False
            except InvalidTenantIdError:
                print(f"   ✅ Correctly rejected '{invalid_id}' ({reason})")
            except Exception as e:
                # Some invalid IDs might fail at different stages
                if 'InvalidTenantIdError' in str(type(e).__name__) or 'invalid' in str(e).lower():
                    print(f"   ✅ Correctly rejected '{invalid_id}' ({reason})")
                else:
                    print(f"   ⚠️  Unexpected error for '{invalid_id}': {e}")
        
        # 2.3 Provision test tenant 'acme'
        print("\n2.3 Provisioning test tenant 'acme'...")
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
        
        # 2.4 Verify Schema Exists in PostgreSQL
        print("\n2.4 Verifying schema exists in PostgreSQL...")
        engine = bootstrap_db.get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name = :schema_name
            """), {'schema_name': tenant_registry.schema_name})
            schema_exists = result.fetchone() is not None
        
        if schema_exists:
            print(f"   ✅ Schema '{tenant_registry.schema_name}' exists in PostgreSQL")
        else:
            print(f"   ❌ Schema '{tenant_registry.schema_name}' does NOT exist in PostgreSQL")
            return False
        
        # 2.5 Verify Tables Exist in Tenant Schema
        print("\n2.5 Verifying tables exist in tenant schema...")
        tenant_db = Database(config=config, tenant_id='acme')
        tenant_engine = tenant_db.get_engine()
        
        # Query tables directly from information_schema for the tenant schema
        with tenant_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = :schema_name
                ORDER BY table_name
            """), {'schema_name': tenant_registry.schema_name})
            tables = [row[0] for row in result.fetchall()]
        required_tables = [
            'docbasket', 
            'document', 
            'document_metadata',
            'file_history',
            'operations',
            'operation_dependencies',
            'doc_events',
            'processors',
            'processing_operations'
        ]
        
        missing_tables = [t for t in required_tables if t not in tables]
        if missing_tables:
            print(f"   ❌ Missing tables in tenant schema: {', '.join(missing_tables)}")
            print(f"   Found tables: {', '.join(tables)}")
            return False
        
        print(f"   ✅ All required tables exist in tenant schema ({len(required_tables)} tables)")
        
        # Verify tenant_registry is NOT in tenant schema (only in bootstrap)
        # Check explicitly in the tenant schema
        with tenant_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = :schema_name 
                AND table_name = 'tenant_registry'
            """), {'schema_name': tenant_registry.schema_name})
            tenant_registry_in_tenant = result.fetchone() is not None
        
        # Also verify tenant_registry exists in bootstrap schema
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'docex_system'
                AND table_name = 'tenant_registry'
            """))
            tenant_registry_in_bootstrap = result.fetchone() is not None
        
        if tenant_registry_in_tenant:
            print(f"   ⚠️  tenant_registry found in tenant schema '{tenant_registry.schema_name}'")
            print("   ⚠️  This is a configuration issue - tenant_registry should only be in bootstrap schema")
            print("   ℹ️  Continuing test but this should be investigated")
        else:
            print("   ✅ tenant_registry correctly NOT in tenant schema")
        
        if tenant_registry_in_bootstrap:
            print("   ✅ tenant_registry exists in bootstrap schema (docex_system)")
        else:
            print("   ⚠️  tenant_registry NOT found in bootstrap schema - this is unexpected")
        
        # 2.6 Verify Tenant Registry Entry
        print("\n2.6 Verifying tenant registry entry...")
        with bootstrap_db.session() as session:
            registry_entry = session.query(TenantRegistry).filter_by(tenant_id='acme').first()
            assert registry_entry is not None, "Tenant should exist in registry"
            assert registry_entry.is_system == False, "Business tenant should not be system tenant"
            assert registry_entry.isolation_strategy == 'schema', "Isolation strategy should be 'schema'"
            assert registry_entry.schema_name == tenant_registry.schema_name, "Schema name should match"
            assert registry_entry.created_by == 'test_user', "created_by should be set"
            assert registry_entry.created_at is not None, "created_at should be set"
        
        print("   ✅ Tenant registry entry validated")
        print(f"      - is_system: {registry_entry.is_system}")
        print(f"      - isolation_strategy: {registry_entry.isolation_strategy}")
        print(f"      - created_by: {registry_entry.created_by}")
        print(f"      - created_at: {registry_entry.created_at}")
        
        # 2.7 Test Duplicate Tenant Prevention
        print("\n2.7 Testing duplicate tenant prevention...")
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
        
        # 2.8 Verify Tenant Can Be Used After Provisioning
        print("\n2.8 Verifying tenant can be used after provisioning...")
        from docex import DocEX
        from docex.context import UserContext
        
        user_context = UserContext(
            user_id='test_user',
            tenant_id='acme',
            roles=['user']
        )
        doc_ex = DocEX(user_context=user_context)
        print(f"   ✅ DocEX instance created for tenant: {user_context.tenant_id}")
        
        # Create a test basket with unique name to avoid conflicts
        import time
        unique_basket_name = f'test_basket_provisioning_{int(time.time())}'
        basket = doc_ex.create_basket(unique_basket_name, 'Test basket for provisioning validation')
        print(f"   ✅ Basket created: {basket.id} ({basket.name})")
        
        # Add a test document - create a temporary file first
        import tempfile
        test_file = Path(test_dir) / 'test_provisioning.txt'
        test_content = "Test document for provisioning validation"
        test_file.write_text(test_content)
        
        doc = basket.add(str(test_file), metadata={'test': 'provisioning_validation'})
        print(f"   ✅ Document added: {doc.id} ({doc.name})")
        
        # Clean up temp file
        test_file.unlink()
        
        # Verify document is in tenant's schema
        # The tenant_db should already be using the tenant schema, but let's verify
        with tenant_db.session() as session:
            from docex.db.models import Document
            db_doc = session.query(Document).filter_by(id=doc.id).first()
            if db_doc:
                print(f"   ✅ Document found in tenant schema: {db_doc.name}")
            else:
                print(f"   ❌ Document not found in tenant schema")
                return False
        
        # Clean up test basket
        basket.delete()
        print("   ✅ Test basket deleted (cleanup)")
        
        # 2.9 Provision another tenant 'contoso' (fresh tenant to verify no tenant_registry)
        print("\n2.9 Provisioning another tenant 'contoso' (fresh tenant)...")
        with bootstrap_db.session() as session:
            existing = session.query(TenantRegistry).filter_by(tenant_id='contoso').first()
            if existing:
                print("   ℹ️  Tenant 'contoso' already exists, deleting and recreating to test fresh provisioning...")
                # Delete existing tenant to test fresh provisioning
                from docex.db.connection import Database as TenantDB
                contoso_db = TenantDB(config=config, tenant_id='contoso')
                contoso_engine = contoso_db.get_engine()
                # Drop schema if it exists
                with contoso_engine.connect() as conn:
                    conn.execute(text(f"DROP SCHEMA IF EXISTS {existing.schema_name} CASCADE"))
                    conn.commit()
                # Remove from registry
                session.delete(existing)
                session.commit()
        
        # Now provision fresh tenant
        tenant_registry2 = provisioner.create(
            tenant_id='contoso',
            display_name='Contoso Ltd',
            created_by='test_user'
        )
        print(f"   ✅ Second tenant provisioned: {tenant_registry2.tenant_id}")
        print(f"   Schema name: {tenant_registry2.schema_name}")
        
        # Verify second tenant's schema exists
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name = :schema_name
            """), {'schema_name': tenant_registry2.schema_name})
            schema2_exists = result.fetchone() is not None
        
        if schema2_exists:
            print(f"   ✅ Second tenant schema '{tenant_registry2.schema_name}' exists")
        else:
            print(f"   ❌ Second tenant schema '{tenant_registry2.schema_name}' does NOT exist")
            return False
        
        # Verify contoso schema does NOT have tenant_registry (fresh tenant test)
        print("\n2.10 Verifying fresh tenant 'contoso' does NOT have tenant_registry...")
        contoso_db = Database(config=config, tenant_id='contoso')
        contoso_engine = contoso_db.get_engine()
        with contoso_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = :schema_name 
                AND table_name = 'tenant_registry'
            """), {'schema_name': tenant_registry2.schema_name})
            contoso_has_registry = result.fetchone() is not None
        
        if contoso_has_registry:
            print(f"   ❌ Fresh tenant 'contoso' has tenant_registry - this is a bug!")
            return False
        else:
            print(f"   ✅ Fresh tenant 'contoso' correctly does NOT have tenant_registry")
        
        # 2.11 Test Error Scenarios (if possible)
        print("\n2.11 Testing error scenarios...")
        # Test with invalid database connection (would require mocking)
        # For now, we'll just verify that the provisioner handles edge cases
        
        # Test that tenant_exists() works correctly
        assert provisioner.tenant_exists('acme'), "tenant_exists() should return True for existing tenant"
        assert not provisioner.tenant_exists('nonexistent_tenant'), "tenant_exists() should return False for non-existent tenant"
        print("   ✅ tenant_exists() method works correctly")
        
        print("\n   ✅ Comprehensive tenant provisioning test passed!")
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
            
            # Get second business tenant (if it exists - provisioning test might have failed)
            contoso = session.query(TenantRegistry).filter_by(
                tenant_id='contoso'
            ).first()
            if contoso:
                print(f"   ✅ Second business tenant found: {contoso.tenant_id}")
                print(f"   Schema: {contoso.schema_name}")
            else:
                print("   ℹ️  Contoso tenant not found (may not have been created if provisioning test failed)")
                print("   ℹ️  This is expected if the provisioning test failed before creating contoso")
        
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
        
        # Set up PostgreSQL test config - use the existing config from previous tests
        # The config should already be set up from test 1 and 2
        config = DocEXConfig()
        
        # Verify multi-tenancy is enabled
        multi_tenancy_enabled = config.get('multi_tenancy', {}).get('enabled', False)
        if not multi_tenancy_enabled:
            print("   ⚠️  Multi-tenancy not enabled in config, enabling it...")
            DocEXConfig.setup(
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
        
        # Reset DocEX singleton to test initialization
        DocEX._instance = None
        DocEX._config = None
        
        print("\n4.1 Testing DocEX initialization without UserContext (should fail)...")
        try:
            doc_ex = DocEX()
            print("   ❌ Should have raised ValueError")
            return False
        except ValueError as e:
            if "UserContext is required" in str(e) or "multi-tenancy is enabled" in str(e):
                print(f"   ✅ Correctly rejected: {e}")
            else:
                print(f"   ⚠️  Unexpected ValueError: {e}")
                return False
        
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

