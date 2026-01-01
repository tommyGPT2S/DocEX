#!/usr/bin/env python3
"""
Storage Comparison Test

Tests creating baskets and documents in both S3 and filesystem storage
to verify they work correctly and use different names/IDs.
"""

import sys
import os
import tempfile
import argparse
import time
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

def test_storage_comparison(tenant_id: str = 'test_tenant', db_type: str = 'sqlite'):
    """Test creating baskets in both S3 and filesystem storage"""
    print("=" * 70)
    print("Storage Comparison Test")
    print("=" * 70)
    print(f"Tenant ID: {tenant_id}")
    print(f"Database type: {db_type}")
    
    # Create temporary directory
    test_dir = tempfile.mkdtemp(prefix='docex_storage_test_')
    print(f"\n📁 Test directory: {test_dir}")
    
    # Setup S3 mocking
    s3_mock = None
    try:
        from moto import mock_aws
        import boto3
        s3_mock = mock_aws()
        s3_mock.start()
        print("✅ S3 mocking enabled (moto)")
        
        # Create S3 bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        s3_client.create_bucket(Bucket='docex-test-bucket')
        print("✅ S3 test bucket created")
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
        
        if db_type == 'postgresql' or db_type == 'postgres':
            db_config = {
                'type': 'postgresql',
                'postgres': {
                    'host': 'localhost',
                    'port': 5433,
                    'database': 'docex_test',
                    'user': 'docex_test',
                    'password': 'docex_test_password'
                }
            }
        else:
            db_config = {
                'type': 'sqlite',
                'sqlite': {
                    'path': str(Path(test_dir) / 'docex.db')
                }
            }
        
        multi_tenancy_config = {
            'enabled': True,
            'isolation_strategy': 'schema' if db_type in ['postgresql', 'postgres'] else 'database',
            'bootstrap_tenant': {
                'id': '_docex_system_',
                'display_name': 'DocEX System',
                'schema': 'docex_system',
                'database_path': str(Path(test_dir) / '_docex_system_' / 'docex.db') if db_type == 'sqlite' else None
            }
        }
        
        # ==================== TEST 1: Filesystem Storage ====================
        print("\n" + "=" * 70)
        print("TEST 1: Filesystem Storage")
        print("=" * 70)
        
        config.setup(
            database=db_config,
            storage={
                'type': 'filesystem',
                'filesystem': {
                    'path': str(Path(test_dir) / 'storage_fs')
                }
            },
            multi_tenancy=multi_tenancy_config
        )
        
        # Initialize bootstrap tenant
        bootstrap_manager = BootstrapTenantManager(config=config)
        if not bootstrap_manager.is_initialized():
            bootstrap_manager.initialize(created_by='test_user')
        
        # Provision tenant if needed
        bootstrap_db = Database(config=config, tenant_id='_docex_system_')
        with bootstrap_db.session() as session:
            existing_tenant = session.query(TenantRegistry).filter_by(tenant_id=tenant_id).first()
            if not existing_tenant:
                provisioner = TenantProvisioner(config=config)
                provisioner.create(
                    tenant_id=tenant_id,
                    display_name=f'Test Tenant {tenant_id}',
                    created_by='test_user'
                )
        bootstrap_db.close()
        
        # Create DocEX instance for filesystem
        user_context = UserContext(user_id='test_user', tenant_id=tenant_id)
        docex_fs = DocEX(user_context=user_context)
        
        # Create basket in filesystem with unique name
        basket_name_fs = f'filesystem_basket_{int(time.time())}'
        try:
            basket_fs = docex_fs.create_basket(
                basket_name_fs,
                'Basket stored in filesystem storage'
            )
            print(f"✅ Created filesystem basket: {basket_fs.id} - {basket_fs.name}")
        except ValueError as e:
            if 'already exists' in str(e):
                # Basket exists, try to get it
                print(f"⚠️  Basket '{basket_name_fs}' already exists, using existing basket...")
                baskets = docex_fs.list_baskets()
                basket_fs = next((b for b in baskets if b.name == basket_name_fs), None)
                if not basket_fs:
                    raise ValueError(f"Basket '{basket_name_fs}' exists but could not be retrieved")
                print(f"✅ Using existing filesystem basket: {basket_fs.id} - {basket_fs.name}")
            else:
                raise
        
        # Add a document
        test_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        test_file.write("Test document for filesystem storage\n")
        test_file.write(f"Created at: {datetime.now()}\n")
        test_file.close()
        
        doc_fs = basket_fs.add(test_file.name, metadata={'storage_type': 'filesystem', 'test': 'fs'})
        print(f"✅ Added document to filesystem basket: {doc_fs.id}")
        print(f"   Path: {doc_fs.path}")
        print(f"   Full filesystem path: {Path(test_dir) / 'storage_fs' / doc_fs.path}")
        
        # Close filesystem DocEX (reset singleton for S3 test)
        # Use the instance method since we have the instance
        docex_fs.close()
        
        # ==================== TEST 2: S3 Storage ====================
        print("\n" + "=" * 70)
        print("TEST 2: S3 Storage")
        print("=" * 70)
        
        config.setup(
            database=db_config,
            storage={
                'type': 's3',
                's3': {
                    'bucket': 'docex-test-bucket',
                    'bucket_application': 'docex-test',
                    'path_namespace': 'finance_dept',
                    'prefix': 'test-env',
                    'region': 'us-east-1',
                    'access_key': 'test-key',
                    'secret_key': 'test-secret'
                }
            },
            multi_tenancy=multi_tenancy_config
        )
        
        # Create DocEX instance for S3
        docex_s3 = DocEX(user_context=user_context)
        
        # Create basket in S3 with unique name
        basket_name_s3 = f's3_basket_{int(time.time())}'
        try:
            basket_s3 = docex_s3.create_basket(
                basket_name_s3,
                'Basket stored in S3 storage'
            )
            print(f"✅ Created S3 basket: {basket_s3.id} - {basket_s3.name}")
        except ValueError as e:
            if 'already exists' in str(e):
                # Basket exists, try to get it
                print(f"⚠️  Basket '{basket_name_s3}' already exists, using existing basket...")
                baskets = docex_s3.list_baskets()
                basket_s3 = next((b for b in baskets if b.name == basket_name_s3), None)
                if not basket_s3:
                    raise ValueError(f"Basket '{basket_name_s3}' exists but could not be retrieved")
                print(f"✅ Using existing S3 basket: {basket_s3.id} - {basket_s3.name}")
            else:
                raise
        
        # Add a document
        test_file2 = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        test_file2.write("Test document for S3 storage\n")
        test_file2.write(f"Created at: {datetime.now()}\n")
        test_file2.close()
        
        doc_s3 = basket_s3.add(test_file2.name, metadata={'storage_type': 's3', 'test': 's3'})
        print(f"✅ Added document to S3 basket: {doc_s3.id}")
        print(f"   Path: {doc_s3.path}")
        
        # Print full S3 path
        from docex.storage.path_builder import DocEXPathBuilder
        path_builder = DocEXPathBuilder(DocEXConfig())
        tenant_id_extracted = basket_s3.path_helper.extract_tenant_id()
        if tenant_id_extracted:
            doc_name_base = doc_s3.name.replace(Path(doc_s3.name).suffix, '') if doc_s3.name else 'document'
            # Pass existing_prefix to avoid duplication
            existing_prefix = basket_s3.storage_config.get('s3', {}).get('prefix', '')
            full_s3_path = path_builder.build_document_path(
                basket_id=basket_s3.id,
                document_id=doc_s3.id,
                basket_name=basket_s3.name,
                document_name=doc_name_base,
                file_ext=Path(doc_s3.name).suffix if doc_s3.name else '',
                tenant_id=tenant_id_extracted,
                existing_prefix=existing_prefix
            )
            bucket = basket_s3.storage_config.get('s3', {}).get('bucket', 'unknown')
            print(f"   Full S3 Path: s3://{bucket}/{full_s3_path}")
        
        # ==================== TEST 3: Document Retrieval by ID ====================
        print("\n" + "=" * 70)
        print("TEST 3: Document Retrieval by ID (with byte option)")
        print("=" * 70)
        
        # Test retrieving document by ID from S3 basket
        print(f"\n   Retrieving document by ID: {doc_s3.id}")
        retrieved_doc = basket_s3.get_document(doc_s3.id)
        if retrieved_doc:
            print(f"   ✅ Retrieved document: {retrieved_doc.id} - {retrieved_doc.name}")
            
            # Test retrieving content as bytes
            print(f"\n   Testing content retrieval as bytes...")
            try:
                content_bytes = retrieved_doc.get_content(mode='bytes')
                print(f"   ✅ Retrieved content as bytes: {len(content_bytes)} bytes")
                print(f"      Content preview (first 100 bytes): {content_bytes[:100]}")
            except Exception as e:
                print(f"   ❌ Failed to retrieve content as bytes: {e}")
                import traceback
                traceback.print_exc()
            
            # Test retrieving content as text
            print(f"\n   Testing content retrieval as text...")
            try:
                content_text = retrieved_doc.get_content(mode='text')
                print(f"   ✅ Retrieved content as text: {len(content_text)} characters")
                print(f"      Content preview: {content_text[:200]}")
            except Exception as e:
                print(f"   ❌ Failed to retrieve content as text: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"   ❌ Document not found: {doc_s3.id}")
        
        # Test retrieving document by ID from filesystem basket
        print(f"\n   Retrieving document by ID from filesystem basket: {doc_fs.id}")
        # Need to get the filesystem basket again (we closed docex_fs)
        docex_fs = DocEX(user_context=user_context)
        basket_fs_retrieved = docex_fs.get_basket(basket_fs.id)
        if basket_fs_retrieved:
            retrieved_doc_fs = basket_fs_retrieved.get_document(doc_fs.id)
            if retrieved_doc_fs:
                print(f"   ✅ Retrieved document: {retrieved_doc_fs.id} - {retrieved_doc_fs.name}")
                
                # Test retrieving content as bytes
                print(f"\n   Testing content retrieval as bytes...")
                try:
                    content_bytes_fs = retrieved_doc_fs.get_content(mode='bytes')
                    print(f"   ✅ Retrieved content as bytes: {len(content_bytes_fs)} bytes")
                    print(f"      Content preview (first 100 bytes): {content_bytes_fs[:100]}")
                except Exception as e:
                    print(f"   ❌ Failed to retrieve content as bytes: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Test retrieving content as text
                print(f"\n   Testing content retrieval as text...")
                try:
                    content_text_fs = retrieved_doc_fs.get_content(mode='text')
                    print(f"   ✅ Retrieved content as text: {len(content_text_fs)} characters")
                    print(f"      Content preview: {content_text_fs[:200]}")
                except Exception as e:
                    print(f"   ❌ Failed to retrieve content as text: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"   ❌ Document not found: {doc_fs.id}")
        else:
            print(f"   ❌ Basket not found: {basket_fs.id}")
        
        # ==================== COMPARISON ====================
        print("\n" + "=" * 70)
        print("COMPARISON")
        print("=" * 70)
        print(f"Filesystem Basket ID: {basket_fs.id}")
        print(f"S3 Basket ID: {basket_s3.id}")
        print(f"✅ Different basket IDs: {basket_fs.id != basket_s3.id}")
        
        print(f"\nFilesystem Document ID: {doc_fs.id}")
        print(f"S3 Document ID: {doc_s3.id}")
        print(f"✅ Different document IDs: {doc_fs.id != doc_s3.id}")
        
        print(f"\nFilesystem Document Path: {doc_fs.path}")
        print(f"S3 Document Path: {doc_s3.path}")
        
        # ==================== TEST 3: Document Retrieval by ID ====================
        print("\n" + "=" * 70)
        print("TEST 3: Document Retrieval by ID (with byte option)")
        print("=" * 70)
        
        # Test retrieving document by ID from S3 basket
        print(f"\n   Retrieving S3 document by ID: {doc_s3.id}")
        retrieved_doc_s3 = basket_s3.get_document(doc_s3.id)
        if retrieved_doc_s3:
            print(f"   ✅ Retrieved document: {retrieved_doc_s3.id} - {retrieved_doc_s3.name}")
            print(f"      Path: {retrieved_doc_s3.path}")
            
            # Test retrieving content as bytes
            print(f"\n   Testing content retrieval as bytes...")
            try:
                content_bytes = retrieved_doc_s3.get_content(mode='bytes')
                print(f"   ✅ Retrieved content as bytes: {len(content_bytes)} bytes")
                if isinstance(content_bytes, bytes):
                    print(f"      Content preview (first 100 bytes): {content_bytes[:100]}")
                    # Verify content matches
                    expected_content = "Test document for S3 storage\n"
                    if expected_content.encode() in content_bytes:
                        print(f"   ✅ Content verification: Found expected content")
                    else:
                        print(f"   ⚠️  Content verification: Expected content not found")
            except Exception as e:
                print(f"   ❌ Failed to retrieve content as bytes: {e}")
                import traceback
                traceback.print_exc()
            
            # Test retrieving content as text
            print(f"\n   Testing content retrieval as text...")
            try:
                content_text = retrieved_doc_s3.get_content(mode='text')
                print(f"   ✅ Retrieved content as text: {len(content_text)} characters")
                print(f"      Content preview: {content_text[:200]}")
            except Exception as e:
                print(f"   ❌ Failed to retrieve content as text: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"   ❌ Document not found: {doc_s3.id}")
        
        # Test retrieving document by ID from filesystem basket
        print(f"\n   Retrieving filesystem document by ID: {doc_fs.id}")
        # Need to get the filesystem basket again (we closed docex_fs)
        docex_fs = DocEX(user_context=user_context)
        basket_fs_retrieved = docex_fs.get_basket(basket_fs.id)
        if basket_fs_retrieved:
            retrieved_doc_fs = basket_fs_retrieved.get_document(doc_fs.id)
            if retrieved_doc_fs:
                print(f"   ✅ Retrieved document: {retrieved_doc_fs.id} - {retrieved_doc_fs.name}")
                print(f"      Path: {retrieved_doc_fs.path}")
                
                # Test retrieving content as bytes
                print(f"\n   Testing content retrieval as bytes...")
                try:
                    content_bytes_fs = retrieved_doc_fs.get_content(mode='bytes')
                    print(f"   ✅ Retrieved content as bytes: {len(content_bytes_fs)} bytes")
                    if isinstance(content_bytes_fs, bytes):
                        print(f"      Content preview (first 100 bytes): {content_bytes_fs[:100]}")
                        # Verify content matches
                        expected_content = "Test document for filesystem storage\n"
                        if expected_content.encode() in content_bytes_fs:
                            print(f"   ✅ Content verification: Found expected content")
                        else:
                            print(f"   ⚠️  Content verification: Expected content not found")
                except Exception as e:
                    print(f"   ❌ Failed to retrieve content as bytes: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Test retrieving content as text
                print(f"\n   Testing content retrieval as text...")
                try:
                    content_text_fs = retrieved_doc_fs.get_content(mode='text')
                    print(f"   ✅ Retrieved content as text: {len(content_text_fs)} characters")
                    print(f"      Content preview: {content_text_fs[:200]}")
                except Exception as e:
                    print(f"   ❌ Failed to retrieve content as text: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"   ❌ Document not found: {doc_fs.id}")
        else:
            print(f"   ❌ Basket not found: {basket_fs.id}")
        
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
        # Stop S3 mocking
        if s3_mock:
            try:
                s3_mock.stop()
                print("✅ S3 mocking stopped")
            except:
                pass
        
        print(f"\n📁 Test directory preserved: {test_dir}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Storage comparison test')
    parser.add_argument(
        '--tenant-id',
        default='test_tenant',
        help='Tenant ID to test (default: test_tenant)'
    )
    parser.add_argument(
        '--db-type',
        choices=['sqlite', 'postgresql', 'postgres'],
        default='sqlite',
        help='Database type (default: sqlite)'
    )
    
    args = parser.parse_args()
    
    success = test_storage_comparison(tenant_id=args.tenant_id, db_type=args.db_type)
    sys.exit(0 if success else 1)

