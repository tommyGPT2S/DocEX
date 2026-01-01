"""
Test PostgreSQL with S3 to verify basket and document definitions match physical S3 locations.

This test verifies that:
1. Basket storage_config in PostgreSQL matches the actual S3 prefix structure
2. Document paths in PostgreSQL match the actual S3 keys where documents are stored
3. Multi-tenant isolation is maintained in both database and S3
"""

import os
import tempfile
import shutil
from pathlib import Path
import pytest
from moto import mock_aws
import boto3
import json

from docex.config.docex_config import DocEXConfig
from docex.db.connection import Database
from docex.provisioning.bootstrap import BootstrapTenantManager
from docex.provisioning.tenant_provisioner import TenantProvisioner
from docex.docCore import DocEX, UserContext
from docex.db.models import DocBasket as DocBasketModel, Document as DocumentModel

# Use mock_aws as a decorator (it mocks all AWS services including S3)
mock_s3 = mock_aws

@pytest.fixture(scope="function")
def s3_setup():
    with mock_s3():
        s3_client = boto3.client("s3", region_name="us-east-1")
        bucket_name = "test-docex-bucket"
        s3_client.create_bucket(Bucket=bucket_name)
        yield s3_client, bucket_name

@pytest.fixture(scope="function")
def postgres_config():
    """Setup PostgreSQL configuration for testing"""
    return {
        'database': {
            'type': 'postgresql',
            'postgres': {
                'host': 'localhost',
                'port': 5433,
                'database': 'docex_test',
                'user': 'docex_test',
                'password': 'docex_test_password'
            }
        },
        'storage': {
            'type': 's3',
            's3': {
                'bucket': 'test-docex-bucket',
                'app_name': 'acme-corp',
                'prefix': 'production',
                'region': 'us-east-1',
                'access_key': 'test-key',
                'secret_key': 'test-secret'
            }
        },
        'multi_tenancy': {
            'enabled': True,
            'isolation_strategy': 'schema',
            'bootstrap_tenant': {
                'id': '_docex_system_',
                'display_name': 'DocEX System',
                'schema': 'docex_system'
            }
        }
    }

def test_postgres_s3_basket_path_match(s3_setup, postgres_config):
    """Test that basket storage_config in PostgreSQL matches S3 prefix structure"""
    print("\n" + "="*60)
    print("TEST: PostgreSQL Basket Storage Config vs S3 Prefix")
    print("="*60)
    
    s3_client, bucket_name = s3_setup
    
    try:
        # Setup DocEX config
        DocEXConfig.setup(**postgres_config)
        config = DocEXConfig()
        
        # Initialize bootstrap tenant
        print("\n1. Initializing bootstrap tenant...")
        bootstrap_manager = BootstrapTenantManager(config)
        if not bootstrap_manager.is_initialized():
            bootstrap_manager.initialize(created_by='test_user')
        print("   ✅ Bootstrap tenant initialized")
        
        # Provision test tenant
        print("\n2. Provisioning tenant 'acme'...")
        provisioner = TenantProvisioner(config)
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
        
        # Create DocEX instance for acme
        print("\n3. Creating DocEX instance for tenant 'acme'...")
        acme_user_context = UserContext(
            user_id='acme_user',
            tenant_id='acme',
            roles=['user']
        )
        acme_docex = DocEX(user_context=acme_user_context)
        print("   ✅ DocEX created for acme")
        
        # Get tenant-aware storage config
        from docex.config.config_resolver import ConfigResolver
        resolver = ConfigResolver(config)
        acme_storage_config = resolver.get_storage_config_for_tenant('acme')
        expected_prefix = acme_storage_config['s3']['prefix']
        print(f"\n4. Expected S3 prefix from ConfigResolver: {expected_prefix}")
        
        # Create basket with unique name
        import uuid
        basket_name = f'test_basket_{uuid.uuid4().hex[:8]}'
        print(f"\n5. Creating document basket '{basket_name}'...")
        basket = acme_docex.create_basket(basket_name, storage_config=acme_storage_config)
        print(f"   ✅ Basket created: {basket.id}")
        
        # Query basket from PostgreSQL
        print("\n6. Querying basket from PostgreSQL...")
        acme_db = Database(config=config, tenant_id='acme')
        with acme_db.session() as session:
            basket_model = session.query(DocBasketModel).filter_by(id=basket.id).first()
            assert basket_model is not None, "Basket not found in PostgreSQL"
            
            stored_storage_config = json.loads(basket_model.storage_config) if isinstance(basket_model.storage_config, str) else basket_model.storage_config
            stored_prefix = stored_storage_config.get('s3', {}).get('prefix', '')
            print(f"   Stored prefix in PostgreSQL: {stored_prefix}")
            
            # Verify prefix matches expected structure
            assert 'tenant_acme' in stored_prefix, f"Prefix should contain 'tenant_acme', got: {stored_prefix}"
            assert stored_prefix.startswith('acme-corp/production/tenant_acme'), \
                f"Prefix should start with 'acme-corp/production/tenant_acme', got: {stored_prefix}"
            print("   ✅ Basket storage_config prefix matches expected structure")
        
        # Verify S3 prefix structure
        print("\n7. Verifying S3 prefix structure...")
        from docex.storage.s3_storage import S3Storage
        s3_storage = S3Storage(stored_storage_config['s3'])
        test_key = s3_storage._get_full_key('test/document.txt')
        print(f"   Full S3 key for test document: {test_key}")
        
        assert test_key.startswith('acme-corp/production/tenant_acme'), \
            f"S3 key should start with 'acme-corp/production/tenant_acme', got: {test_key}"
        print("   ✅ S3 key structure matches database prefix")
        
        print("\n✅ TEST PASSED: Basket storage_config matches S3 prefix structure")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise

def test_postgres_s3_document_path_match(s3_setup, postgres_config):
    """Test that document paths in PostgreSQL match actual S3 keys"""
    print("\n" + "="*60)
    print("TEST: PostgreSQL Document Path vs S3 Key")
    print("="*60)
    
    s3_client, bucket_name = s3_setup
    
    try:
        # Setup DocEX config
        DocEXConfig.setup(**postgres_config)
        config = DocEXConfig()
        
        # Initialize bootstrap tenant
        print("\n1. Initializing bootstrap tenant...")
        bootstrap_manager = BootstrapTenantManager(config)
        if not bootstrap_manager.is_initialized():
            bootstrap_manager.initialize(created_by='test_user')
        print("   ✅ Bootstrap tenant initialized")
        
        # Provision test tenant
        print("\n2. Provisioning tenant 'acme'...")
        provisioner = TenantProvisioner(config)
        bootstrap_db = Database(config=config, tenant_id='_docex_system_')
        from docex.db.tenant_registry_model import TenantRegistry
        with bootstrap_db.session() as session:
            existing = session.query(TenantRegistry).filter_by(tenant_id='acme').first()
            if not existing:
                provisioner.create(
                    tenant_id='acme',
                    display_name='Acme Corporation',
                    created_by='test_user'
                )
        print("   ✅ Tenant 'acme' provisioned")
        
        # Create DocEX instance for acme
        print("\n3. Creating DocEX instance for tenant 'acme'...")
        acme_user_context = UserContext(
            user_id='acme_user',
            tenant_id='acme',
            roles=['user']
        )
        acme_docex = DocEX(user_context=acme_user_context)
        print("   ✅ DocEX created for acme")
        
        # Get tenant-aware storage config
        from docex.config.config_resolver import ConfigResolver
        resolver = ConfigResolver(config)
        acme_storage_config = resolver.get_storage_config_for_tenant('acme')
        
        # Create basket with unique name
        import uuid
        basket_name = f'test_basket_{uuid.uuid4().hex[:8]}'
        print(f"\n4. Creating document basket '{basket_name}'...")
        basket = acme_docex.create_basket(basket_name, storage_config=acme_storage_config)
        print(f"   ✅ Basket created: {basket.id}")
        
        # Add document
        print("\n5. Adding document to basket...")
        test_file = Path(tempfile.gettempdir()) / 'test_doc.txt'
        test_file.write_text("Test document content")
        
        doc = basket.add(str(test_file))
        print(f"   ✅ Document added: {doc.id}")
        
        # Query document from PostgreSQL
        print("\n6. Querying document from PostgreSQL...")
        acme_db = Database(config=config, tenant_id='acme')
        with acme_db.session() as session:
            doc_model = session.query(DocumentModel).filter_by(id=doc.id).first()
            assert doc_model is not None, "Document not found in PostgreSQL"
            
            stored_path = doc_model.path
            print(f"   Document path in PostgreSQL: {stored_path}")
            
            # Get basket storage config
            basket_model = session.query(DocBasketModel).filter_by(id=basket.id).first()
            stored_storage_config = json.loads(basket_model.storage_config) if isinstance(basket_model.storage_config, str) else basket_model.storage_config
            stored_prefix = stored_storage_config.get('s3', {}).get('prefix', '')
            print(f"   Basket prefix in PostgreSQL: {stored_prefix}")
            
            # Construct expected S3 key
            from docex.storage.s3_storage import S3Storage
            s3_storage = S3Storage(stored_storage_config['s3'])
            expected_s3_key = s3_storage._get_full_key(stored_path)
            print(f"   Expected S3 key: {expected_s3_key}")
            
            # Verify document exists in S3 at expected location
            print("\n7. Verifying document in S3...")
            try:
                s3_client.head_object(Bucket=bucket_name, Key=expected_s3_key)
                print(f"   ✅ Document found in S3 at: {expected_s3_key}")
            except s3_client.exceptions.NoSuchKey:
                # List all objects to see what's actually there
                all_objects = s3_client.list_objects_v2(Bucket=bucket_name)
                all_keys = [obj['Key'] for obj in all_objects.get('Contents', [])]
                print(f"   ❌ Document not found at expected key")
                print(f"   Available S3 keys: {all_keys}")
                # Check if document exists with different key
                matching_keys = [k for k in all_keys if doc.id in k]
                if matching_keys:
                    print(f"   Found document with different key: {matching_keys[0]}")
                    raise AssertionError(
                        f"Document path mismatch: Expected '{expected_s3_key}', "
                        f"but document found at '{matching_keys[0]}'"
                    )
                else:
                    raise AssertionError(f"Document not found in S3. Expected key: {expected_s3_key}")
        
        print("\n✅ TEST PASSED: Document path in PostgreSQL matches S3 key")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    finally:
        # Cleanup
        if test_file.exists():
            test_file.unlink()

def test_postgres_s3_multi_tenant_isolation(s3_setup, postgres_config):
    """Test that multi-tenant isolation is maintained in both PostgreSQL and S3"""
    print("\n" + "="*60)
    print("TEST: Multi-Tenant Isolation (PostgreSQL + S3)")
    print("="*60)
    
    s3_client, bucket_name = s3_setup
    
    try:
        # Setup DocEX config
        DocEXConfig.setup(**postgres_config)
        config = DocEXConfig()
        
        # Initialize bootstrap tenant
        print("\n1. Initializing bootstrap tenant...")
        bootstrap_manager = BootstrapTenantManager(config)
        if not bootstrap_manager.is_initialized():
            bootstrap_manager.initialize(created_by='test_user')
        print("   ✅ Bootstrap tenant initialized")
        
        # Provision tenants
        print("\n2. Provisioning tenants...")
        provisioner = TenantProvisioner(config)
        bootstrap_db = Database(config=config, tenant_id='_docex_system_')
        from docex.db.tenant_registry_model import TenantRegistry
        
        for tenant_id, display_name in [('acme', 'Acme Corp'), ('contoso', 'Contoso Ltd')]:
            with bootstrap_db.session() as session:
                existing = session.query(TenantRegistry).filter_by(tenant_id=tenant_id).first()
                if not existing:
                    provisioner.create(
                        tenant_id=tenant_id,
                        display_name=display_name,
                        created_by='test_user'
                    )
            print(f"   ✅ Tenant '{tenant_id}' provisioned")
        
        # Create baskets for each tenant
        print("\n3. Creating baskets for each tenant...")
        from docex.config.config_resolver import ConfigResolver
        resolver = ConfigResolver(config)
        
        baskets = {}
        for tenant_id in ['acme', 'contoso']:
            # Create a fresh DocEX instance for each tenant to ensure correct tenant isolation
            user_context = UserContext(
                user_id=f'{tenant_id}_user',
                tenant_id=tenant_id,
                roles=['user']
            )
            # Reset DocEX singleton by creating new instance
            # This ensures the database connection is correctly set for each tenant
            docex = DocEX(user_context=user_context)
            storage_config = resolver.get_storage_config_for_tenant(tenant_id)
            import uuid
            basket_name = f'{tenant_id}_basket_{uuid.uuid4().hex[:8]}'
            basket = docex.create_basket(basket_name, storage_config=storage_config)
            baskets[tenant_id] = basket
            print(f"   ✅ Basket created for {tenant_id}: {basket.id} (name: {basket_name})")
        
        # Add documents to each basket
        print("\n4. Adding documents to each basket...")
        documents = {}
        # IMPORTANT: Process tenants in separate loops to avoid tenant switching issues
        # In practice, developers should process one tenant at a time, or ensure
        # basket objects are used with their original tenant context
        for tenant_id in ['acme', 'contoso']:
            # Get the basket for this tenant
            basket = baskets[tenant_id]
            
            # Verify basket belongs to this tenant
            basket_tenant_id = getattr(basket.db, 'tenant_id', None)
            print(f"   Processing tenant {tenant_id}, basket {basket.id} belongs to tenant: {basket_tenant_id}")
            assert basket_tenant_id == tenant_id, \
                f"Basket {basket.id} belongs to tenant {basket_tenant_id}, but we're processing {tenant_id}"
            
            # Create DocEX instance with correct tenant context
            # This ensures the singleton is set correctly, though basket uses its own db connection
            user_context = UserContext(
                user_id=f'{tenant_id}_user',
                tenant_id=tenant_id,
                roles=['user']
            )
            docex = DocEX(user_context=user_context)
            
            # Verify DocEX singleton is set to correct tenant
            docex_tenant_id = getattr(docex.db, 'tenant_id', None)
            assert docex_tenant_id == tenant_id, \
                f"DocEX singleton is set to tenant {docex_tenant_id}, but we're processing {tenant_id}"
            
            # Add document - basket.add() uses basket.db which should be tenant-specific
            test_file = Path(tempfile.gettempdir()) / f'{tenant_id}_doc.txt'
            test_file.write_text(f"Document for {tenant_id}")
            doc = basket.add(str(test_file))
            documents[tenant_id] = doc
            print(f"   ✅ Document added for {tenant_id}: {doc.id}")
        
        # Verify isolation in PostgreSQL
        print("\n5. Verifying isolation in PostgreSQL...")
        for tenant_id in ['acme', 'contoso']:
            tenant_db = Database(config=config, tenant_id=tenant_id)
            with tenant_db.session() as session:
                # Query baskets - should only see own tenant's baskets
                tenant_baskets = session.query(DocBasketModel).all()
                print(f"   {tenant_id} schema has {len(tenant_baskets)} basket(s)")
                
                # Verify each basket has correct prefix
                for basket_model in tenant_baskets:
                    stored_config = json.loads(basket_model.storage_config) if isinstance(basket_model.storage_config, str) else basket_model.storage_config
                    stored_prefix = stored_config.get('s3', {}).get('prefix', '')
                    assert f'tenant_{tenant_id}' in stored_prefix, \
                        f"Basket in {tenant_id} schema should have 'tenant_{tenant_id}' in prefix, got: {stored_prefix}"
                    print(f"   ✅ Basket {basket_model.id} has correct prefix: {stored_prefix}")
        
        # Verify isolation in S3
        print("\n6. Verifying isolation in S3...")
        all_objects = s3_client.list_objects_v2(Bucket=bucket_name)
        all_keys = [obj['Key'] for obj in all_objects.get('Contents', [])]
        
        acme_keys = [k for k in all_keys if 'tenant_acme' in k]
        contoso_keys = [k for k in all_keys if 'tenant_contoso' in k]
        
        print(f"   Acme documents in S3: {len(acme_keys)}")
        print(f"   Contoso documents in S3: {len(contoso_keys)}")
        
        assert len(acme_keys) > 0, "Acme should have documents in S3"
        assert len(contoso_keys) > 0, "Contoso should have documents in S3"
        
        # Verify no cross-tenant access
        assert all('tenant_acme' in k for k in acme_keys), "All acme keys should contain 'tenant_acme'"
        assert all('tenant_contoso' in k for k in contoso_keys), "All contoso keys should contain 'tenant_contoso'"
        assert not any('tenant_contoso' in k for k in acme_keys), "Acme keys should not contain 'tenant_contoso'"
        assert not any('tenant_acme' in k for k in contoso_keys), "Contoso keys should not contain 'tenant_acme'"
        
        print("   ✅ Tenant isolation verified in S3")
        
        print("\n✅ TEST PASSED: Multi-tenant isolation maintained in PostgreSQL and S3")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    finally:
        # Cleanup
        for tenant_id in ['acme', 'contoso']:
            test_file = Path(tempfile.gettempdir()) / f'{tenant_id}_doc.txt'
            if test_file.exists():
                test_file.unlink()

if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v', '-s'])

