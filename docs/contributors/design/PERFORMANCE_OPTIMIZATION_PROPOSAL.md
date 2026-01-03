# Performance Optimization Proposal for DocEX 2.8.3

## Overview

This document outlines performance improvements for basket and document operations, focusing on search, list, and query operations that support both `basket_id` and `basket_name` while prioritizing `basket_id` for efficiency.

## Current State Analysis

### Basket Operations

**Current Implementation:**
- `DocBasket.get(basket_id)` - Primary key lookup (O(1), very fast)
- `DocBasket.find_by_name(name)` - Unique constraint index lookup (O(log n), fast)
- `DocBasket.list()` - Full table scan (O(n), can be slow for many baskets)

**Indexes:**
- ✅ Primary key on `id` (automatic)
- ✅ Unique constraint on `name` (creates index automatically)
- ❌ No index on `status` (for filtering active baskets)
- ❌ No composite indexes for common queries

### Document Operations

**Current Implementation:**
- All document queries use `basket_id` (foreign key, indexed)
- Composite indexes exist for:
  - `idx_document_basket_status` - (basket_id, status)
  - `idx_document_basket_type` - (basket_id, document_type)
  - `idx_document_basket_created` - (basket_id, created_at DESC)
  - `idx_document_basket_updated` - (basket_id, updated_at DESC)
  - `idx_document_basket_name` - (basket_id, name)

**Performance:**
- ✅ Good: Document queries are well-indexed
- ⚠️  Concern: Metadata queries can be slow for large datasets
- ⚠️  Concern: No covering indexes for common column projections

## Performance Improvement Recommendations

### 1. Basket Query Optimization

#### 1.1 Support Both basket_id and basket_name

**Strategy:** Always prefer `basket_id` when available, fallback to `basket_name` lookup.

**Implementation:**
```python
def get_basket(basket_id: Optional[str] = None, basket_name: Optional[str] = None) -> Optional['DocBasket']:
    """
    Get basket by ID (preferred) or name (fallback).
    
    Performance:
    - basket_id: O(1) primary key lookup (fastest)
    - basket_name: O(log n) unique index lookup (fast, but slower than ID)
    
    Args:
        basket_id: Basket ID (preferred for performance)
        basket_name: Basket name (fallback if ID not provided)
        
    Returns:
        DocBasket instance or None
    """
    if basket_id:
        return DocBasket.get(basket_id)  # Fast: primary key lookup
    elif basket_name:
        return DocBasket.find_by_name(basket_name)  # Fast: unique index lookup
    else:
        raise ValueError("Either basket_id or basket_name must be provided")
```

#### 1.2 Add Basket Status Index

**Purpose:** Optimize filtering active/inactive baskets

**Index:**
```sql
CREATE INDEX IF NOT EXISTS idx_docbasket_status ON docbasket(status);
```

**Use Case:**
- `list_baskets(status='active')` - Fast filtering
- `count_baskets(status='active')` - Fast counting

#### 1.3 Optimize Basket Listing

**Current:** Full table scan
**Improved:** Use indexed queries with pagination

```python
def list_baskets(
    status: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    order_by: str = 'created_at',
    order_desc: bool = True
) -> List['DocBasket']:
    """
    List baskets with filtering, pagination, and sorting.
    Optimized with proper indexes.
    """
    query = select(DocBasketModel)
    
    if status:
        query = query.where(DocBasketModel.status == status)  # Uses idx_docbasket_status
    
    # Add sorting (consider adding index on created_at if needed)
    if order_by == 'created_at':
        query = query.order_by(DocBasketModel.created_at.desc() if order_desc else DocBasketModel.created_at.asc())
    elif order_by == 'name':
        query = query.order_by(DocBasketModel.name.asc() if not order_desc else DocBasketModel.name.desc())
    
    # Add pagination
    if limit:
        query = query.limit(limit)
    if offset:
        query = query.offset(offset)
    
    # Execute with index support
    return session.execute(query).scalars().all()
```

### 2. Document Query Optimization

#### 2.1 Ensure basket_id is Always Used

**Principle:** All document queries should use `basket_id` (foreign key) for maximum performance.

**Current State:** ✅ Already implemented correctly

**Recommendation:** Add validation to ensure basket_id is always provided:
```python
def list_documents(
    basket_id: Optional[str] = None,
    basket_name: Optional[str] = None,
    ...
) -> List['Document']:
    """
    List documents with basket_id (preferred) or basket_name (fallback).
    
    Performance:
    - basket_id: Uses foreign key index directly (fastest)
    - basket_name: Requires basket lookup first, then document query (slower)
    """
    # Resolve basket_id from name if needed
    if basket_name and not basket_id:
        basket = DocBasket.find_by_name(basket_name)
        if not basket:
            return []
        basket_id = basket.id
    
    if not basket_id:
        raise ValueError("Either basket_id or basket_name must be provided")
    
    # Use basket_id for query (fast, indexed)
    query = select(DocumentModel).where(DocumentModel.basket_id == basket_id)
    ...
```

#### 2.2 Add Covering Indexes for Common Queries

**Purpose:** Allow index-only scans for frequently accessed columns

**Indexes:**
```sql
-- Covering index for list_documents_with_metadata with common columns
CREATE INDEX IF NOT EXISTS idx_document_basket_covering_list 
ON document(basket_id, status, document_type, created_at DESC) 
INCLUDE (id, name, size);

-- Covering index for document search by name
CREATE INDEX IF NOT EXISTS idx_document_basket_name_covering 
ON document(basket_id, name) 
INCLUDE (id, document_type, status, created_at);
```

**Note:** PostgreSQL supports INCLUDE, SQLite doesn't. For SQLite, use composite index:
```sql
CREATE INDEX IF NOT EXISTS idx_document_basket_covering_list 
ON document(basket_id, status, document_type, created_at DESC, id, name, size);
```

#### 2.3 Optimize Metadata Queries

**Current:** Uses `idx_document_metadata_key_value` (good)
**Improvement:** Add composite index with document_id for faster joins

```sql
-- Composite index for metadata queries with document_id
CREATE INDEX IF NOT EXISTS idx_document_metadata_doc_key_value 
ON document_metadata(document_id, key, value);
```

### 3. Unified Query Interface

#### 3.1 Create Unified Basket+Document Query Methods

**Purpose:** Provide efficient methods that support both basket_id and basket_name

```python
class DocEX:
    def get_basket(self, basket_id: Optional[str] = None, basket_name: Optional[str] = None) -> Optional['DocBasket']:
        """
        Get basket by ID (preferred) or name (fallback).
        
        Performance:
        - basket_id: O(1) primary key lookup
        - basket_name: O(log n) unique index lookup
        """
        if basket_id:
            return DocBasket.get(basket_id, db=self.db)
        elif basket_name:
            return DocBasket.find_by_name(basket_name, db=self.db)
        else:
            raise ValueError("Either basket_id or basket_name must be provided")
    
    def list_documents(
        self,
        basket_id: Optional[str] = None,
        basket_name: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> List['Document']:
        """
        List documents with basket_id (preferred) or basket_name (fallback).
        
        Performance:
        - basket_id: Direct foreign key lookup (fastest)
        - basket_name: Basket lookup + document query (slower, but acceptable)
        """
        # Resolve basket_id
        basket = self.get_basket(basket_id=basket_id, basket_name=basket_name)
        if not basket:
            return []
        
        # Use basket_id for document query (fast, indexed)
        return basket.list_documents(
            limit=limit,
            offset=offset,
            filters=filters,
            order_by=order_by,
            order_desc=order_desc
        )
```

### 4. Caching Strategy (Optional)

#### 4.1 Basket Name-to-ID Cache

**Purpose:** Avoid repeated name lookups for frequently accessed baskets

**Implementation:**
```python
from functools import lru_cache
from typing import Optional

class BasketNameCache:
    """Simple LRU cache for basket name -> ID mapping"""
    
    @staticmethod
    @lru_cache(maxsize=1000)
    def get_basket_id_by_name(name: str, tenant_id: Optional[str] = None) -> Optional[str]:
        """
        Get basket ID by name with caching.
        
        Cache key includes tenant_id for multi-tenant support.
        """
        basket = DocBasket.find_by_name(name)
        return basket.id if basket else None
```

**Trade-offs:**
- ✅ Reduces database queries for repeated name lookups
- ⚠️  Cache invalidation needed when baskets are created/deleted/renamed
- ⚠️  Memory overhead (minimal with LRU cache)

**Recommendation:** Implement only if profiling shows name lookups are a bottleneck.

### 5. Index Creation Strategy

#### 5.1 Required Indexes

**Basket Indexes:**
```sql
-- Status index for filtering
CREATE INDEX IF NOT EXISTS idx_docbasket_status ON docbasket(status);

-- Created_at index for sorting (if not already covered by primary key)
CREATE INDEX IF NOT EXISTS idx_docbasket_created_at ON docbasket(created_at DESC);
```

**Document Indexes (already exist, verify):**
```sql
-- Verify these indexes exist:
-- idx_documents_basket_id (foreign key index, usually automatic)
-- idx_document_basket_status
-- idx_document_basket_type
-- idx_document_basket_created
-- idx_document_basket_updated
-- idx_document_basket_name
```

**Metadata Indexes:**
```sql
-- Composite index for faster metadata queries
CREATE INDEX IF NOT EXISTS idx_document_metadata_doc_key_value 
ON document_metadata(document_id, key, value);
```

#### 5.2 Index Maintenance

**Strategy:**
- Create indexes during tenant provisioning (already implemented)
- Verify indexes exist in existing installations
- Add migration script for existing databases

### 6. Query Optimization Patterns

#### 6.1 Always Use basket_id When Available

**Pattern:**
```python
# ✅ GOOD: Use basket_id directly
basket = DocBasket.get(basket_id)
documents = basket.list_documents()

# ⚠️  ACCEPTABLE: Use basket_name (requires lookup first)
basket = DocBasket.find_by_name(basket_name)
documents = basket.list_documents()

# ❌ BAD: Don't query documents without basket context
documents = Document.query().all()  # Full table scan!
```

#### 6.2 Use Efficient Column Projection

**Pattern:**
```python
# ✅ GOOD: Use list_documents_with_metadata for lightweight queries
documents = basket.list_documents_with_metadata(
    columns=['id', 'name', 'status'],
    limit=100
)

# ⚠️  ACCEPTABLE: Use list_documents for full objects (heavier)
documents = basket.list_documents(limit=100)
```

#### 6.3 Leverage Composite Indexes

**Pattern:**
```python
# ✅ GOOD: Filter by basket_id + status (uses idx_document_basket_status)
documents = basket.list_documents(status='RECEIVED')

# ✅ GOOD: Filter by basket_id + document_type (uses idx_document_basket_type)
documents = basket.list_documents(document_type='invoice')

# ✅ GOOD: Sort by basket_id + created_at (uses idx_document_basket_created)
documents = basket.list_documents(order_by='created_at', order_desc=True)
```

### 7. Performance Benchmarks

#### Expected Improvements

| Operation | Current | Optimized | Improvement |
|-----------|---------|-----------|-------------|
| Get basket by ID | ~1ms | ~1ms | No change (already optimal) |
| Get basket by name | ~2ms | ~2ms | No change (already optimal) |
| List baskets (1000) | ~50ms | ~10ms | 5x faster (with status index) |
| List documents (10k) | ~200ms | ~50ms | 4x faster (with covering index) |
| List documents with filter | ~150ms | ~30ms | 5x faster (composite index) |
| Find by metadata (1k docs) | ~100ms | ~20ms | 5x faster (optimized metadata index) |

*Note: Actual performance depends on database type, hardware, and data distribution*

## Implementation Plan

### Phase 1: Index Creation (High Priority)
1. Add `idx_docbasket_status` index
2. Add `idx_document_metadata_doc_key_value` index
3. Create migration script for existing databases
4. Verify indexes are created during tenant provisioning

### Phase 2: Unified Query Interface (Medium Priority)
1. Add `get_basket(basket_id=None, basket_name=None)` method
2. Add `list_documents(basket_id=None, basket_name=None, ...)` method
3. Update documentation with performance recommendations

### Phase 3: Query Optimization (Medium Priority)
1. Optimize `list_baskets()` with filtering and pagination
2. Add covering indexes for common queries (PostgreSQL)
3. Optimize metadata query patterns

### Phase 4: Caching (Low Priority - Optional)
1. Implement basket name-to-ID cache (if profiling shows need)
2. Add cache invalidation on basket create/update/delete
3. Make caching configurable

## Code Examples

### Example 1: Efficient Basket Access

```python
from docex import DocEX
from docex.context import UserContext

docex = DocEX(user_context=UserContext(user_id='user1', tenant_id='acme_corp'))

# ✅ PREFERRED: Use basket_id (fastest)
basket = docex.get_basket(basket_id='bas_1234567890abcdef')
documents = basket.list_documents(limit=100)

# ⚠️  ACCEPTABLE: Use basket_name (requires lookup first)
basket = docex.get_basket(basket_name='invoice_raw')
documents = basket.list_documents(limit=100)
```

### Example 2: Efficient Document Listing

```python
# ✅ PREFERRED: Use basket_id directly
basket = docex.get_basket(basket_id='bas_1234567890abcdef')
documents = basket.list_documents_with_metadata(
    columns=['id', 'name', 'status', 'created_at'],
    filters={'status': 'RECEIVED'},
    limit=100,
    order_by='created_at',
    order_desc=True
)

# ⚠️  ACCEPTABLE: Use basket_name (lookup + query)
basket = docex.get_basket(basket_name='invoice_raw')
documents = basket.list_documents_with_metadata(
    columns=['id', 'name', 'status'],
    limit=100
)
```

### Example 3: Efficient Search Operations

```python
# ✅ GOOD: Use basket_id for document search
basket = docex.get_basket(basket_id='bas_1234567890abcdef')
results = basket.find_documents_by_metadata(
    metadata={'invoice_number': 'INV-001'},
    limit=10
)

# ✅ GOOD: Use efficient listing with filters
results = basket.list_documents_with_metadata(
    columns=['id', 'name', 'document_type'],
    filters={'document_type': 'invoice', 'status': 'RECEIVED'},
    limit=50
)
```

## Migration Guide

### For Existing Installations

1. **Add Missing Indexes:**
```bash
# Run migration script
psql -d your_database -f docex/db/migrations/003_add_basket_performance_indexes.sql
```

2. **Verify Indexes:**
```python
from docex.db.connection import Database
from sqlalchemy import inspect, text

db = Database()
inspector = inspect(db.get_engine())

# Check basket indexes
basket_indexes = inspector.get_indexes('docbasket')
print("Basket indexes:", [idx['name'] for idx in basket_indexes])

# Check document indexes
doc_indexes = inspector.get_indexes('document')
print("Document indexes:", [idx['name'] for idx in doc_indexes])
```

## Conclusion

The key performance principles are:
1. **Always prefer `basket_id` over `basket_name`** - Primary key lookups are O(1) vs O(log n)
2. **Use composite indexes** - Leverage (basket_id, status), (basket_id, type) for filtered queries
3. **Use column projection** - `list_documents_with_metadata()` for lightweight queries
4. **Add missing indexes** - Status index for baskets, covering indexes for documents
5. **Support both ID and name** - But guide users to prefer ID for performance

