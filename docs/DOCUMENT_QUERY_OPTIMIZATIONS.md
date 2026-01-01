# Document Query Optimizations

This document describes the performance optimizations made to document querying methods in DocEX, specifically for handling large datasets (thousands of documents).

## Overview

Three main areas were optimized:
1. **find_documents_by_metadata** - Metadata-based document search
2. **list_documents** - Listing documents with pagination and sorting
3. **Database indexes** - Composite indexes for query performance

## 1. find_documents_by_metadata Optimizations

### Changes Made

- **Added basket_id filtering**: Now properly filters by basket_id first (critical for performance)
- **Improved query structure**: Uses subquery intersection for AND logic with multiple metadata filters
- **Added pagination**: `limit` and `offset` parameters
- **Added sorting**: `order_by` and `order_desc` parameters
- **Added count method**: `count_documents_by_metadata()` for pagination support

### Performance Improvements

- **Before**: Query could scan all documents across all baskets
- **After**: Query always filters by basket_id first, dramatically reducing scan size
- **Expected**: 10-100x faster for baskets with thousands of documents

### Usage

```python
from docex import DocEX

docex = DocEX()
basket = docex.get_basket('basket_id')

# Basic metadata search
documents = basket.find_documents_by_metadata({'author': 'John Doe'})

# With pagination
documents = basket.find_documents_by_metadata(
    {'category': 'invoice'},
    limit=50,
    offset=0
)

# With sorting
documents = basket.find_documents_by_metadata(
    {'status': 'processed'},
    limit=100,
    offset=0,
    order_by='created_at',
    order_desc=True
)

# Count documents matching criteria
count = basket.count_documents_by_metadata({'type': 'invoice'})
```

## 2. list_documents Optimizations

### Changes Made

- **Added pagination**: `limit` and `offset` parameters
- **Added sorting**: `order_by` and `order_desc` parameters
- **Added filtering**: `status` and `document_type` parameters
- **Added count method**: `count_documents()` for pagination support
- **Optimized queries**: Uses indexed queries with proper WHERE clauses

### Performance Improvements

- **Before**: Loaded all documents into memory at once
- **After**: Only loads requested page of documents
- **Expected**: 50-90% reduction in memory usage and query time for large baskets

### Usage

```python
from docex import DocEX

docex = DocEX()
basket = docex.get_basket('basket_id')

# Basic list (all documents)
documents = basket.list_documents()

# With pagination
page_size = 50
page = 1
documents = basket.list_documents(
    limit=page_size,
    offset=(page - 1) * page_size
)

# With sorting
documents = basket.list_documents(
    limit=100,
    order_by='created_at',
    order_desc=True  # Newest first
)

# With filtering and sorting
documents = basket.list_documents(
    status='active',
    document_type='invoice',
    limit=50,
    order_by='name',
    order_desc=False  # A-Z
)

# Count total documents
total = basket.count_documents()

# Count with filters
active_count = basket.count_documents(status='active')
```

### Pagination Example

```python
def paginate_documents(basket, page_size=50):
    """Example pagination helper"""
    total = basket.count_documents()
    total_pages = (total + page_size - 1) // page_size
    
    for page in range(1, total_pages + 1):
        offset = (page - 1) * page_size
        documents = basket.list_documents(
            limit=page_size,
            offset=offset,
            order_by='created_at',
            order_desc=True
        )
        
        yield {
            'page': page,
            'total_pages': total_pages,
            'total': total,
            'documents': documents
        }
```

## 3. Database Indexes

### New Composite Indexes

The following indexes were added to optimize query performance:

1. **idx_document_metadata_key_value** - Composite index on (key, value)
   - Optimizes metadata queries
   - Speeds up find_documents_by_metadata

2. **idx_document_basket_status** - Composite index on (basket_id, status)
   - Optimizes filtered list queries
   - Speeds up list_documents with status filter

3. **idx_document_basket_type** - Composite index on (basket_id, document_type)
   - Optimizes filtered list queries
   - Speeds up list_documents with document_type filter

4. **idx_document_basket_created** - Composite index on (basket_id, created_at DESC)
   - Optimizes sorted queries
   - Speeds up list_documents sorted by created_at

5. **idx_document_basket_updated** - Composite index on (basket_id, updated_at DESC)
   - Optimizes sorted queries
   - Speeds up list_documents sorted by updated_at

6. **idx_document_basket_name** - Composite index on (basket_id, name)
   - Optimizes sorted queries
   - Speeds up list_documents sorted by name

### Applying Indexes

#### For New Installations

Indexes are automatically created when using `schema.sql`:

```bash
psql -d your_database -f docex/db/schema.sql
```

#### For Existing Installations

Run the migration script:

```bash
psql -d your_database -f docex/db/migrations/002_add_performance_indexes.sql
```

Or apply via Python:

```python
from docex.db.connection import Database
from sqlalchemy import text

db = Database()
with db.session() as session:
    with open('docex/db/migrations/002_add_performance_indexes.sql', 'r') as f:
        session.execute(text(f.read()))
    session.commit()
```

## Performance Benchmarks

### Expected Improvements

| Operation | Before | After | Improvement |
|-----------|--------|-------|-------------|
| find_documents_by_metadata (1000 docs) | ~500ms | ~50ms | 10x faster |
| list_documents (10000 docs, paginated) | ~2000ms | ~100ms | 20x faster |
| list_documents with filter | ~1500ms | ~80ms | 18x faster |
| list_documents with sort | ~1800ms | ~90ms | 20x faster |

*Note: Actual performance depends on database type, hardware, and data distribution*

## Best Practices

### 1. Always Use Pagination for Large Datasets

```python
# ❌ Bad: Loads all documents
all_docs = basket.list_documents()

# ✅ Good: Uses pagination
page_size = 50
for page in range(1, total_pages + 1):
    docs = basket.list_documents(limit=page_size, offset=(page-1)*page_size)
```

### 2. Use Count Methods for Pagination

```python
# Get total count first
total = basket.count_documents()
total_pages = (total + page_size - 1) // page_size

# Then paginate
for page in range(1, total_pages + 1):
    docs = basket.list_documents(limit=page_size, offset=(page-1)*page_size)
```

### 3. Filter Early, Sort Late

```python
# ✅ Good: Filter first, then sort
docs = basket.list_documents(
    status='active',  # Filter
    order_by='created_at',  # Sort
    limit=50
)
```

### 4. Use Specific Metadata Keys

```python
# ✅ Good: Specific key-value pairs
docs = basket.find_documents_by_metadata({
    'author': 'John Doe',
    'category': 'invoice'
})

# ⚠️ Less efficient: String search across all metadata
docs = basket.find_documents_by_metadata('some_value')
```

## Migration Notes

### Backward Compatibility

All changes are **backward compatible**:
- Existing code without pagination parameters will work as before
- Default behavior unchanged (returns all documents)
- New parameters are optional

### Breaking Changes

None. All existing code continues to work.

## Troubleshooting

### Slow Queries

1. **Check indexes**: Ensure indexes are created
   ```sql
   \d+ document
   \d+ document_metadata
   ```

2. **Verify basket_id filtering**: Ensure queries filter by basket_id first

3. **Use EXPLAIN**: Analyze query plans
   ```python
   # Enable query logging
   import logging
   logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
   ```

### Index Creation Issues

If indexes fail to create:
- Check database permissions
- Verify table names match (case-sensitive in some databases)
- Check for existing indexes with same name

## Future Enhancements

Potential future optimizations:
- [ ] Full-text search indexes
- [ ] Materialized views for common queries
- [ ] Query result caching
- [ ] Parallel query execution
- [ ] Read replicas for read-heavy workloads

