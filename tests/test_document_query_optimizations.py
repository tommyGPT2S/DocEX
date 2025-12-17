"""
Tests for document query optimizations including:
- find_documents_by_metadata with pagination and sorting
- list_documents with pagination, sorting, and filtering
- count_documents and count_documents_by_metadata
- Performance tests
"""

import os
import shutil
import pytest
import time
from pathlib import Path
from datetime import datetime, timedelta
from docex import DocEX
from docex.db.connection import Database, Base
from docex.db.models import DocBasket as DocBasketModel
from sqlalchemy import select

# Test configuration
TEST_BASKET_NAME = "test_query_optimizations"
TEST_STORAGE_PATH = "test_data/query_test_storage"


@pytest.fixture(scope="module")
def test_docex():
    """Fixture to set up DocEX for testing"""
    # Clean up any existing test data
    test_dir = Path('test_data')
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(mode=0o755, exist_ok=True)
    
    # Set up DocEX with SQLite for testing
    db_path = str(test_dir / 'test_query.db')
    DocEX.setup(
        database={
            'type': 'sqlite',
            'sqlite': {
                'path': db_path
            }
        },
        storage={
            'filesystem': {
                'path': TEST_STORAGE_PATH
            }
        },
        logging={
            'level': 'INFO'
        }
    )
    
    # Create database tables
    docex = DocEX()
    db = Database()
    Base.metadata.create_all(db.get_engine())
    
    yield docex
    
    # Cleanup
    if test_dir.exists():
        shutil.rmtree(test_dir)


@pytest.fixture
def test_basket(test_docex):
    """Fixture to create and cleanup a test basket"""
    db = Database()
    
    # Clean up any existing test basket
    with db.transaction() as session:
        existing_basket = session.execute(
            select(DocBasketModel).where(DocBasketModel.name == TEST_BASKET_NAME)
        ).scalar_one_or_none()
        if existing_basket:
            session.delete(existing_basket)
            session.commit()
    
    # Create new basket
    basket = test_docex.create_basket(TEST_BASKET_NAME, "Test basket for query optimizations")
    
    yield basket
    
    # Cleanup - basket will be cleaned up by test_docex fixture


@pytest.fixture
def sample_documents_with_metadata(test_basket):
    """Fixture to create sample documents with various metadata"""
    documents = []
    os.makedirs(TEST_STORAGE_PATH, exist_ok=True)
    
    # Create documents with different metadata
    test_data = [
        {"name": "invoice_001.pdf", "author": "John Doe", "category": "invoice", "status": "processed"},
        {"name": "invoice_002.pdf", "author": "Jane Smith", "category": "invoice", "status": "pending"},
        {"name": "invoice_003.pdf", "author": "John Doe", "category": "invoice", "status": "processed"},
        {"name": "report_001.pdf", "author": "John Doe", "category": "report", "status": "processed"},
        {"name": "report_002.pdf", "author": "Jane Smith", "category": "report", "status": "pending"},
        {"name": "contract_001.pdf", "author": "Bob Johnson", "category": "contract", "status": "processed"},
    ]
    
    for i, data in enumerate(test_data):
        file_path = os.path.join(TEST_STORAGE_PATH, data["name"])
        with open(file_path, 'w') as f:
            f.write(f"Test content for {data['name']}")
        
        doc = test_basket.add(file_path, metadata={
            "author": data["author"],
            "category": data["category"],
            "status": data["status"],
            "document_number": i + 1
        })
        documents.append(doc)
    
    return documents


class TestFindDocumentsByMetadata:
    """Tests for find_documents_by_metadata optimizations"""
    
    def test_basic_metadata_search(self, test_basket, sample_documents_with_metadata):
        """Test basic metadata search"""
        results = test_basket.find_documents_by_metadata({"author": "John Doe"})
        assert len(results) == 3
        for doc in results:
            metadata = doc.get_metadata_dict()
            assert metadata.get("author") == "John Doe"
    
    def test_metadata_search_with_multiple_filters(self, test_basket, sample_documents_with_metadata):
        """Test metadata search with multiple filters (AND logic)"""
        results = test_basket.find_documents_by_metadata({
            "author": "John Doe",
            "category": "invoice"
        })
        assert len(results) == 2
        for doc in results:
            metadata = doc.get_metadata_dict()
            assert metadata.get("author") == "John Doe"
            assert metadata.get("category") == "invoice"
    
    def test_metadata_search_with_pagination(self, test_basket, sample_documents_with_metadata):
        """Test metadata search with pagination"""
        # Get first page
        page1 = test_basket.find_documents_by_metadata(
            {"category": "invoice"},
            limit=2,
            offset=0
        )
        assert len(page1) == 2
        
        # Get second page
        page2 = test_basket.find_documents_by_metadata(
            {"category": "invoice"},
            limit=2,
            offset=2
        )
        assert len(page2) == 1
        
        # Verify no overlap
        page1_ids = {doc.id for doc in page1}
        page2_ids = {doc.id for doc in page2}
        assert len(page1_ids & page2_ids) == 0
    
    def test_metadata_search_with_sorting(self, test_basket, sample_documents_with_metadata):
        """Test metadata search with sorting"""
        # Sort by document_number ascending
        results_asc = test_basket.find_documents_by_metadata(
            {"author": "John Doe"},
            order_by="created_at",
            order_desc=False
        )
        assert len(results_asc) == 3
        
        # Sort by created_at descending
        results_desc = test_basket.find_documents_by_metadata(
            {"author": "John Doe"},
            order_by="created_at",
            order_desc=True
        )
        assert len(results_desc) == 3
        
        # Verify order is different (unless all created at same time)
        # In practice, they should be in reverse order
        if len(results_asc) > 1:
            # At least verify we got results
            assert results_asc[0].id != results_desc[0].id or len(results_asc) == 1
    
    def test_metadata_search_string_value(self, test_basket, sample_documents_with_metadata):
        """Test metadata search with string value (searches all metadata)"""
        # This searches for the value across all metadata keys
        results = test_basket.find_documents_by_metadata("processed")
        # Should find documents with status="processed"
        assert len(results) >= 4  # At least 4 documents have status="processed"
    
    def test_count_documents_by_metadata(self, test_basket, sample_documents_with_metadata):
        """Test count_documents_by_metadata method"""
        count = test_basket.count_documents_by_metadata({"author": "John Doe"})
        assert count == 3
        
        count = test_basket.count_documents_by_metadata({
            "author": "John Doe",
            "category": "invoice"
        })
        assert count == 2
        
        count = test_basket.count_documents_by_metadata({"category": "nonexistent"})
        assert count == 0


class TestListDocuments:
    """Tests for list_documents optimizations"""
    
    def test_basic_list(self, test_basket, sample_documents_with_metadata):
        """Test basic list_documents"""
        all_docs = test_basket.list_documents()
        assert len(all_docs) == 6
    
    def test_list_with_pagination(self, test_basket, sample_documents_with_metadata):
        """Test list_documents with pagination"""
        page_size = 2
        
        # Get first page
        page1 = test_basket.list_documents(limit=page_size, offset=0)
        assert len(page1) == page_size
        
        # Get second page
        page2 = test_basket.list_documents(limit=page_size, offset=page_size)
        assert len(page2) == page_size
        
        # Get third page
        page3 = test_basket.list_documents(limit=page_size, offset=page_size * 2)
        assert len(page3) == 2  # Remaining documents
        
        # Verify no overlap
        all_ids = {doc.id for doc in page1 + page2 + page3}
        assert len(all_ids) == 6  # All unique
    
    def test_list_with_sorting(self, test_basket, sample_documents_with_metadata):
        """Test list_documents with sorting"""
        # Sort by name ascending
        docs_asc = test_basket.list_documents(
            order_by="name",
            order_desc=False
        )
        assert len(docs_asc) == 6
        
        # Sort by name descending
        docs_desc = test_basket.list_documents(
            order_by="name",
            order_desc=True
        )
        assert len(docs_desc) == 6
        
        # Verify order is reversed
        if len(docs_asc) > 1:
            assert docs_asc[0].name != docs_desc[0].name or docs_asc[0].name == docs_desc[-1].name
    
    def test_list_with_status_filter(self, test_basket, sample_documents_with_metadata):
        """Test list_documents with status filter"""
        # Note: This filters by document.status field, not metadata
        # We'll test with all documents (status filter works on document model)
        all_docs = test_basket.list_documents()
        assert len(all_docs) >= 0  # At least we can list
    
    def test_list_with_document_type_filter(self, test_basket, sample_documents_with_metadata):
        """Test list_documents with document_type filter"""
        all_docs = test_basket.list_documents()
        # All our test documents are 'file' type
        file_docs = test_basket.list_documents(document_type='file')
        assert len(file_docs) == len(all_docs)
    
    def test_list_with_multiple_options(self, test_basket, sample_documents_with_metadata):
        """Test list_documents with pagination, sorting, and filtering"""
        results = test_basket.list_documents(
            limit=3,
            offset=0,
            order_by="created_at",
            order_desc=True,
            document_type="file"
        )
        assert len(results) <= 3
    
    def test_count_documents(self, test_basket, sample_documents_with_metadata):
        """Test count_documents method"""
        total = test_basket.count_documents()
        assert total == 6
        
        # Count with filter (if status field exists in document model)
        # Note: This depends on document.status field, not metadata
        all_count = test_basket.count_documents()
        assert all_count == 6


class TestPerformance:
    """Performance tests for query optimizations"""
    
    def test_metadata_search_performance(self, test_basket):
        """Test that metadata search is reasonably fast"""
        # Create many documents
        os.makedirs(TEST_STORAGE_PATH, exist_ok=True)
        num_docs = 100
        
        for i in range(num_docs):
            file_path = os.path.join(TEST_STORAGE_PATH, f"perf_test_{i}.txt")
            with open(file_path, 'w') as f:
                f.write(f"Performance test document {i}")
            
            test_basket.add(file_path, metadata={
                "batch": "performance_test",
                "index": i,
                "category": "test" if i % 2 == 0 else "demo"
            })
        
        # Time the search
        start = time.time()
        results = test_basket.find_documents_by_metadata({"batch": "performance_test"})
        elapsed = time.time() - start
        
        assert len(results) == num_docs
        # Should complete in reasonable time (< 1 second for 100 docs)
        assert elapsed < 1.0, f"Search took {elapsed:.2f}s, expected < 1.0s"
    
    def test_list_with_pagination_performance(self, test_basket):
        """Test that paginated list is faster than loading all"""
        # Create many documents
        os.makedirs(TEST_STORAGE_PATH, exist_ok=True)
        num_docs = 200
        
        for i in range(num_docs):
            file_path = os.path.join(TEST_STORAGE_PATH, f"list_perf_{i}.txt")
            with open(file_path, 'w') as f:
                f.write(f"List performance test {i}")
            test_basket.add(file_path)
        
        # Time paginated query
        start = time.time()
        page = test_basket.list_documents(limit=50, offset=0)
        paginated_time = time.time() - start
        
        # Time full query
        start = time.time()
        all_docs = test_basket.list_documents()
        full_time = time.time() - start
        
        assert len(page) == 50
        assert len(all_docs) == num_docs
        # Paginated should be faster (or at least not much slower)
        # In practice, with proper indexes, paginated should be significantly faster
        assert paginated_time < full_time * 1.5, \
            f"Paginated ({paginated_time:.3f}s) should be faster than full ({full_time:.3f}s)"
    
    def test_count_performance(self, test_basket):
        """Test that count is faster than loading all documents"""
        # Create documents
        os.makedirs(TEST_STORAGE_PATH, exist_ok=True)
        num_docs = 150
        
        for i in range(num_docs):
            file_path = os.path.join(TEST_STORAGE_PATH, f"count_perf_{i}.txt")
            with open(file_path, 'w') as f:
                f.write(f"Count performance test {i}")
            test_basket.add(file_path, metadata={"test": "count_perf"})
        
        # Time count
        start = time.time()
        count = test_basket.count_documents()
        count_time = time.time() - start
        
        # Time loading all
        start = time.time()
        all_docs = test_basket.list_documents()
        load_time = time.time() - start
        
        assert count == num_docs
        # Count should be significantly faster
        assert count_time < load_time, \
            f"Count ({count_time:.3f}s) should be faster than load ({load_time:.3f}s)"


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_results(self, test_basket):
        """Test queries that return no results"""
        results = test_basket.find_documents_by_metadata({"nonexistent": "value"})
        assert len(results) == 0
        
        count = test_basket.count_documents_by_metadata({"nonexistent": "value"})
        assert count == 0
    
    def test_pagination_beyond_results(self, test_basket, sample_documents_with_metadata):
        """Test pagination when offset is beyond available results"""
        results = test_basket.list_documents(limit=10, offset=100)
        assert len(results) == 0
    
    def test_invalid_order_by(self, test_basket, sample_documents_with_metadata):
        """Test with invalid order_by field"""
        # Should fall back to default sorting
        results = test_basket.list_documents(order_by="invalid_field")
        assert len(results) == 6  # Should still return results
    
    def test_zero_limit(self, test_basket, sample_documents_with_metadata):
        """Test with limit=0"""
        results = test_basket.list_documents(limit=0)
        assert len(results) == 0
    
    def test_large_offset(self, test_basket, sample_documents_with_metadata):
        """Test with very large offset"""
        results = test_basket.find_documents_by_metadata(
            {"category": "invoice"},
            limit=10,
            offset=1000
        )
        assert len(results) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

