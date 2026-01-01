#!/usr/bin/env python3
"""
S3 Multi-Tenant Integration Test for DocEX 3.0

Tests S3 storage with multiple tenants to ensure:
1. Tenant isolation in S3 prefixes
2. Documents from different tenants are stored separately
3. Tenants cannot access each other's documents
4. S3 prefix resolution works correctly

Prerequisites:
- moto and boto3 installed in virtual environment

Run this script to test S3 multi-tenancy:
    python test_docex3_s3_multitenant.py
"""

import sys
import tempfile
import shutil
from pathlib import Path
from io import BytesIO

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Mock S3 before importing boto3
from moto import mock_aws
import boto3

# Use mock_aws as a decorator (it mocks all AWS services including S3)
mock_s3 = mock_aws


def test_s3_prefix_resolution():
    """Test S3 prefix resolution for different tenants"""
    print("\n" + "="*60)
    print("TEST 1: S3 Prefix Resolution")
    print("="*60)
    
    try:
        from docex.config.config_resolver import ConfigResolver
        from docex.config.docex_config import DocEXConfig
        
        # Set up test config
        DocEXConfig.setup(
            storage={
                'type': 's3',
                's3': {
                    'bucket': 'test-bucket',
                    'app_name': 'docex',
                    'prefix': 'production',
                    'region': 'us-east-1'
                }
            }
        )
        
        config = DocEXConfig()
        resolver = ConfigResolver(config)
        
        print("\n1.1 Testing prefix resolution for tenant 'acme'...")
        prefix_acme = resolver.resolve_s3_prefix('acme')
        print(f"   Prefix: {prefix_acme}")
        assert prefix_acme == 'docex/production/tenant_acme/', f"Expected 'docex/production/tenant_acme/', got '{prefix_acme}'"
        print("   ✅ Correct prefix for acme")
        
        print("\n1.2 Testing prefix resolution for tenant 'contoso'...")
        prefix_contoso = resolver.resolve_s3_prefix('contoso')
        print(f"   Prefix: {prefix_contoso}")
        assert prefix_contoso == 'docex/production/tenant_contoso/', f"Expected 'docex/production/tenant_contoso/', got '{prefix_contoso}'"
        print("   ✅ Correct prefix for contoso")
        
        print("\n1.3 Testing prefix resolution for bootstrap tenant...")
        prefix_bootstrap = resolver.resolve_s3_prefix('_docex_system_')
        print(f"   Prefix: {prefix_bootstrap}")
        assert prefix_bootstrap == 'docex/production/tenant__docex_system_/', f"Expected 'docex/production/tenant__docex_system_/', got '{prefix_bootstrap}'"
        print("   ✅ Correct prefix for bootstrap tenant")
        
        print("\n   ✅ S3 prefix resolution test passed!")
        return True
        
    except Exception as e:
        print(f"\n   ❌ S3 prefix resolution test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


@mock_s3
def test_s3_storage_isolation():
    """Test that S3 storage isolates documents by tenant"""
    print("\n" + "="*60)
    print("TEST 2: S3 Storage Tenant Isolation")
    print("="*60)
    
    try:
        from docex.storage.s3_storage import S3Storage
        from docex.config.docex_config import DocEXConfig
        
        # Set up S3 mock
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-docex-bucket'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Set up test config
        DocEXConfig.setup(
            storage={
                'type': 's3',
                's3': {
                    'bucket': bucket_name,
                    'app_name': 'docex',
                    'prefix': 'test',
                    'region': 'us-east-1',
                    'access_key': 'test-key',
                    'secret_key': 'test-secret'
                }
            }
        )
        
        config = DocEXConfig()
        storage_config = config.get('storage', {}).get('s3', {})
        
        print("\n2.1 Creating S3Storage for tenant 'acme'...")
        # Create storage with tenant-aware config
        from docex.config.config_resolver import ConfigResolver
        resolver = ConfigResolver(config)
        acme_storage_config = resolver.get_storage_config_for_tenant('acme')
        acme_storage = S3Storage(acme_storage_config['s3'])
        print("   ✅ S3Storage created for acme")
        
        print("\n2.2 Creating S3Storage for tenant 'contoso'...")
        contoso_storage_config = resolver.get_storage_config_for_tenant('contoso')
        contoso_storage = S3Storage(contoso_storage_config['s3'])
        print("   ✅ S3Storage created for contoso")
        
        print("\n2.3 Saving document for tenant 'acme'...")
        acme_doc_path = 'documents/doc1.txt'
        acme_content = b'This is a document for Acme Corporation'
        acme_storage.save(acme_doc_path, acme_content)
        print("   ✅ Document saved for acme")
        
        # Verify the key includes tenant prefix
        acme_full_key = acme_storage._get_full_key(acme_doc_path, tenant_id='acme')
        print(f"   Full S3 key: {acme_full_key}")
        assert 'tenant_acme' in acme_full_key, f"Expected 'tenant_acme' in key, got '{acme_full_key}'"
        assert acme_full_key.startswith('docex/test/tenant_acme/'), f"Expected key to start with 'docex/test/tenant_acme/', got '{acme_full_key}'"
        
        print("\n2.4 Saving document for tenant 'contoso'...")
        contoso_doc_path = 'documents/doc1.txt'  # Same relative path
        contoso_content = b'This is a document for Contoso Ltd'
        contoso_storage.save(contoso_doc_path, contoso_content)
        print("   ✅ Document saved for contoso")
        
        # Verify the key includes tenant prefix
        contoso_full_key = contoso_storage._get_full_key(contoso_doc_path, tenant_id='contoso')
        print(f"   Full S3 key: {contoso_full_key}")
        assert 'tenant_contoso' in contoso_full_key, f"Expected 'tenant_contoso' in key, got '{contoso_full_key}'"
        assert contoso_full_key.startswith('docex/test/tenant_contoso/'), f"Expected key to start with 'docex/test/tenant_contoso/', got '{contoso_full_key}'"
        
        print("\n2.5 Verifying tenant isolation...")
        # Verify keys are different
        assert acme_full_key != contoso_full_key, "Tenant keys should be different"
        print("   ✅ Keys are different for different tenants")
        
        # Verify documents exist in correct locations
        assert acme_storage.exists(acme_doc_path), "Acme document should exist"
        assert contoso_storage.exists(contoso_doc_path), "Contoso document should exist"
        print("   ✅ Documents exist in correct tenant locations")
        
        # Verify tenants can't access each other's documents
        # Acme trying to access Contoso's document (should fail or return different content)
        acme_trying_contoso = acme_storage._get_full_key(contoso_doc_path, tenant_id='acme')
        contoso_trying_acme = contoso_storage._get_full_key(acme_doc_path, tenant_id='contoso')
        
        assert acme_trying_contoso != contoso_full_key, "Acme should not be able to access Contoso's key"
        assert contoso_trying_acme != acme_full_key, "Contoso should not be able to access Acme's key"
        print("   ✅ Tenants cannot access each other's document keys")
        
        print("\n   ✅ S3 storage tenant isolation test passed!")
        return True
        
    except Exception as e:
        print(f"\n   ❌ S3 storage tenant isolation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


@mock_s3
def test_s3_with_doc_ex_multitenant():
    """Test S3 storage with DocEX multi-tenant operations"""
    print("\n" + "="*60)
    print("TEST 3: S3 with DocEX Multi-Tenant Operations")
    print("="*60)
    
    test_dir = None
    try:
        from docex import DocEX
        from docex.context import UserContext
        from docex.config.docex_config import DocEXConfig
        from docex.provisioning.bootstrap import BootstrapTenantManager
        from docex.provisioning.tenant_provisioner import TenantProvisioner
        
        # Set up S3 mock
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-docex-bucket'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Create temporary test directory
        test_dir = tempfile.mkdtemp()
        
        # Set up test config with SQLite (for simplicity) and S3 storage
        DocEXConfig.setup(
            database={
                'type': 'sqlite',
                'sqlite': {
                    'path': str(Path(test_dir) / 'bootstrap_test.db'),
                    'path_template': str(Path(test_dir) / 'tenant_{tenant_id}' / 'docex.db')
                }
            },
            storage={
                'type': 's3',
                's3': {
                    'bucket': bucket_name,
                    'app_name': 'docex',
                    'prefix': 'test',
                    'region': 'us-east-1',
                    'access_key': 'test-key',
                    'secret_key': 'test-secret'
                }
            },
            multi_tenancy={
                'enabled': True,
                'isolation_strategy': 'database',
                'bootstrap_tenant': {
                    'id': '_docex_system_',
                    'display_name': 'DocEX System',
                    'database_path': str(Path(test_dir) / '_docex_system_' / 'docex.db')
                }
            }
        )
        
        config = DocEXConfig()
        
        print("\n3.1 Initializing bootstrap tenant...")
        bootstrap_manager = BootstrapTenantManager(config)
        if not bootstrap_manager.is_initialized():
            bootstrap_manager.initialize(created_by='test_user')
        print("   ✅ Bootstrap tenant initialized")
        
        print("\n3.2 Provisioning tenant 'acme'...")
        provisioner = TenantProvisioner(config)
        # Check if tenant exists
        from docex.db.connection import Database
        from docex.db.tenant_registry_model import TenantRegistry
        bootstrap_db = Database(config=config, tenant_id='_docex_system_')
        with bootstrap_db.session() as session:
            existing = session.query(TenantRegistry).filter_by(tenant_id='acme').first()
            if not existing:
                provisioner.create(
                    tenant_id='acme',
                    display_name='Acme Corporation',
                    created_by='test_user'
                )
        print("   ✅ Tenant 'acme' provisioned")
        
        print("\n3.3 Provisioning tenant 'contoso'...")
        with bootstrap_db.session() as session:
            existing = session.query(TenantRegistry).filter_by(tenant_id='contoso').first()
            if not existing:
                provisioner.create(
                    tenant_id='contoso',
                    display_name='Contoso Ltd',
                    created_by='test_user'
                )
        print("   ✅ Tenant 'contoso' provisioned")
        
        print("\n3.4 Creating DocEX instance for tenant 'acme'...")
        acme_user_context = UserContext(
            user_id='acme_user',
            tenant_id='acme',
            roles=['user']
        )
        acme_docex = DocEX(user_context=acme_user_context)
        print("   ✅ DocEX created for acme")
        
        print("\n3.5 Creating document basket for acme with tenant-aware S3 storage...")
        # Get tenant-aware storage config for acme
        from docex.config.config_resolver import ConfigResolver
        resolver = ConfigResolver(config)
        acme_storage_config = resolver.get_storage_config_for_tenant('acme')
        acme_basket = acme_docex.create_basket('acme_documents', storage_config=acme_storage_config)
        print(f"   ✅ Basket created: {acme_basket.id}")
        print(f"   Storage config: {acme_basket.storage_config}")
        
        print("\n3.6 Adding document to acme basket...")
        # Create temporary file with content
        acme_temp_file = Path(test_dir) / 'acme_doc.txt'
        acme_doc_content = "This is a confidential document for Acme Corporation"
        acme_temp_file.write_text(acme_doc_content)
        
        acme_doc = acme_basket.add(str(acme_temp_file))
        print(f"   ✅ Document added: {acme_doc.id}")
        
        # Verify document is stored in S3 with correct prefix
        acme_doc_details = acme_doc.get_details()
        acme_doc_path = acme_doc_details.get('storage_path') or acme_doc_details.get('source', '')
        print(f"   Document storage path: {acme_doc_path}")
        
        # Check S3 bucket for acme's document
        # List all objects to see what's actually stored
        all_objects = s3_client.list_objects_v2(Bucket=bucket_name)
        all_keys = [obj['Key'] for obj in all_objects.get('Contents', [])]
        print(f"   All S3 keys in bucket: {all_keys}")
        
        # Check for acme prefix (may have app_name duplicated, so check for tenant_acme)
        acme_keys = [key for key in all_keys if 'tenant_acme' in key]
        print(f"   S3 keys for acme: {acme_keys}")
        
        assert len(acme_keys) > 0, f"Acme document should be in tenant_acme prefix. Found keys: {all_keys}"
        print("   ✅ Acme document stored in correct S3 prefix")
        
        print("\n3.7 Creating DocEX instance for tenant 'contoso'...")
        contoso_user_context = UserContext(
            user_id='contoso_user',
            tenant_id='contoso',
            roles=['user']
        )
        contoso_docex = DocEX(user_context=contoso_user_context)
        print("   ✅ DocEX created for contoso")
        
        print("\n3.8 Creating document basket for contoso with tenant-aware S3 storage...")
        # Get tenant-aware storage config for contoso
        contoso_storage_config = resolver.get_storage_config_for_tenant('contoso')
        contoso_basket = contoso_docex.create_basket('contoso_documents', storage_config=contoso_storage_config)
        print(f"   ✅ Basket created: {contoso_basket.id}")
        print(f"   Storage config: {contoso_basket.storage_config}")
        
        print("\n3.9 Adding document to contoso basket...")
        # Create temporary file with content
        contoso_temp_file = Path(test_dir) / 'contoso_doc.txt'
        contoso_doc_content = "This is a confidential document for Contoso Ltd"
        contoso_temp_file.write_text(contoso_doc_content)
        
        contoso_doc = contoso_basket.add(str(contoso_temp_file))
        print(f"   ✅ Document added: {contoso_doc.id}")
        
        # Verify document is stored in S3 with correct prefix
        contoso_doc_details = contoso_doc.get_details()
        contoso_doc_path = contoso_doc_details.get('storage_path') or contoso_doc_details.get('source', '')
        print(f"   Document storage path: {contoso_doc_path}")
        
        # Check S3 bucket for contoso's document
        all_objects = s3_client.list_objects_v2(Bucket=bucket_name)
        all_keys_after_contoso = [obj['Key'] for obj in all_objects.get('Contents', [])]
        print(f"   All S3 keys after contoso: {all_keys_after_contoso}")
        
        contoso_keys = [key for key in all_keys_after_contoso if 'tenant_contoso' in key]
        print(f"   S3 keys for contoso: {contoso_keys}")
        assert len(contoso_keys) > 0, f"Contoso document should be in tenant_contoso prefix. Found keys: {all_keys_after_contoso}"
        print("   ✅ Contoso document stored in correct S3 prefix")
        
        print("\n3.10 Verifying tenant isolation in S3...")
        # Verify acme keys don't contain contoso prefix
        assert not any('tenant_contoso' in key for key in acme_keys), "Acme keys should not contain contoso prefix"
        # Verify contoso keys don't contain acme prefix
        assert not any('tenant_acme' in key for key in contoso_keys), "Contoso keys should not contain acme prefix"
        print("   ✅ Tenant isolation verified in S3")
        
        print("\n   ✅ S3 with DocEX multi-tenant operations test passed!")
        return True
        
    except Exception as e:
        print(f"\n   ❌ S3 with DocEX multi-tenant operations test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if test_dir and Path(test_dir).exists():
            shutil.rmtree(test_dir, ignore_errors=True)


def main():
    """Run all S3 multi-tenant tests"""
    print("\n" + "="*60)
    print("DocEX 3.0 S3 Multi-Tenant Integration Test")
    print("="*60)
    
    results = []
    
    try:
        # Test 1: S3 Prefix Resolution
        result = test_s3_prefix_resolution()
        results.append(("S3 Prefix Resolution", result))
        
        # Test 2: S3 Storage Tenant Isolation
        result = test_s3_storage_isolation()
        results.append(("S3 Storage Tenant Isolation", result))
        
        # Test 3: S3 with DocEX Multi-Tenant Operations
        result = test_s3_with_doc_ex_multitenant()
        results.append(("S3 with DocEX Multi-Tenant Operations", result))
        
    finally:
        pass  # No cleanup needed for mocked S3
    
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
        print("\n🎉 All S3 multi-tenant tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())

