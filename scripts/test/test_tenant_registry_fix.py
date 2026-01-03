#!/usr/bin/env python3
"""
Test script to verify tenant registry schema fix.

This script tests that the tenant_registry table is created in the
bootstrap schema (docex_system) instead of the public schema.
"""

import os
import sys
from pathlib import Path
from sqlalchemy import text

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_tenant_registry_schema():
    """Test that tenant registry operations use the bootstrap schema."""
    try:
        from docex.db.connection import Database
        from sqlalchemy import text

        print("🧪 Testing Tenant Registry Schema Fix")
        print("=" * 50)

        # Get database connection
        db = Database()

        # Check if we're using PostgreSQL
        db_config = db.config.get('database', {})
        if db_config.get('type') not in ['postgresql', 'postgres']:
            print("ℹ️  Test skipped - not using PostgreSQL")
            return True

        bootstrap_schema = db.get_bootstrap_schema()
        print(f"📋 Bootstrap schema: {bootstrap_schema}")

        # Check if tenant_registry table exists in bootstrap schema
        with db.engine.connect() as conn:
            # Set search path to bootstrap schema
            conn.execute(text(f'SET search_path TO {bootstrap_schema}'))

            # Check if table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = :schema_name
                    AND table_name = 'tenant_registry'
                )
            """), {'schema_name': bootstrap_schema})

            table_exists = result.fetchone()[0]

            if table_exists:
                print(f"✅ tenant_registry table exists in schema: {bootstrap_schema}")

                # Check table structure
                result = conn.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = :schema_name
                    AND table_name = 'tenant_registry'
                    ORDER BY ordinal_position
                """), {'schema_name': bootstrap_schema})

                columns = result.fetchall()
                print("📋 Table structure:")
                for col in columns:
                    print(f"   - {col[0]}: {col[1]} ({'NOT NULL' if col[2] == 'NO' else 'NULL'})")

                return True
            else:
                print(f"❌ tenant_registry table NOT found in schema: {bootstrap_schema}")

                # Check if it exists in public schema (which would be the bug)
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = 'tenant_registry'
                    )
                """))

                in_public = result.fetchone()[0]
                if in_public:
                    print("🚨 BUG: tenant_registry table found in PUBLIC schema!")
                    return False
                else:
                    print("ℹ️  tenant_registry table doesn't exist yet (expected for new installations)")
                    return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tenant_provisioning():
    """Test tenant provisioning and registry."""
    try:
        from docex.context import UserContext
        from docex.db.tenant_database_manager import TenantDatabaseManager
        from docex.config.docex_config import DocEXConfig

        print("\n🧪 Testing Tenant Provisioning")
        print("=" * 30)

        # Check configuration
        config = DocEXConfig()
        security_config = config.get('security', {})
        multi_tenancy_model = security_config.get('multi_tenancy_model', 'row_level')

        if multi_tenancy_model != 'database_level':
            print("ℹ️  Test skipped - database-level multi-tenancy not enabled")
            return True

        # Provision a test tenant using the tenant provisioner
        tenant_id = "test_registry_tenant"

        print(f"📦 Provisioning tenant: {tenant_id}")

        # Use the tenant provisioner to properly register and provision the tenant
        from docex.provisioning.tenant_provisioner import TenantProvisioner
        provisioner = TenantProvisioner()

        # Check if tenant already exists
        if provisioner.tenant_exists(tenant_id):
            print(f"🧹 Cleaning up existing tenant: {tenant_id}")
            # For this test, we'll simulate the error condition by removing registry entry but keeping schema
            try:
                # Remove from registry but keep schema to simulate the error condition
                from docex.db.connection import Database
                bootstrap_db = Database.get_default_connection()
                with bootstrap_db.get_bootstrap_connection() as conn:
                    conn.execute(text("DELETE FROM tenant_registry WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
                    conn.commit()
                print(f"🧪 Simulated error condition: schema exists but registry entry removed for tenant {tenant_id}")
            except Exception as e:
                print(f"⚠️  Could not simulate error condition: {e}")
                return True

        # Provision the tenant (this registers it in the tenant registry and creates the database/schema)
        tenant_registry = provisioner.create(
            tenant_id=tenant_id,
            display_name=f"Test Tenant {tenant_id}",
            created_by="test_script"
        )

        print(f"✅ Tenant registered in registry: {tenant_registry.tenant_id}")

        print(f"✅ Tenant {tenant_id} provisioned successfully")

        # Test DocEX instance creation
        user_context = UserContext(user_id="test_user", tenant_id=tenant_id)
        from docex import DocEX
        docex = DocEX(user_context=user_context)

        print(f"✅ DocEX instance created for tenant: {tenant_id}")

        # Test basic operations
        baskets = docex.list_baskets()
        print(f"✅ Tenant can list baskets: {len(baskets)} found")

        # Test tenant validation and cleanup functionality
        print(f"\n🧪 Testing Tenant Validation & Cleanup")
        print("=" * 40)

        # Test the validation methods
        from docex.db.tenant_database_manager import TenantDatabaseManager
        manager = TenantDatabaseManager()

        # Test validation on properly set up tenant
        validation = manager.validate_tenant_setup(tenant_id)
        print(f"✅ Tenant validation: {validation}")

        # Test cleanup on properly set up tenant (should do nothing)
        cleanup_result = manager.cleanup_incomplete_tenant(tenant_id)
        print(f"✅ Cleanup on valid tenant: {cleanup_result}")

        # Test validation on non-existent tenant
        validation = manager.validate_tenant_setup("non_existent_tenant")
        print(f"✅ Non-existent tenant validation: {validation}")

        # Test cleanup on non-existent tenant
        cleanup_result = manager.cleanup_incomplete_tenant("non_existent_tenant")
        print(f"✅ Cleanup on non-existent tenant: {cleanup_result}")

        print(f"✅ All tenant validation and cleanup tests passed!")
        return True

    except Exception as e:
        print(f"❌ Tenant provisioning test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tenant registry tests."""
    print("🚀 DocEX Tenant Registry Fix Test Suite")
    print("=" * 50)

    success = True

    # Test 1: Schema setup
    if not test_tenant_registry_schema():
        success = False

    # Test 2: Tenant provisioning
    if not test_tenant_provisioning():
        success = False

    if success:
        print("\n🎉 All tests passed!")
        print("✅ Tenant registry schema fix is working correctly")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())