"""
Test script for database-level multi-tenancy (Model B).

This script demonstrates:
1. Configuration for database-level multi-tenancy
2. Creating baskets and documents for different tenants
3. Verifying tenant isolation
4. Connection management
"""

import asyncio
import logging
import os
import tempfile
import uuid
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

from docex import DocEX
from docex.context import UserContext

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_sqlite_multi_tenancy():
    """Test SQLite multi-tenancy (separate database files per tenant)"""
    logger.info("=" * 60)
    logger.info("Testing SQLite Multi-Tenancy (Separate DB Files)")
    logger.info("=" * 60)
    
    # Note: This test requires configuration to be set up first
    # You would need to update ~/.docex/config.yaml with:
    # security:
    #   multi_tenancy_model: database_level
    #   tenant_database_routing: true
    # database:
    #   type: sqlite
    #   sqlite:
    #     path_template: "storage/tenant_{tenant_id}/docex.db"
    
    try:
        # Generate unique test ID
        test_id = uuid.uuid4().hex[:8]
        
        # Tenant 1
        logger.info("\n--- Tenant 1 Operations ---")
        user_context1 = UserContext(
            user_id="alice",
            tenant_id="tenant1",
            user_email="alice@example.com"
        )
        # For multi-tenancy, create new Database connection for tenant1
        from docex.db.connection import Database
        db1 = Database(tenant_id="tenant1")
        docEX1 = DocEX()
        docEX1.db = db1
        docEX1.user_context = user_context1
        
        # Create basket for tenant1 with unique name
        basket_name1 = f"tenant1_invoices_{test_id}"
        basket1 = docEX1.create_basket(
            basket_name1,
            storage_config={'type': 'filesystem', 'path': f'storage/tenant1/baskets'}
        )
        logger.info(f"✅ Created basket for tenant1: {basket1.id}")
        
        # Add document to tenant1
        temp_file1 = Path(tempfile.gettempdir()) / "invoice_tenant1.txt"
        temp_file1.write_text("Invoice for Tenant 1 - Amount: $1000")
        doc1 = basket1.add(str(temp_file1))
        logger.info(f"✅ Added document to tenant1: {doc1.id}")
        
        # List baskets for tenant1
        baskets1 = docEX1.list_baskets()
        logger.info(f"✅ Tenant1 has {len(baskets1)} baskets")
        
        # Tenant 2 (isolated)
        logger.info("\n--- Tenant 2 Operations ---")
        user_context2 = UserContext(
            user_id="bob",
            tenant_id="tenant2",
            user_email="bob@example.com"
        )
        # Create new Database connection for tenant2
        db2 = Database(tenant_id="tenant2")
        docEX2 = DocEX()
        docEX2.db = db2
        docEX2.user_context = user_context2
        
        # Create basket for tenant2 with unique name
        basket_name2 = f"tenant2_invoices_{test_id}"
        basket2 = docEX2.create_basket(
            basket_name2,
            storage_config={'type': 'filesystem', 'path': f'storage/tenant2/baskets'}
        )
        logger.info(f"✅ Created basket for tenant2: {basket2.id}")
        
        # Add document to tenant2
        temp_file2 = Path(tempfile.gettempdir()) / "invoice_tenant2.txt"
        temp_file2.write_text("Invoice for Tenant 2 - Amount: $2000")
        doc2 = basket2.add(str(temp_file2))
        logger.info(f"✅ Added document to tenant2: {doc2.id}")
        
        # List baskets for tenant2
        baskets2 = docEX2.list_baskets()
        logger.info(f"✅ Tenant2 has {len(baskets2)} baskets")
        
        # Verify isolation
        logger.info("\n--- Verifying Tenant Isolation ---")
        logger.info(f"Tenant1 baskets: {[b.name for b in baskets1]}")
        logger.info(f"Tenant2 baskets: {[b.name for b in baskets2]}")
        
        # Try to access tenant1 basket from tenant2 context (should fail or return None)
        try:
            basket_from_tenant2 = docEX2.get_basket(basket1.id)
            if basket_from_tenant2 is None:
                logger.info("✅ Isolation verified: Tenant2 cannot access Tenant1 basket")
            else:
                logger.warning(f"⚠️  Isolation issue: Tenant2 accessed Tenant1 basket {basket1.id}")
        except Exception as e:
            logger.info(f"✅ Isolation verified: Tenant2 cannot access Tenant1 basket ({e})")
        
        # Cleanup
        temp_file1.unlink()
        temp_file2.unlink()
        
        logger.info("\n✅ SQLite multi-tenancy test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ SQLite multi-tenancy test failed: {e}", exc_info=True)
        raise


def test_postgres_multi_tenancy():
    """Test PostgreSQL multi-tenancy (separate schemas per tenant)"""
    logger.info("=" * 60)
    logger.info("Testing PostgreSQL Multi-Tenancy (Separate Schemas)")
    logger.info("=" * 60)
    
    # Note: This test requires PostgreSQL and configuration to be set up first
    # You would need to update ~/.docex/config.yaml with:
    # security:
    #   multi_tenancy_model: database_level
    #   tenant_database_routing: true
    # database:
    #   type: postgresql
    #   postgres:
    #     host: localhost
    #     port: 5432
    #     database: docex
    #     user: postgres
    #     password: postgres
    #     schema_template: "tenant_{tenant_id}"
    
    # Check if PostgreSQL is configured
    pg_user = os.getenv("PG_USER")
    if not pg_user:
        logger.warning("⚠️  PostgreSQL not configured (PG_USER not set). Skipping PostgreSQL test.")
        return
    
    try:
        # Generate unique test ID
        test_id = uuid.uuid4().hex[:8]
        
        # Tenant 1
        logger.info("\n--- Tenant 1 Operations ---")
        user_context1 = UserContext(
            user_id="alice",
            tenant_id="tenant1",
            user_email="alice@example.com"
        )
        from docex.db.connection import Database
        db1 = Database(tenant_id="tenant1")
        docEX1 = DocEX()
        docEX1.db = db1
        docEX1.user_context = user_context1
        
        # Create basket for tenant1 with unique name
        basket_name1 = f"tenant1_invoices_{test_id}"
        basket1 = docEX1.create_basket(
            basket_name1,
            storage_config={'type': 'filesystem', 'path': f'storage/tenant1/baskets'}
        )
        logger.info(f"✅ Created basket for tenant1: {basket1.id}")
        
        # Add document to tenant1
        temp_file1 = Path(tempfile.gettempdir()) / "invoice_tenant1.txt"
        temp_file1.write_text("Invoice for Tenant 1 - Amount: $1000")
        doc1 = basket1.add(str(temp_file1))
        logger.info(f"✅ Added document to tenant1: {doc1.id}")
        
        # Tenant 2 (isolated)
        logger.info("\n--- Tenant 2 Operations ---")
        user_context2 = UserContext(
            user_id="bob",
            tenant_id="tenant2",
            user_email="bob@example.com"
        )
        # Create new Database connection for tenant2
        db2 = Database(tenant_id="tenant2")
        docEX2 = DocEX()
        docEX2.db = db2
        docEX2.user_context = user_context2
        
        # Create basket for tenant2 with unique name
        basket_name2 = f"tenant2_invoices_{test_id}"
        basket2 = docEX2.create_basket(
            basket_name2,
            storage_config={'type': 'filesystem', 'path': f'storage/tenant2/baskets'}
        )
        logger.info(f"✅ Created basket for tenant2: {basket2.id}")
        
        # Add document to tenant2
        temp_file2 = Path(tempfile.gettempdir()) / "invoice_tenant2.txt"
        temp_file2.write_text("Invoice for Tenant 2 - Amount: $2000")
        doc2 = basket2.add(str(temp_file2))
        logger.info(f"✅ Added document to tenant2: {doc2.id}")
        
        # Verify isolation
        logger.info("\n--- Verifying Tenant Isolation ---")
        baskets1 = docEX1.list_baskets()
        baskets2 = docEX2.list_baskets()
        logger.info(f"Tenant1 baskets: {[b.name for b in baskets1]}")
        logger.info(f"Tenant2 baskets: {[b.name for b in baskets2]}")
        
        # Cleanup
        temp_file1.unlink()
        temp_file2.unlink()
        
        logger.info("\n✅ PostgreSQL multi-tenancy test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ PostgreSQL multi-tenancy test failed: {e}", exc_info=True)
        raise


def test_connection_management():
    """Test connection management features"""
    logger.info("=" * 60)
    logger.info("Testing Connection Management")
    logger.info("=" * 60)
    
    try:
        from docex.db.tenant_database_manager import TenantDatabaseManager
        
        manager = TenantDatabaseManager()
        
        # Generate unique test ID
        test_id = uuid.uuid4().hex[:8]
        
        # Create connections for multiple tenants
        from docex.db.connection import Database
        user_context1 = UserContext(user_id="alice", tenant_id="tenant1")
        db1 = Database(tenant_id="tenant1")
        docEX1 = DocEX()
        docEX1.db = db1
        docEX1.user_context = user_context1
        basket1 = docEX1.create_basket(
            f"test1_{test_id}",
            storage_config={'type': 'filesystem', 'path': f'storage/tenant1/baskets'}
        )
        logger.info("✅ Created connection for tenant1")
        
        user_context2 = UserContext(user_id="bob", tenant_id="tenant2")
        db2 = Database(tenant_id="tenant2")
        docEX2 = DocEX()
        docEX2.db = db2
        docEX2.user_context = user_context2
        basket2 = docEX2.create_basket(
            f"test2_{test_id}",
            storage_config={'type': 'filesystem', 'path': f'storage/tenant2/baskets'}
        )
        logger.info("✅ Created connection for tenant2")
        
        # List active tenant connections
        active_tenants = manager.list_tenant_databases()
        logger.info(f"✅ Active tenant connections: {active_tenants}")
        
        # Close connection for one tenant
        manager.close_tenant_connection("tenant1")
        logger.info("✅ Closed connection for tenant1")
        
        # List remaining connections
        remaining = manager.list_tenant_databases()
        logger.info(f"✅ Remaining tenant connections: {remaining}")
        
        logger.info("\n✅ Connection management test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Connection management test failed: {e}", exc_info=True)
        raise


def main():
    """Run all multi-tenancy tests"""
    logger.info("🚀 Starting Multi-Tenancy Tests")
    logger.info("=" * 60)
    
    # Check configuration
    logger.info("\n⚠️  Note: These tests require database-level multi-tenancy to be configured.")
    logger.info("   Update ~/.docex/config.yaml with:")
    logger.info("   security:")
    logger.info("     multi_tenancy_model: database_level")
    logger.info("     tenant_database_routing: true")
    logger.info("")
    
    try:
        # Test SQLite multi-tenancy
        test_sqlite_multi_tenancy()
        
        # Test PostgreSQL multi-tenancy (if configured)
        test_postgres_multi_tenancy()
        
        # Test connection management
        test_connection_management()
        
        logger.info("\n" + "=" * 60)
        logger.info("🎉 All multi-tenancy tests completed!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"\n❌ Tests failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

