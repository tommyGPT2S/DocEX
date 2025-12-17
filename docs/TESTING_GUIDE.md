# Testing Guide for Document Query Optimizations

This guide explains how to test the document query optimizations we've implemented.

## Quick Start

### Run All Tests

```bash
# Run all query optimization tests
pytest tests/test_document_query_optimizations.py -v

# Run performance benchmarks
pytest tests/test_query_performance_benchmark.py -v -s

# Run both with coverage
pytest tests/test_document_query_optimizations.py tests/test_query_performance_benchmark.py --cov=docex.docbasket --cov-report=html
```

### Run Specific Test Classes

```bash
# Test metadata search optimizations
pytest tests/test_document_query_optimizations.py::TestFindDocumentsByMetadata -v

# Test list documents optimizations
pytest tests/test_document_query_optimizations.py::TestListDocuments -v

# Test performance
pytest tests/test_document_query_optimizations.py::TestPerformance -v
```

### Run Specific Tests

```bash
# Test pagination
pytest tests/test_document_query_optimizations.py::TestListDocuments::test_list_with_pagination -v

# Test metadata search with sorting
pytest tests/test_document_query_optimizations.py::TestFindDocumentsByMetadata::test_metadata_search_with_sorting -v
```

## Test Files

### 1. `test_document_query_optimizations.py`

Comprehensive unit tests covering:
- ✅ Basic functionality
- ✅ Pagination
- ✅ Sorting
- ✅ Filtering
- ✅ Count methods
- ✅ Edge cases
- ✅ Basic performance checks

**Run:**
```bash
pytest tests/test_document_query_optimizations.py -v
```

### 2. `test_query_performance_benchmark.py`

Performance benchmarks with large datasets (1000 documents):
- ✅ Metadata search performance
- ✅ List documents performance
- ✅ Count operations
- ✅ Pagination efficiency
- ✅ Optimization comparisons

**Run:**
```bash
pytest tests/test_query_performance_benchmark.py -v -s
```

## Test Coverage

### find_documents_by_metadata Tests

| Test | Description |
|------|-------------|
| `test_basic_metadata_search` | Basic single-filter search |
| `test_metadata_search_with_multiple_filters` | Multiple filters with AND logic |
| `test_metadata_search_with_pagination` | Pagination support |
| `test_metadata_search_with_sorting` | Sorting support |
| `test_metadata_search_string_value` | String value search across all metadata |
| `test_count_documents_by_metadata` | Count method |

### list_documents Tests

| Test | Description |
|------|-------------|
| `test_basic_list` | Basic listing |
| `test_list_with_pagination` | Pagination support |
| `test_list_with_sorting` | Sorting by various fields |
| `test_list_with_status_filter` | Status filtering |
| `test_list_with_document_type_filter` | Document type filtering |
| `test_list_with_multiple_options` | Combined pagination, sorting, filtering |
| `test_count_documents` | Count method |

### Performance Tests

| Test | Description |
|------|-------------|
| `test_metadata_search_performance` | Metadata search with 100 documents |
| `test_list_with_pagination_performance` | Pagination vs full load |
| `test_count_performance` | Count vs loading all |

### Edge Cases

| Test | Description |
|------|-------------|
| `test_empty_results` | Queries with no results |
| `test_pagination_beyond_results` | Offset beyond available data |
| `test_invalid_order_by` | Invalid sort field handling |
| `test_zero_limit` | Limit=0 handling |
| `test_large_offset` | Very large offset handling |

## Performance Benchmarks

### Expected Performance

| Operation | Dataset Size | Expected Time | Notes |
|-----------|--------------|---------------|-------|
| Metadata search (single filter) | 1000 docs | < 100ms | With indexes |
| Metadata search (multiple filters) | 1000 docs | < 200ms | With indexes |
| List with pagination (50 docs) | 1000 docs | < 50ms | Much faster than full load |
| Count all documents | 1000 docs | < 10ms | Very fast |
| Count by metadata | 1000 docs | < 50ms | With indexes |

### Running Benchmarks

```bash
# Run all benchmarks
pytest tests/test_query_performance_benchmark.py -v -s

# Run specific benchmark
pytest tests/test_query_performance_benchmark.py::test_metadata_search_benchmark -v -s

# Run with timing details
pytest tests/test_query_performance_benchmark.py -v -s --durations=10
```

## Manual Testing

### Test Pagination

```python
from docex import DocEX

docex = DocEX()
basket = docex.get_basket('your_basket_id')

# Test pagination
page_size = 50
total = basket.count_documents()
total_pages = (total + page_size - 1) // page_size

for page in range(1, total_pages + 1):
    offset = (page - 1) * page_size
    docs = basket.list_documents(limit=page_size, offset=offset)
    print(f"Page {page}: {len(docs)} documents")
```

### Test Metadata Search

```python
# Test with pagination
results = basket.find_documents_by_metadata(
    {'category': 'invoice'},
    limit=20,
    offset=0,
    order_by='created_at',
    order_desc=True
)

# Test count
count = basket.count_documents_by_metadata({'category': 'invoice'})
print(f"Found {count} invoices")
```

### Test Sorting

```python
# Sort by name
docs = basket.list_documents(
    order_by='name',
    order_desc=False,
    limit=100
)

# Sort by creation date (newest first)
docs = basket.list_documents(
    order_by='created_at',
    order_desc=True,
    limit=100
)
```

## Verifying Indexes

### Check if Indexes Exist (PostgreSQL)

```sql
-- Connect to your database
psql -d your_database

-- List indexes on document table
\d+ document

-- List indexes on document_metadata table
\d+ document_metadata

-- Check for composite indexes
SELECT 
    indexname, 
    indexdef 
FROM pg_indexes 
WHERE tablename IN ('document', 'document_metadata')
ORDER BY tablename, indexname;
```

### Apply Indexes if Missing

```bash
# Apply migration
psql -d your_database -f docex/db/migrations/002_add_performance_indexes.sql
```

Or via Python:

```python
from docex.db.connection import Database
from sqlalchemy import text

db = Database()
with db.session() as session:
    with open('docex/db/migrations/002_add_performance_indexes.sql', 'r') as f:
        session.execute(text(f.read()))
    session.commit()
```

## Troubleshooting

### Tests Fail with "No such table"

**Solution:** Ensure database tables are created:
```python
from docex.db.connection import Database, Base
db = Database()
Base.metadata.create_all(db.get_engine())
```

### Slow Performance

**Check:**
1. Indexes are created (see above)
2. Database type (PostgreSQL is faster than SQLite for large datasets)
3. Query is using indexes (check with EXPLAIN)

### Pagination Returns Wrong Results

**Check:**
1. Offset calculation: `offset = (page - 1) * page_size`
2. Total count matches actual documents
3. No documents deleted between count and query

## Continuous Integration

Add to your CI/CD pipeline:

```yaml
# Example GitHub Actions
- name: Run Query Optimization Tests
  run: |
    pytest tests/test_document_query_optimizations.py -v --cov=docex.docbasket
    
- name: Run Performance Benchmarks
  run: |
    pytest tests/test_query_performance_benchmark.py -v -s
```

## Test Data Setup

Tests automatically create test data, but for manual testing:

```python
from docex import DocEX

docex = DocEX()
basket = docex.create_basket('test_basket')

# Create test documents
for i in range(100):
    file_path = f'test_doc_{i}.txt'
    with open(file_path, 'w') as f:
        f.write(f'Test document {i}')
    
    basket.add(file_path, metadata={
        'category': 'test' if i % 2 == 0 else 'demo',
        'index': i
    })
```

## Next Steps

1. ✅ Run all tests to verify functionality
2. ✅ Run benchmarks to verify performance
3. ✅ Check indexes are created
4. ✅ Test with your actual data
5. ✅ Monitor performance in production

