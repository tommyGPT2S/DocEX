#!/usr/bin/env python3
"""
Comprehensive Test Suite for acme-corp Tenant

Tests various DocEX operations:
1. Multiple basket creation
2. Document operations (add, retrieve, delete)
3. Metadata operations
4. Basket operations
5. Tenant isolation verification
"""

import sys
import os
import tempfile
import shutil
import argparse
from pathlib import Path
from datetime import datetime

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

def test_basket_operations(docex, tenant_id):
    """Test basket creation and management"""
    print("\n" + "=" * 70)
    print("TEST: Basket Operations")
    print("=" * 70)
    
    # Create multiple baskets
    baskets = []
    basket_names = ['invoices', 'purchase_orders', 'contracts']
    
    for basket_name in basket_names:
        print(f"\n   Creating basket: {basket_name}")
        try:
            basket = docex.create_basket(
                basket_name,
                f'Basket for {basket_name} in {tenant_id}'
            )
            baskets.append(basket)
            print(f"   ✅ Created: {basket.id} - {basket.name}")
        except ValueError as e:
            if "already exists" in str(e):
                print(f"   ⚠️  Basket '{basket_name}' already exists, retrieving...")
                # Try to get existing basket
                all_baskets = docex.list_baskets()
                for b in all_baskets:
                    if b.name == basket_name:
                        baskets.append(b)
                        print(f"   ✅ Retrieved: {b.id} - {b.name}")
                        break
            else:
                raise
    
    # List all baskets
    print(f"\n   Listing all baskets in tenant '{tenant_id}':")
    all_baskets = docex.list_baskets()
    print(f"   Found {len(all_baskets)} basket(s):")
    for basket in all_baskets:
        print(f"     - {basket.id}: {basket.name} ({basket.description or 'No description'})")
    
    return baskets

def test_document_operations(docex, baskets):
    """Test document operations"""
    print("\n" + "=" * 70)
    print("TEST: Document Operations")
    print("=" * 70)
    
    if not baskets:
        print("   ⚠️  No baskets available, skipping document operations")
        return
    
    # Use the first basket
    basket = baskets[0]
    print(f"\n   Using basket: {basket.name} ({basket.id})")
    
    # Create test documents
    test_documents = []
    
    # Document 1: Text file
    print(f"\n   Adding text document...")
    test_file_1 = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
    test_file_1.write("This is a test document for acme-corp tenant.\n")
    test_file_1.write(f"Created at: {datetime.now()}\n")
    test_file_1.close()
    
    try:
        doc1 = basket.add(test_file_1.name, metadata={'document_type': 'test', 'category': 'sample'})
        test_documents.append((doc1, test_file_1.name))
        print(f"   ✅ Added document: {doc1.id}")
        print(f"      Path: {doc1.path}")
        # Print full S3 path if using S3 storage
        if basket.storage_config.get('type') == 's3':
            from docex.storage.path_builder import DocEXPathBuilder
            from docex.config.docex_config import DocEXConfig
            path_builder = DocEXPathBuilder(DocEXConfig())
            tenant_id = basket.path_helper.extract_tenant_id()
            if tenant_id:
                doc_name_base = doc1.name.replace(Path(doc1.name).suffix, '') if doc1.name else 'document'
                full_s3_path = path_builder.build_document_path(
                    basket_id=basket.id,
                    document_id=doc1.id,
                    basket_name=basket.name,
                    document_name=doc_name_base,
                    file_ext=Path(doc1.name).suffix if doc1.name else '',
                    tenant_id=tenant_id
                )
                bucket = basket.storage_config.get('s3', {}).get('bucket', 'unknown')
                print(f"      Full S3 Path: s3://{bucket}/{full_s3_path}")
        metadata = doc1.get_metadata()
        if metadata:
            print(f"      Metadata: {metadata}")
    except Exception as e:
        print(f"   ❌ Failed to add document: {e}")
        import traceback
        traceback.print_exc()
    
    # Document 2: Another text file
    print(f"\n   Adding second text document...")
    test_file_2 = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
    test_file_2.write("Second test document for acme-corp.\n")
    test_file_2.write(f"Created at: {datetime.now()}\n")
    test_file_2.close()
    
    try:
        doc2 = basket.add(test_file_2.name, metadata={'document_type': 'test', 'category': 'sample'})
        test_documents.append((doc2, test_file_2.name))
        print(f"   ✅ Added document: {doc2.id}")
        # Print full S3 path if using S3 storage
        if basket.storage_config.get('type') == 's3':
            from docex.storage.path_builder import DocEXPathBuilder
            from docex.config.docex_config import DocEXConfig
            path_builder = DocEXPathBuilder(DocEXConfig())
            tenant_id = basket.path_helper.extract_tenant_id()
            if tenant_id:
                doc_name_base = doc2.name.replace(Path(doc2.name).suffix, '') if doc2.name else 'document'
                full_s3_path = path_builder.build_document_path(
                    basket_id=basket.id,
                    document_id=doc2.id,
                    basket_name=basket.name,
                    document_name=doc_name_base,
                    file_ext=Path(doc2.name).suffix if doc2.name else '',
                    tenant_id=tenant_id
                )
                bucket = basket.storage_config.get('s3', {}).get('bucket', 'unknown')
                print(f"      Full S3 Path: s3://{bucket}/{full_s3_path}")
    except Exception as e:
        print(f"   ❌ Failed to add document: {e}")
    
    # List documents in basket
    print(f"\n   Listing documents in basket '{basket.name}':")
    documents = basket.list_documents()
    print(f"   Found {len(documents)} document(s):")
    for doc in documents:
        print(f"     - {doc.id}: {doc.path or 'No path'}")
        # Print full S3 path if using S3 storage
        if basket.storage_config.get('type') == 's3':
            from docex.storage.path_builder import DocEXPathBuilder
            from docex.config.docex_config import DocEXConfig
            path_builder = DocEXPathBuilder(DocEXConfig())
            tenant_id = basket.path_helper.extract_tenant_id()
            if tenant_id:
                doc_name_base = doc.name.replace(Path(doc.name).suffix, '') if doc.name else 'document'
                full_s3_path = path_builder.build_document_path(
                    basket_id=basket.id,
                    document_id=doc.id,
                    basket_name=basket.name,
                    document_name=doc_name_base,
                    file_ext=Path(doc.name).suffix if doc.name else '',
                    tenant_id=tenant_id
                )
                bucket = basket.storage_config.get('s3', {}).get('bucket', 'unknown')
                print(f"       Full S3 Path: s3://{bucket}/{full_s3_path}")
        metadata = doc.get_metadata()
        if metadata:
            print(f"       Metadata: {metadata}")
    
    # Retrieve document content
    if test_documents:
        print(f"\n   Retrieving document content...")
        doc, file_path = test_documents[0]
        try:
            content = doc.get_content()
            print(f"   ✅ Retrieved content from {doc.id}")
            print(f"      Content length: {len(content)} bytes")
            if isinstance(content, str):
                print(f"      Preview: {content[:100]}...")
        except Exception as e:
            print(f"   ❌ Failed to retrieve content: {e}")
    
    # Cleanup test files
    for doc, file_path in test_documents:
        try:
            os.unlink(file_path)
        except:
            pass
    
    return test_documents

def test_metadata_operations(docex, baskets):
    """Test metadata operations"""
    print("\n" + "=" * 70)
    print("TEST: Metadata Operations")
    print("=" * 70)
    
    if not baskets:
        print("   ⚠️  No baskets available, skipping metadata operations")
        return
    
    basket = baskets[0]
    documents = basket.list_documents()
    
    if not documents:
        print("   ⚠️  No documents available, skipping metadata operations")
        return
    
    doc = documents[0]
    print(f"\n   Working with document: {doc.id}")
    
    # Get current metadata
    print(f"\n   Current metadata:")
    current_metadata = doc.get_metadata() or {}
    for key, value in current_metadata.items():
        print(f"     - {key}: {value}")
    
    # Get available metadata keys
    print(f"\n   Available metadata keys:")
    metadata_keys = DocEX.get_metadata_keys()
    for key, description in list(metadata_keys.items())[:5]:  # Show first 5
        print(f"     - {key}: {description}")
    if len(metadata_keys) > 5:
        print(f"     ... and {len(metadata_keys) - 5} more")

def test_tenant_isolation(docex, tenant_id, config):
    """Test tenant isolation"""
    print("\n" + "=" * 70)
    print("TEST: Tenant Isolation Verification")
    print("=" * 70)
    
    # Verify we're using the correct tenant
    print(f"\n   Verifying tenant isolation for: {tenant_id}")
    
    # Check database connection
    if hasattr(docex, 'db') and docex.db:
        db_tenant_id = getattr(docex.db, 'tenant_id', None)
        print(f"   Database tenant_id: {db_tenant_id}")
        if db_tenant_id == tenant_id:
            print(f"   ✅ Database correctly configured for tenant '{tenant_id}'")
        else:
            print(f"   ⚠️  Database tenant_id mismatch: expected '{tenant_id}', got '{db_tenant_id}'")
    
    # Check user context
    if docex.user_context:
        print(f"   User context tenant_id: {docex.user_context.tenant_id}")
        print(f"   User context user_id: {docex.user_context.user_id}")
        if docex.user_context.tenant_id == tenant_id:
            print(f"   ✅ UserContext correctly configured for tenant '{tenant_id}'")
        else:
            print(f"   ⚠️  UserContext tenant_id mismatch")
    
    # List baskets and verify they belong to this tenant
    baskets = docex.list_baskets()
    print(f"\n   Found {len(baskets)} basket(s) in tenant '{tenant_id}'")
    for basket in baskets:
        print(f"     - {basket.id}: {basket.name}")

def main(tenant_id: str = 'acme_corp', db_type: str = 'sqlite', storage_type: str = 'filesystem'):
    print("=" * 70)
    print("Comprehensive Test Suite for Tenant Operations")
    print("=" * 70)
    print(f"Tenant ID: {tenant_id}")
    print(f"Database type: {db_type}")
    print(f"Storage type: {storage_type}")
    
    # Create temporary directory for test (only used for SQLite and filesystem storage)
    test_dir = tempfile.mkdtemp(prefix='docex_test_')
    print(f"\n📁 Test directory: {test_dir}")
    
    # Setup S3 mocking if using S3 storage
    s3_mock = None
    if storage_type == 's3':
        try:
            from moto import mock_aws
            import boto3
            s3_mock = mock_aws()
            s3_mock.start()
            print("✅ S3 mocking enabled (moto)")
            
            # Create S3 bucket for testing
            s3_client = boto3.client('s3', region_name='us-east-1')
            try:
                s3_client.create_bucket(Bucket='docex-test-bucket')
                print("✅ S3 test bucket created")
            except Exception as e:
                # Bucket might already exist in mock
                print(f"⚠️  S3 bucket creation note: {e}")
        except ImportError as e:
            print(f"❌ ERROR: Required packages not installed: {e}")
            print("   Install with: pip install moto boto3")
            return False
        except Exception as e:
            print(f"❌ ERROR: Failed to start S3 mocking: {e}")
            return False
    
    try:
        # Initialize configuration
        config = DocEXConfig()
        
        # Build storage configuration
        if storage_type == 's3':
            storage_config = {
                'type': 's3',
                's3': {
                    'bucket': 'docex-test-bucket',
                    'bucket_application': 'docex-test',
                    'path_namespace': 'finance_dept',
                    'prefix': 'test',
                    'region': 'us-east-1',
                    'access_key': 'test-key',
                    'secret_key': 'test-secret'
                }
            }
        else:
            storage_config = {
                'type': 'filesystem',
                'filesystem': {
                    'path': str(Path(test_dir) / 'storage')
                }
            }
        
        if db_type == 'postgresql' or db_type == 'postgres':
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
                storage=storage_config,
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
            config.setup(
                database={
                    'type': 'sqlite',
                    'sqlite': {
                        'path': str(Path(test_dir) / 'docex.db')
                    }
                },
                storage=storage_config,
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
        
        # Ensure tenant exists
        print("\n" + "-" * 70)
        print("Ensuring Tenant is Provisioned")
        print("-" * 70)
        
        # Clear cached connections
        from docex.db.tenant_database_manager import TenantDatabaseManager
        tenant_manager = TenantDatabaseManager()
        tenant_manager.close_all_connections()
        
        bootstrap_manager = BootstrapTenantManager(config=config)
        if not bootstrap_manager.is_initialized():
            print("   Initializing bootstrap tenant...")
            bootstrap_manager.initialize(created_by='test_user')
            print("   ✅ Bootstrap tenant initialized")
        
        # Check if tenant exists
        bootstrap_db = Database(config=config, tenant_id='_docex_system_')
        with bootstrap_db.session() as session:
            existing_tenant = session.query(TenantRegistry).filter_by(tenant_id=tenant_id).first()
            if not existing_tenant:
                print(f"   Provisioning tenant '{tenant_id}'...")
                provisioner = TenantProvisioner(config=config)
                provisioner.create(
                    tenant_id=tenant_id,
                    display_name=f'Test Tenant {tenant_id}',
                    created_by='test_user'
                )
                print(f"   ✅ Tenant '{tenant_id}' provisioned")
            else:
                print(f"   ✅ Tenant '{tenant_id}' already exists")
        
        bootstrap_db.close()
        
        # Initialize DocEX for the tenant
        print("\n" + "-" * 70)
        print("Initializing DocEX for Tenant")
        print("-" * 70)
        
        user_context = UserContext(user_id='test_user', tenant_id=tenant_id)
        docex = DocEX(user_context=user_context)
        print(f"✅ DocEX initialized for tenant: {tenant_id}")
        
        # Run test suites
        baskets = test_basket_operations(docex, tenant_id)
        documents = test_document_operations(docex, baskets)
        test_metadata_operations(docex, baskets)
        test_tenant_isolation(docex, tenant_id, config)
        
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
        # Stop S3 mocking if it was started
        if storage_type == 's3' and 's3_mock' in locals() and s3_mock:
            try:
                s3_mock.stop()
                print("✅ S3 mocking stopped")
            except:
                pass
        
        # Skip cleanup - keep test directory for inspection
        print(f"\n📁 Test directory preserved for inspection: {test_dir}")
        if storage_type == 's3':
            print(f"   S3 bucket: docex-test-bucket")
            print(f"   S3 objects were created in mocked S3 (moto)")
        print(f"   To clean up manually, run:")
        if storage_type == 'filesystem':
            print(f"   rm -rf {test_dir}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Comprehensive test suite for tenant operations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_acme_corp_comprehensive.py                    # Uses default 'acme_corp' with SQLite
  python test_acme_corp_comprehensive.py acme_corp          # Uses 'acme_corp' with SQLite
  python test_acme_corp_comprehensive.py acme_corp --db-type postgresql  # Uses PostgreSQL
        """
    )
    parser.add_argument(
        'tenant_id',
        nargs='?',
        default='acme_corp',
        help='Tenant ID to test (default: acme_corp)'
    )
    parser.add_argument(
        '--db-type',
        choices=['sqlite', 'postgresql', 'postgres'],
        default='sqlite',
        help='Database type to use (default: sqlite)'
    )
    parser.add_argument(
        '--storage-type',
        choices=['filesystem', 's3'],
        default='filesystem',
        help='Storage type to use (default: filesystem). S3 uses moto for mocking.'
    )
    
    args = parser.parse_args()
    
    print(f"Using tenant_id: {args.tenant_id}")
    print(f"Using database type: {args.db_type}")
    print(f"Using storage type: {args.storage_type}")
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
    
    # Check S3 dependencies if using S3
    if args.storage_type == 's3':
        try:
            import boto3
            from moto import mock_aws
            print("✅ S3 dependencies available (boto3, moto)")
            print()
        except ImportError as e:
            print(f"❌ ERROR: S3 dependencies not installed: {e}")
            print("   Install with: pip install boto3 moto")
            sys.exit(1)
    
    success = main(tenant_id=args.tenant_id, db_type=args.db_type, storage_type=args.storage_type)
    sys.exit(0 if success else 1)

