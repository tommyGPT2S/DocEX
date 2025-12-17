"""
Performance benchmark tests for document query optimizations.
Run these tests to verify performance improvements.

Usage:
    pytest tests/test_query_performance_benchmark.py -v -s
    pytest tests/test_query_performance_benchmark.py::test_large_dataset_benchmark -v -s
"""

import os
import shutil
import pytest
import time
from pathlib import Path
from docex import DocEX
from docex.db.connection import Database, Base

TEST_BASKET_NAME = "performance_benchmark"
TEST_STORAGE_PATH = "test_data/benchmark_storage"


@pytest.fixture(scope="module")
def benchmark_docex():
    """Set up DocEX for benchmarking"""
    test_dir = Path('test_data')
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(mode=0o755, exist_ok=True)
    
    db_path = str(test_dir / 'benchmark.db')
    DocEX.setup(
        database={
            'type': 'sqlite',
            'sqlite': {'path': db_path}
        },
        storage={
            'filesystem': {'path': TEST_STORAGE_PATH}
        }
    )
    
    docex = DocEX()
    db = Database()
    Base.metadata.create_all(db.get_engine())
    
    yield docex
    
    if test_dir.exists():
        shutil.rmtree(test_dir)


@pytest.fixture
def large_basket(benchmark_docex):
    """Create a basket with many documents for benchmarking"""
    basket = benchmark_docex.create_basket(
        TEST_BASKET_NAME,
        "Basket for performance benchmarking"
    )
    
    # Create 1000 documents with metadata
    os.makedirs(TEST_STORAGE_PATH, exist_ok=True)
    print(f"\nCreating 1000 test documents...")
    
    start = time.time()
    for i in range(1000):
        file_path = os.path.join(TEST_STORAGE_PATH, f"doc_{i:04d}.txt")
        with open(file_path, 'w') as f:
            f.write(f"Document {i} content")
        
        basket.add(file_path, metadata={
            "batch": "benchmark",
            "index": i,
            "category": "test" if i % 3 == 0 else ("demo" if i % 3 == 1 else "sample"),
            "status": "processed" if i % 2 == 0 else "pending",
            "author": f"Author_{i % 10}"
        })
        
        if (i + 1) % 100 == 0:
            print(f"  Created {i + 1} documents...")
    
    elapsed = time.time() - start
    print(f"Created 1000 documents in {elapsed:.2f}s ({elapsed/1000*1000:.3f}ms per document)\n")
    
    yield basket


def test_metadata_search_benchmark(large_basket):
    """Benchmark metadata search performance"""
    print("\n=== Metadata Search Benchmark ===")
    
    # Test 1: Single filter
    start = time.time()
    results = large_basket.find_documents_by_metadata({"category": "test"})
    elapsed = time.time() - start
    print(f"Single filter (category='test'): {len(results)} results in {elapsed*1000:.2f}ms")
    assert elapsed < 1.0, "Search should complete in < 1 second"
    
    # Test 2: Multiple filters (AND)
    start = time.time()
    results = large_basket.find_documents_by_metadata({
        "category": "test",
        "status": "processed"
    })
    elapsed = time.time() - start
    print(f"Multiple filters (AND): {len(results)} results in {elapsed*1000:.2f}ms")
    assert elapsed < 1.0
    
    # Test 3: With pagination
    start = time.time()
    results = large_basket.find_documents_by_metadata(
        {"category": "test"},
        limit=50,
        offset=0
    )
    elapsed = time.time() - start
    print(f"With pagination (limit=50): {len(results)} results in {elapsed*1000:.2f}ms")
    assert elapsed < 0.5, "Paginated search should be faster"
    
    # Test 4: With sorting
    start = time.time()
    results = large_basket.find_documents_by_metadata(
        {"category": "test"},
        order_by="created_at",
        order_desc=True,
        limit=50
    )
    elapsed = time.time() - start
    print(f"With sorting and pagination: {len(results)} results in {elapsed*1000:.2f}ms")
    assert elapsed < 0.5


def test_list_documents_benchmark(large_basket):
    """Benchmark list_documents performance"""
    print("\n=== List Documents Benchmark ===")
    
    # Test 1: Full list (no pagination)
    start = time.time()
    all_docs = large_basket.list_documents()
    full_time = time.time() - start
    print(f"Full list (no pagination): {len(all_docs)} documents in {full_time*1000:.2f}ms")
    
    # Test 2: Paginated list
    start = time.time()
    page = large_basket.list_documents(limit=50, offset=0)
    paginated_time = time.time() - start
    print(f"Paginated list (limit=50): {len(page)} documents in {paginated_time*1000:.2f}ms")
    
    # Paginated should be significantly faster
    speedup = full_time / paginated_time if paginated_time > 0 else float('inf')
    print(f"Speedup: {speedup:.2f}x faster with pagination")
    assert paginated_time < full_time, "Pagination should be faster"
    
    # Test 3: With sorting
    start = time.time()
    sorted_docs = large_basket.list_documents(
        limit=50,
        order_by="created_at",
        order_desc=True
    )
    sorted_time = time.time() - start
    print(f"With sorting (limit=50): {len(sorted_docs)} documents in {sorted_time*1000:.2f}ms")
    assert sorted_time < 0.5


def test_count_benchmark(large_basket):
    """Benchmark count operations"""
    print("\n=== Count Operations Benchmark ===")
    
    # Test 1: Count all documents
    start = time.time()
    total = large_basket.count_documents()
    count_time = time.time() - start
    print(f"count_documents(): {total} documents in {count_time*1000:.2f}ms")
    assert total == 1000
    assert count_time < 0.1, "Count should be very fast"
    
    # Test 2: Count by metadata
    start = time.time()
    metadata_count = large_basket.count_documents_by_metadata({"category": "test"})
    metadata_count_time = time.time() - start
    print(f"count_documents_by_metadata(): {metadata_count} documents in {metadata_count_time*1000:.2f}ms")
    assert metadata_count_time < 0.5
    
    # Test 3: Compare count vs loading all
    start = time.time()
    all_docs = large_basket.list_documents()
    load_time = time.time() - start
    
    speedup = load_time / count_time if count_time > 0 else float('inf')
    print(f"Count is {speedup:.2f}x faster than loading all documents")
    assert count_time < load_time, "Count should be faster than loading"


def test_pagination_efficiency(large_basket):
    """Test that pagination is efficient across multiple pages"""
    print("\n=== Pagination Efficiency Test ===")
    
    page_size = 50
    total_pages = 20  # 1000 / 50
    
    times = []
    for page in range(total_pages):
        start = time.time()
        results = large_basket.list_documents(
            limit=page_size,
            offset=page * page_size
        )
        elapsed = time.time() - start
        times.append(elapsed)
        assert len(results) == page_size or (page == total_pages - 1 and len(results) <= page_size)
    
    avg_time = sum(times) / len(times)
    max_time = max(times)
    min_time = min(times)
    
    print(f"Average page load time: {avg_time*1000:.2f}ms")
    print(f"Min: {min_time*1000:.2f}ms, Max: {max_time*1000:.2f}ms")
    
    # All pages should load in reasonable time
    assert max_time < 0.5, f"Slowest page took {max_time*1000:.2f}ms"
    assert avg_time < 0.2, f"Average page time {avg_time*1000:.2f}ms is too slow"


def test_comparison_no_optimization(large_basket):
    """Compare optimized vs non-optimized queries"""
    print("\n=== Optimization Comparison ===")
    
    # Simulate "old way" - load all then filter in Python
    start = time.time()
    all_docs = large_basket.list_documents()
    # Filter in Python (simulating old behavior)
    filtered = [d for d in all_docs if d.get_metadata_dict().get("category") == "test"]
    old_way_time = time.time() - start
    
    # New way - filter at database level
    start = time.time()
    new_filtered = large_basket.find_documents_by_metadata({"category": "test"})
    new_way_time = time.time() - start
    
    print(f"Old way (load all + Python filter): {len(filtered)} results in {old_way_time*1000:.2f}ms")
    print(f"New way (database filter): {len(new_filtered)} results in {new_way_time*1000:.2f}ms")
    
    speedup = old_way_time / new_way_time if new_way_time > 0 else float('inf')
    print(f"Speedup: {speedup:.2f}x faster with database filtering")
    
    assert len(filtered) == len(new_filtered)
    assert new_way_time < old_way_time, "Database filtering should be faster"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

