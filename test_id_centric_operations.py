#!/usr/bin/env python3
"""
Test ID-Centric Operations

Verifies that all operations center around basket_id and document_id,
and that paths are built internally using DocEXPathBuilder.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from docex.storage.path_builder import DocEXPathBuilder
from docex.config.docex_config import DocEXConfig
from docex.storage.s3_storage import S3Storage
from moto import mock_aws
import boto3

def test_path_builder():
    """Test DocEXPathBuilder builds paths from IDs"""
    print("=" * 60)
    print("TEST 1: DocEXPathBuilder - Building paths from IDs")
    print("=" * 60)
    
    # Setup config
    config = DocEXConfig()
    config.setup(
        storage={
            'type': 's3',
            's3': {
                'bucket': 'test-bucket',
                'path_namespace': 'acme-corp',
                'prefix': 'production',
                'region': 'us-east-1'
            }
        }
    )
    
    builder = DocEXPathBuilder(config)
    
    # Build document path from IDs
    basket_id = 'bas_1234567890abcdef'
    document_id = 'doc_9876543210fedcba'
    
    full_path = builder.build_document_path(
        basket_id=basket_id,
        document_id=document_id,
        basket_name='invoices',
        document_name='invoice_001',
        file_ext='.pdf',
        tenant_id='acme'
    )
    
    print(f"✅ Built full path from IDs: {full_path}")
    
    # Verify path structure (not exact match, since IDs determine suffixes)
    # Path should contain: path_namespace/prefix/tenant_id/basket_name_{last4}/document_name_{last6}.ext
    assert 'acme-corp' in full_path, "Path namespace should be in path"
    assert 'production' in full_path, "Environment prefix should be in path"
    assert 'acme' in full_path, "Tenant ID should be in path"
    assert 'invoices' in full_path, "Basket name should be in path"
    assert 'invoice_001' in full_path, "Document name should be in path"
    assert full_path.endswith('.pdf'), "Path should end with file extension"
    
    # Verify basket suffix (last 4 of basket_id)
    basket_suffix = basket_id.replace('bas_', '')[-4:] if basket_id.startswith('bas_') else basket_id[-4:]
    assert f"invoices_{basket_suffix}" in full_path, f"Basket path should contain last 4 of basket_id: {basket_suffix}"
    
    # Verify document suffix (last 6 of document_id)
    doc_suffix = document_id.replace('doc_', '')[-6:] if document_id.startswith('doc_') else document_id[-6:]
    assert f"invoice_001_{doc_suffix}.pdf" in full_path, f"Document filename should contain last 6 of document_id: {doc_suffix}"
    
    print(f"✅ Path structure is correct")
    print(f"   - Basket suffix: {basket_suffix}")
    print(f"   - Document suffix: {doc_suffix}")
    
    return True

def test_s3_storage_full_paths():
    """Test S3Storage accepts full paths without interpretation"""
    print("\n" + "=" * 60)
    print("TEST 2: S3Storage - Accepts full paths (no interpretation)")
    print("=" * 60)
    
    with mock_aws():
        # Create S3 bucket
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        
        # Initialize S3Storage with bucket only (no prefix)
        storage = S3Storage({
            'bucket': 'test-bucket',
            'region': 'us-east-1'
        })
        
        # Save with full path (should not interpret or add prefix)
        full_path = 'acme-corp/production/acme/invoices_a1b2/invoice_001_c3d4e5.pdf'
        storage.save(full_path, b'test content')
        print(f"✅ Saved to full path: {full_path}")
        
        # Verify it was saved at the exact path
        response = s3.get_object(Bucket='test-bucket', Key=full_path)
        content = response['Body'].read()
        assert content == b'test content', "Content doesn't match"
        print(f"✅ Retrieved from exact path: {full_path}")
        
        # Verify path exists
        exists = storage.exists(full_path)
        assert exists, "Path should exist"
        print(f"✅ Path exists check passed")
        
        # Load content
        loaded = storage.load(full_path)
        assert loaded == b'test content', "Loaded content doesn't match"
        print(f"✅ Loaded content matches")
        
        # Delete
        deleted = storage.delete(full_path)
        assert deleted, "Delete should succeed"
        print(f"✅ Delete operation succeeded")
        
        # Verify deleted
        exists_after = storage.exists(full_path)
        assert not exists_after, "Path should not exist after delete"
        print(f"✅ Path correctly deleted")
    
    return True

def test_path_builder_filesystem():
    """Test DocEXPathBuilder for filesystem storage"""
    print("\n" + "=" * 60)
    print("TEST 3: DocEXPathBuilder - Filesystem paths")
    print("=" * 60)
    
    config = DocEXConfig()
    config.setup(
        storage={
            'type': 'filesystem',
            'filesystem': {
                'path': 'storage/test-org'
            }
        }
    )
    
    builder = DocEXPathBuilder(config)
    
    # Build filesystem path from IDs
    basket_id = 'bas_1234567890abcdef'
    document_id = 'doc_9876543210fedcba'
    
    full_path = builder.build_document_path(
        basket_id=basket_id,
        document_id=document_id,
        basket_name='invoices',
        document_name='invoice_001',
        file_ext='.pdf',
        tenant_id='acme'
    )
    
    print(f"✅ Built filesystem path from IDs: {full_path}")
    
    # Verify path structure (using actual ID suffixes, not hardcoded)
    assert 'storage/test-org' in full_path, "Base path should be included"
    assert 'acme' in full_path, "Tenant ID should be in path"
    
    # Verify basket suffix (last 4 of basket_id)
    basket_suffix = basket_id.replace('bas_', '')[-4:] if basket_id.startswith('bas_') else basket_id[-4:]
    basket_path = f"invoices_{basket_suffix}"
    assert basket_path in full_path, f"Basket path should contain last 4 of basket_id: {basket_path}"
    
    # Verify document suffix (last 6 of document_id)
    doc_suffix = document_id.replace('doc_', '')[-6:] if document_id.startswith('doc_') else document_id[-6:]
    doc_filename = f"invoice_001_{doc_suffix}.pdf"
    assert doc_filename in full_path, f"Document filename should contain last 6 of document_id: {doc_filename}"
    
    print(f"✅ Filesystem path structure is correct")
    print(f"   - Basket suffix: {basket_suffix}")
    print(f"   - Document suffix: {doc_suffix}")
    
    return True

def test_path_resolver_relationship():
    """Test relationship between DocEXPathBuilder and DocEXPathResolver"""
    print("\n" + "=" * 60)
    print("TEST 4: DocEXPathBuilder uses DocEXPathResolver")
    print("=" * 60)
    
    config = DocEXConfig()
    config.setup(
        storage={
            'type': 's3',
            's3': {
                'bucket': 'test-bucket',
                'path_namespace': 'acme-corp',
                'prefix': 'production',
                'region': 'us-east-1'
            }
        }
    )
    
    builder = DocEXPathBuilder(config)
    
    # Verify builder has path_resolver
    assert hasattr(builder, 'path_resolver'), "DocEXPathBuilder should have path_resolver"
    print(f"✅ DocEXPathBuilder has path_resolver")
    
    # Verify path_resolver can resolve tenant prefix
    tenant_prefix = builder.path_resolver.resolve_s3_prefix('acme')
    print(f"✅ Resolved tenant prefix: {tenant_prefix}")
    assert 'acme-corp' in tenant_prefix, "Path namespace should be in prefix"
    assert 'production' in tenant_prefix, "Environment prefix should be in prefix"
    assert 'acme' in tenant_prefix, "Tenant ID should be in prefix"
    
    return True

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("ID-Centric Operations Test Suite")
    print("=" * 60)
    
    try:
        test_path_builder()
        test_s3_storage_full_paths()
        test_path_builder_filesystem()
        test_path_resolver_relationship()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nSummary:")
        print("  ✅ DocEXPathBuilder builds full paths from IDs")
        print("  ✅ S3Storage accepts full paths (no interpretation)")
        print("  ✅ Filesystem paths work correctly")
        print("  ✅ DocEXPathBuilder uses DocEXPathResolver correctly")
        print("\nAll operations center around basket_id and document_id!")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

