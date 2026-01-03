#!/usr/bin/env python3
"""
Test script for DocEX 2.8.3 performance improvements.

This script demonstrates:
1. list_baskets_with_metadata() with document_count
2. Lazy object instantiation pattern
3. Performance comparisons
4. Both basket and document operations
"""

import sys
import time
import argparse
import tempfile
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from docex import DocEX
from docex.context import UserContext


# Try to import moto for S3 mocking
try:
    from moto import mock_aws
    import boto3
    MOTO_AVAILABLE = True
except ImportError:
    MOTO_AVAILABLE = False
    mock_aws = None


def setup_s3_mocking():
    """
    Set up S3 mocking using moto if S3 storage is configured.
    This prevents actual AWS calls and credential errors during testing.
    """
    if not MOTO_AVAILABLE:
        return None
    
    try:
        from docex.config.docex_config import DocEXConfig
        
        config = DocEXConfig()
        storage_config = config.get('storage', {})
        storage_type = storage_config.get('type', 'filesystem')
        
        # Check if S3 is configured (either as default or in storage config)
        if storage_type == 's3' or 's3' in storage_config:
            s3_config = storage_config.get('s3', {})
            bucket_name = s3_config.get('bucket')
            region = s3_config.get('region', 'us-east-1')
            
            if bucket_name:
                print(f"🔧 Setting up S3 mocking for bucket: {bucket_name} (region: {region})")
                mock = mock_aws()
                mock.start()
                
                # Create the test bucket
                try:
                    s3_client = boto3.client('s3', region_name=region)
                    # For us-east-1, don't specify LocationConstraint
                    if region == 'us-east-1':
                        s3_client.create_bucket(Bucket=bucket_name)
                    else:
                        s3_client.create_bucket(
                            Bucket=bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': region}
                        )
                    print(f"✅ S3 mock bucket created: {bucket_name}")
                except Exception as e:
                    # Bucket might already exist in mock
                    error_msg = str(e).lower()
                    if 'already exists' in error_msg or 'bucketalreadyownedbyyou' in error_msg:
                        print(f"ℹ️  S3 mock bucket already exists: {bucket_name}")
                    else:
                        print(f"⚠️  S3 mock bucket setup warning: {e}")
                
                return mock
        return None
    except Exception as e:
        print(f"⚠️  Failed to setup S3 mocking: {e}")
        return None


def teardown_s3_mocking(mock):
    """Stop S3 mocking if it was started"""
    if mock:
        try:
            mock.stop()
            print("✅ S3 mocking stopped")
        except Exception as e:
            print(f"⚠️  Error stopping S3 mocking: {e}")


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def test_basket_listing_with_metadata(docex: DocEX, verbose: bool = False):
    """Test list_baskets_with_metadata() with document_count"""
    print_section("TEST 1: Basket Listing with Metadata (including document_count)")
    
    try:
        # Test 1.1: Get baskets with document counts
        print("1.1: Getting baskets with document counts...")
        baskets_metadata = docex.list_baskets_with_metadata(
            columns=['id', 'name', 'status', 'document_count', 'created_at'],
            filters={'status': 'active'},
            order_by='document_count',
            order_desc=True,
            limit=10
        )
        
        print(f"✅ Retrieved {len(baskets_metadata)} baskets")
        if verbose:
            print("\nBaskets with document counts:")
            for basket in baskets_metadata:
                print(f"  - {basket['name']} (ID: {basket['id'][:20]}...): {basket['document_count']} documents")
        else:
            if baskets_metadata:
                print(f"  Example: {baskets_metadata[0]['name']} has {baskets_metadata[0]['document_count']} documents")
        
        # Test 1.2: Get lightweight basket list (IDs and names only)
        print("\n1.2: Getting lightweight basket list (IDs and names only)...")
        baskets_lightweight = docex.list_baskets_with_metadata(
            columns=['id', 'name'],
            order_by='name',
            order_desc=False
        )
        
        print(f"✅ Retrieved {len(baskets_lightweight)} baskets (lightweight)")
        if verbose and baskets_lightweight:
            print("  First 5 baskets:")
            for basket in baskets_lightweight[:5]:
                print(f"    - {basket['name']} (ID: {basket['id']})")
        
        # Test 1.3: Lazy instantiation pattern
        print("\n1.3: Testing lazy instantiation pattern...")
        if baskets_metadata:
            # Get ID from metadata (no object instantiation)
            selected_basket_id = baskets_metadata[0]['id']
            selected_basket_name = baskets_metadata[0]['name']
            
            print(f"  Selected basket from metadata: {selected_basket_name} (ID: {selected_basket_id[:20]}...)")
            
            # NOW instantiate full object only when needed
            basket = docex.get_basket(basket_id=selected_basket_id)
            if basket:
                print(f"  ✅ Successfully instantiated full basket object")
                print(f"  Basket name: {basket.name}")
                print(f"  Basket ID: {basket.id}")
            else:
                print(f"  ❌ Failed to get basket")
        else:
            print("  ⚠️  No baskets found to test lazy instantiation")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_document_listing_with_metadata(docex: DocEX, verbose: bool = False):
    """Test list_documents_with_metadata() and lazy instantiation"""
    print_section("TEST 2: Document Listing with Metadata (lazy instantiation)")
    
    try:
        # Find a basket with documents for meaningful testing
        baskets_with_docs = docex.list_baskets_with_metadata(
            columns=['id', 'name', 'document_count'],
            filters={'status': 'active'},
            order_by='document_count',
            order_desc=True,
            limit=10
        )
        
        # Find a basket that has documents
        basket = None
        for basket_info in baskets_with_docs:
            if basket_info.get('document_count', 0) > 0:
                basket_id = basket_info['id']
                basket = docex.get_basket(basket_id=basket_id)
                print(f"Using basket: {basket.name} (ID: {basket.id[:20]}...) with {basket_info['document_count']} documents")
                break
        
        # If no baskets with documents, create a test basket with documents
        if not basket:
            print("⚠️  No baskets with documents found. Creating a test basket with documents...")
            import tempfile
            basket = docex.create_basket('test_performance_basket', 'Test basket for performance testing')
            
            # Create a few test documents
            for i in range(3):
                test_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
                test_file.write(f"Test document {i} content for performance testing\n")
                test_file.close()
                try:
                    basket.add(test_file.name, document_type='test')
                finally:
                    Path(test_file.name).unlink()
            
            print(f"✅ Created test basket with {len(basket.list_documents())} documents")
        
        # Test 2.1: Get documents with metadata
        print("\n2.1: Getting documents with metadata...")
        documents_metadata = basket.list_documents_with_metadata(
            columns=['id', 'name', 'status', 'document_type', 'created_at'],
            limit=10
        )
        
        print(f"✅ Retrieved {len(documents_metadata)} documents (lightweight)")
        if verbose and documents_metadata:
            print("\nDocuments:")
            for doc in documents_metadata[:5]:
                print(f"  - {doc['name']} ({doc['status']}) - ID: {doc['id'][:20]}...")
        elif documents_metadata:
            print(f"  Example: {documents_metadata[0]['name']} ({documents_metadata[0]['status']})")
        
        # Test 2.2: Lazy instantiation pattern for documents
        print("\n2.2: Testing lazy instantiation pattern for documents...")
        if documents_metadata:
            # Get IDs from metadata (no object instantiation)
            selected_doc_ids = [doc['id'] for doc in documents_metadata[:3]]
            print(f"  Selected {len(selected_doc_ids)} document IDs from metadata")
            
            # NOW instantiate full objects only for selected documents
            instantiated_docs = []
            for doc_id in selected_doc_ids:
                doc = basket.get_document(doc_id)
                if doc:
                    instantiated_docs.append(doc)
                    if verbose:
                        print(f"    ✅ Instantiated: {doc.name} (ID: {doc.id[:20]}...)")
            
            print(f"  ✅ Successfully instantiated {len(instantiated_docs)} document objects")
            
            # Test accessing document content (only for instantiated objects)
            if instantiated_docs and verbose:
                print("\n  Testing document content access...")
                for doc in instantiated_docs[:1]:  # Just test first one
                    try:
                        content = doc.get_content(mode='text')
                        print(f"    ✅ Retrieved content from {doc.name} ({len(content)} chars)")
                    except Exception as e:
                        print(f"    ⚠️  Could not retrieve content: {e}")
        else:
            print("  ⚠️  No documents found to test lazy instantiation")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_performance_comparison(docex: DocEX, verbose: bool = False):
    """Compare performance between full objects and metadata methods"""
    print_section("TEST 3: Performance Comparison")
    
    try:
        # Test 3.1: Basket listing performance
        print("3.1: Comparing basket listing methods...")
        
        # Method 1: Full objects
        start_time = time.time()
        baskets_full = docex.list_baskets(limit=100)
        time_full = (time.time() - start_time) * 1000  # Convert to ms
        
        # Method 2: Metadata only
        start_time = time.time()
        baskets_metadata = docex.list_baskets_with_metadata(
            columns=['id', 'name', 'status'],
            limit=100
        )
        time_metadata = (time.time() - start_time) * 1000  # Convert to ms
        
        print(f"  Full objects: {len(baskets_full)} baskets in {time_full:.2f}ms")
        print(f"  Metadata only: {len(baskets_metadata)} baskets in {time_metadata:.2f}ms")
        if time_full > 0:
            speedup = time_full / time_metadata if time_metadata > 0 else float('inf')
            print(f"  ⚡ Speedup: {speedup:.2f}x faster with metadata method")
        
        # Test 3.2: Document listing performance
        print("\n3.2: Comparing document listing methods...")
        
        # Find a basket with documents for meaningful comparison
        baskets_with_docs = docex.list_baskets_with_metadata(
            columns=['id', 'name', 'document_count'],
            filters={'status': 'active'},
            order_by='document_count',
            order_desc=True,
            limit=10
        )
        
        # Find a basket that has documents
        basket_with_docs = None
        for basket_info in baskets_with_docs:
            if basket_info.get('document_count', 0) > 0:
                basket_id = basket_info['id']
                basket_with_docs = docex.get_basket(basket_id=basket_id)
                print(f"  Using basket '{basket_info['name']}' with {basket_info['document_count']} documents")
                break
        
        if not basket_with_docs:
            # No baskets with documents - create a test basket with documents
            print("  ⚠️  No baskets with documents found. Creating test basket with documents...")
            import tempfile
            test_basket = docex.create_basket('test_perf_comparison', 'Test basket for performance comparison')
            
            # Create a few test documents
            for i in range(5):
                test_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
                test_file.write(f"Test document {i} content for performance comparison\n")
                test_file.close()
                try:
                    test_basket.add(test_file.name, document_type='test')
                finally:
                    Path(test_file.name).unlink()
            
            basket_with_docs = test_basket
            print(f"  ✅ Created test basket with {len(basket_with_docs.list_documents())} documents")
        
        basket = basket_with_docs
        
        # Method 1: Full objects
        start_time = time.time()
        docs_full = basket.list_documents(limit=100)
        time_full = (time.time() - start_time) * 1000
        
        # Method 2: Metadata only
        start_time = time.time()
        docs_metadata = basket.list_documents_with_metadata(
            columns=['id', 'name', 'status'],
            limit=100
        )
        time_metadata = (time.time() - start_time) * 1000
        
        print(f"  Full objects: {len(docs_full)} documents in {time_full:.2f}ms")
        print(f"  Metadata only: {len(docs_metadata)} documents in {time_metadata:.2f}ms")
        if time_full > 0:
            speedup = time_full / time_metadata if time_metadata > 0 else float('inf')
            print(f"  ⚡ Speedup: {speedup:.2f}x faster with metadata method")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_document_count_feature(docex: DocEX, verbose: bool = False):
    """Test document_count feature in list_baskets_with_metadata()"""
    print_section("TEST 4: Document Count Feature")
    
    try:
        # Test 4.1: Get baskets with document counts
        print("4.1: Getting baskets sorted by document count...")
        baskets_with_counts = docex.list_baskets_with_metadata(
            columns=['id', 'name', 'document_count'],
            order_by='document_count',
            order_desc=True,
            limit=10
        )
        
        print(f"✅ Retrieved {len(baskets_with_counts)} baskets with document counts")
        if baskets_with_counts:
            print("\nBaskets sorted by document count (descending):")
            for i, basket in enumerate(baskets_with_counts, 1):
                print(f"  {i}. {basket['name']}: {basket['document_count']} documents")
        
        # Test 4.2: Filter baskets with document counts
        print("\n4.2: Filtering baskets with document counts...")
        baskets_filtered = docex.list_baskets_with_metadata(
            columns=['id', 'name', 'status', 'document_count'],
            filters={'status': 'active'},
            order_by='document_count',
            order_desc=False,  # Ascending
            limit=5
        )
        
        print(f"✅ Retrieved {len(baskets_filtered)} active baskets (sorted by count ascending)")
        if baskets_filtered:
            print("  Baskets with fewest documents first:")
            for basket in baskets_filtered:
                print(f"    - {basket['name']}: {basket['document_count']} documents")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description='Test DocEX 2.8.3 performance improvements')
    parser.add_argument('--tenant-id', type=str, help='Tenant ID for multi-tenant mode')
    parser.add_argument('--user-id', type=str, default='test_user', help='User ID (default: test_user)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--skip-setup', action='store_true', help='Skip DocEX setup (assume already initialized)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("DocEX 2.8.3 Performance Improvements Test")
    print("=" * 80)
    
    # Initialize DocEX
    try:
        # Create UserContext if tenant_id provided
        user_context = None
        if args.tenant_id:
            user_context = UserContext(
                user_id=args.user_id,
                tenant_id=args.tenant_id
            )
            print(f"✅ Using multi-tenant mode: tenant_id={args.tenant_id}, user_id={args.user_id}")
        else:
            print("ℹ️  Using single-tenant mode")
        
        # Create DocEX instance (will auto-load config if available)
        # DocEX.__init__ will call is_initialized() and load config automatically
        if not args.skip_setup:
            # Check if config exists
            from pathlib import Path
            config_path = Path.home() / '.docex' / 'config.yaml'
            if config_path.exists():
                print(f"✅ Config file found at {config_path}")
            else:
                print(f"⚠️  Config file not found at {config_path}")
                print("⚠️  Please run 'docex init' first or use --skip-setup")
                return 1
        
        print("🔧 Creating DocEX instance (will auto-load config if available)...")
        
        # Setup S3 mocking if S3 is configured
        s3_mock = setup_s3_mocking()
        
        try:
            docex = DocEX(user_context=user_context)
            print("✅ DocEX instance created successfully\n")
            
            # Setup: Create test basket with 100 documents for performance testing
            print("🔧 Setting up test data: Creating 'invoices' basket with 100 documents...")
            try:
                # Try to get existing invoices basket
                invoices_basket = docex.get_basket(basket_name='invoices')
                if invoices_basket:
                    print(f"  Found existing 'invoices' basket with {len(invoices_basket.list_documents())} documents")
                    # Check if we need to add more documents
                    current_count = len(invoices_basket.list_documents())
                    if current_count < 100:
                        print(f"  Adding {100 - current_count} more documents to reach 100...")
                        for i in range(current_count, 100):
                            test_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
                            test_file.write(f"Invoice document {i} content for performance testing\n")
                            test_file.close()
                            try:
                                invoices_basket.add(test_file.name, document_type='invoice', metadata={'invoice_number': f'INV-{i:03d}'})
                            finally:
                                Path(test_file.name).unlink()
                        print(f"  ✅ 'invoices' basket now has {len(invoices_basket.list_documents())} documents")
                    else:
                        print(f"  ✅ 'invoices' basket already has {current_count} documents (>= 100)")
                else:
                    # Create new invoices basket
                    print("  Creating new 'invoices' basket...")
                    invoices_basket = docex.create_basket('invoices', 'Invoices basket for performance testing')
                    
                    # Add 100 test documents
                    for i in range(100):
                        test_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
                        test_file.write(f"Invoice document {i} content for performance testing\n")
                        test_file.close()
                        try:
                            invoices_basket.add(test_file.name, document_type='invoice', metadata={'invoice_number': f'INV-{i:03d}'})
                        finally:
                            Path(test_file.name).unlink()
                    
                    print(f"  ✅ Created 'invoices' basket with {len(invoices_basket.list_documents())} documents")
            except Exception as e:
                print(f"  ⚠️  Could not setup test data: {e}")
                print("  Continuing with existing data...")
            
            print()  # Empty line for readability
            
            # Run tests
            results = []
            
            results.append(("Basket Listing with Metadata", test_basket_listing_with_metadata(docex, args.verbose)))
            results.append(("Document Listing with Metadata", test_document_listing_with_metadata(docex, args.verbose)))
            results.append(("Performance Comparison", test_performance_comparison(docex, args.verbose)))
            results.append(("Document Count Feature", test_document_count_feature(docex, args.verbose)))
            
            # Summary
            print_section("Test Summary")
            passed = sum(1 for _, result in results if result)
            total = len(results)
            
            for test_name, result in results:
                status = "✅ PASSED" if result else "❌ FAILED"
                print(f"  {status}: {test_name}")
            
            print(f"\n{'=' * 80}")
            print(f"Total: {passed}/{total} tests passed")
            print(f"{'=' * 80}\n")
            
            return 0 if passed == total else 1
            
        finally:
            # Always teardown S3 mocking
            teardown_s3_mocking(s3_mock)
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

