#!/usr/bin/env python3
"""
Test script for document query optimizations using docEX-Demo-PS tenant.

This script tests:
- list_documents with pagination, sorting, and filtering
- find_documents_by_metadata with pagination and sorting
- count_documents and count_documents_by_metadata
- Performance comparisons
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from docex import DocEX
from docex.context import UserContext

def create_test_documents(basket, num_documents=50):
    """Create test documents with various metadata"""
    print(f"\n📄 Creating {num_documents} test documents...")
    
    test_dir = Path('test_data/query_test_docs')
    test_dir.mkdir(parents=True, exist_ok=True)
    
    documents = []
    categories = ['invoice', 'report', 'contract', 'memo']
    authors = ['Alice', 'Bob', 'Charlie', 'Diana']
    statuses = ['processed', 'pending', 'reviewed', 'archived']
    
    for i in range(num_documents):
        # Create test file
        file_path = test_dir / f"doc_{i:03d}.txt"
        file_path.write_text(f"Test document {i} content\nCategory: {categories[i % len(categories)]}\nAuthor: {authors[i % len(authors)]}")
        
        # Add document with metadata
        doc = basket.add(
            str(file_path),
            metadata={
                'category': categories[i % len(categories)],
                'author': authors[i % len(authors)],
                'status': statuses[i % len(statuses)],
                'document_number': i + 1,
                'batch': 'test_batch'
            }
        )
        documents.append(doc)
        
        if (i + 1) % 10 == 0:
            print(f"  Created {i + 1}/{num_documents} documents...")
    
    print(f"✅ Created {len(documents)} documents")
    return documents


def test_list_documents_pagination(basket):
    """Test list_documents with pagination"""
    print("\n" + "="*60)
    print("TEST 1: list_documents with Pagination")
    print("="*60)
    
    total = basket.count_documents()
    print(f"Total documents: {total}")
    
    page_size = 10
    total_pages = (total + page_size - 1) // page_size
    
    print(f"\n📄 Testing pagination (page_size={page_size}, total_pages={total_pages})...")
    
    for page in range(1, min(total_pages + 1, 4)):  # Test first 3 pages
        offset = (page - 1) * page_size
        start = time.time()
        docs = basket.list_documents(limit=page_size, offset=offset)
        elapsed = time.time() - start
        
        print(f"  Page {page} (offset={offset}): {len(docs)} documents in {elapsed*1000:.2f}ms")
        if docs:
            print(f"    First doc: {docs[0].name} (ID: {docs[0].id[:20]}...)")
            print(f"    Last doc: {docs[-1].name} (ID: {docs[-1].id[:20]}...)")


def test_list_documents_sorting(basket):
    """Test list_documents with sorting"""
    print("\n" + "="*60)
    print("TEST 2: list_documents with Sorting")
    print("="*60)
    
    # Test sorting by name
    print("\n📄 Testing sorting by name...")
    start = time.time()
    docs_asc = basket.list_documents(order_by='name', order_desc=False, limit=10)
    elapsed_asc = time.time() - start
    
    start = time.time()
    docs_desc = basket.list_documents(order_by='name', order_desc=True, limit=10)
    elapsed_desc = time.time() - start
    
    print(f"  Ascending: {len(docs_asc)} docs in {elapsed_asc*1000:.2f}ms")
    if docs_asc:
        print(f"    First: {docs_asc[0].name}")
        print(f"    Last: {docs_asc[-1].name}")
    
    print(f"  Descending: {len(docs_desc)} docs in {elapsed_desc*1000:.2f}ms")
    if docs_desc:
        print(f"    First: {docs_desc[0].name}")
        print(f"    Last: {docs_desc[-1].name}")
    
    # Test sorting by created_at
    print("\n📄 Testing sorting by created_at...")
    start = time.time()
    docs_newest = basket.list_documents(order_by='created_at', order_desc=True, limit=5)
    elapsed = time.time() - start
    
    print(f"  Newest first: {len(docs_newest)} docs in {elapsed*1000:.2f}ms")
    if docs_newest:
        print(f"    Newest: {docs_newest[0].name} ({docs_newest[0].created_at})")


def test_list_documents_filtering(basket):
    """Test list_documents with filtering"""
    print("\n" + "="*60)
    print("TEST 3: list_documents with Filtering")
    print("="*60)
    
    # Test with document_type filter
    print("\n📄 Testing with document_type filter...")
    start = time.time()
    file_docs = basket.list_documents(document_type='file', limit=20)
    elapsed = time.time() - start
    print(f"  document_type='file': {len(file_docs)} docs in {elapsed*1000:.2f}ms")
    
    # Test with status filter (if available)
    print("\n📄 Testing with status filter...")
    start = time.time()
    active_docs = basket.list_documents(status='active', limit=20)
    elapsed = time.time() - start
    print(f"  status='active': {len(active_docs)} docs in {elapsed*1000:.2f}ms")


def test_metadata_search(basket):
    """Test find_documents_by_metadata"""
    print("\n" + "="*60)
    print("TEST 4: find_documents_by_metadata")
    print("="*60)
    
    # Test single filter
    print("\n📄 Testing single metadata filter...")
    start = time.time()
    invoice_docs = basket.find_documents_by_metadata({'category': 'invoice'})
    elapsed = time.time() - start
    print(f"  category='invoice': {len(invoice_docs)} docs in {elapsed*1000:.2f}ms")
    
    # Test multiple filters (AND logic)
    print("\n📄 Testing multiple metadata filters (AND)...")
    start = time.time()
    filtered_docs = basket.find_documents_by_metadata({
        'category': 'invoice',
        'author': 'Alice'
    })
    elapsed = time.time() - start
    print(f"  category='invoice' AND author='Alice': {len(filtered_docs)} docs in {elapsed*1000:.2f}ms")
    
    # Test with pagination
    print("\n📄 Testing metadata search with pagination...")
    start = time.time()
    page1 = basket.find_documents_by_metadata(
        {'category': 'invoice'},
        limit=5,
        offset=0
    )
    elapsed = time.time() - start
    print(f"  Page 1 (limit=5): {len(page1)} docs in {elapsed*1000:.2f}ms")
    
    start = time.time()
    page2 = basket.find_documents_by_metadata(
        {'category': 'invoice'},
        limit=5,
        offset=5
    )
    elapsed = time.time() - start
    print(f"  Page 2 (limit=5, offset=5): {len(page2)} docs in {elapsed*1000:.2f}ms")
    
    # Test with sorting
    print("\n📄 Testing metadata search with sorting...")
    start = time.time()
    sorted_docs = basket.find_documents_by_metadata(
        {'category': 'invoice'},
        limit=10,
        order_by='created_at',
        order_desc=True
    )
    elapsed = time.time() - start
    print(f"  Sorted by created_at (desc): {len(sorted_docs)} docs in {elapsed*1000:.2f}ms")


def test_count_operations(basket):
    """Test count operations"""
    print("\n" + "="*60)
    print("TEST 5: Count Operations")
    print("="*60)
    
    # Test count_documents
    print("\n📄 Testing count_documents...")
    start = time.time()
    total = basket.count_documents()
    elapsed = time.time() - start
    print(f"  Total documents: {total} (counted in {elapsed*1000:.2f}ms)")
    
    # Test count_documents_by_metadata
    print("\n📄 Testing count_documents_by_metadata...")
    start = time.time()
    invoice_count = basket.count_documents_by_metadata({'category': 'invoice'})
    elapsed = time.time() - start
    print(f"  category='invoice': {invoice_count} docs (counted in {elapsed*1000:.2f}ms)")
    
    start = time.time()
    multi_filter_count = basket.count_documents_by_metadata({
        'category': 'invoice',
        'author': 'Alice'
    })
    elapsed = time.time() - start
    print(f"  category='invoice' AND author='Alice': {multi_filter_count} docs (counted in {elapsed*1000:.2f}ms)")


def test_performance_comparison(basket):
    """Compare performance: pagination vs full load"""
    print("\n" + "="*60)
    print("TEST 6: Performance Comparison")
    print("="*60)
    
    total = basket.count_documents()
    
    # Test paginated load
    print("\n📄 Testing paginated load...")
    start = time.time()
    page = basket.list_documents(limit=20, offset=0)
    paginated_time = time.time() - start
    print(f"  Paginated (limit=20): {len(page)} docs in {paginated_time*1000:.2f}ms")
    
    # Test full load
    print("\n📄 Testing full load...")
    start = time.time()
    all_docs = basket.list_documents()
    full_time = time.time() - start
    print(f"  Full load: {len(all_docs)} docs in {full_time*1000:.2f}ms")
    
    # Calculate speedup
    if paginated_time > 0:
        speedup = full_time / paginated_time
        print(f"\n  ⚡ Pagination is {speedup:.2f}x faster for first page")
        print(f"  💾 Memory saved: {len(all_docs) - len(page)} documents not loaded")


def main():
    """Main test function"""
    print("="*60)
    print("Document Query Optimizations Test")
    print("Tenant: docEX-Demo-PS (PostgreSQL)")
    print("="*60)
    
    # Initialize DocEX with tenant context
    user_context = UserContext(
        user_id="test_user",
        tenant_id="docEX-Demo-PS"
    )
    docex = DocEX(user_context=user_context)
    
    # Get or create test basket
    basket_name = "query_test_basket"
    try:
        baskets = docex.list_baskets()
        basket = next((b for b in baskets if b.name == basket_name), None)
        if not basket:
            print(f"\n📦 Creating test basket: {basket_name}")
            basket = docex.create_basket(basket_name, "Basket for query optimization tests")
        else:
            print(f"\n📦 Using existing basket: {basket_name} (ID: {basket.id})")
    except Exception as e:
        print(f"Error getting basket: {e}")
        basket = docex.create_basket(basket_name, "Basket for query optimization tests")
    
    # Check if we need to create test documents
    total = basket.count_documents()
    print(f"\nCurrent documents in basket: {total}")
    
    # Auto-create test documents if needed
    if total < 50:
        print(f"\n📄 Creating {50 - total} test documents...")
        create_test_documents(basket, num_documents=50 - total)
        total = basket.count_documents()
    
    if total == 0:
        print("\n⚠️  No documents found. Creating test documents...")
        create_test_documents(basket, num_documents=50)
        total = basket.count_documents()
    
    print(f"\n✅ Ready to test with {total} documents")
    
    # Run all tests
    test_list_documents_pagination(basket)
    test_list_documents_sorting(basket)
    test_list_documents_filtering(basket)
    test_metadata_search(basket)
    test_count_operations(basket)
    test_performance_comparison(basket)
    
    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("="*60)
    print(f"\nTenant: docEX-Demo-PS")
    print(f"Basket: {basket.name} (ID: {basket.id})")
    print(f"Total documents: {basket.count_documents()}")


if __name__ == '__main__':
    main()

