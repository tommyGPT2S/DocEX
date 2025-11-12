# Vector Database Recommendation for DocEX

## Quick Answer: **Yes, pgvector is an excellent choice for DocEX!**

Given that DocEX already uses PostgreSQL, **pgvector is highly recommended** because it:
- ✅ Requires **no additional infrastructure**
- ✅ Stores vectors **alongside document metadata** in the same database
- ✅ Supports **ACID transactions** (consistency with DocEX operations)
- ✅ Enables **SQL queries** (join with documents, metadata, operations)
- ✅ Provides **good performance** for small to medium datasets
- ✅ Offers **simple integration** with DocEX's existing database

---

## Detailed Comparison

### 1. pgvector (PostgreSQL Extension) ⭐ **RECOMMENDED**

**Best for:** DocEX projects using PostgreSQL, small to medium datasets, transactional consistency

**Pros:**
- ✅ **No additional infrastructure** - Uses existing PostgreSQL
- ✅ **ACID transactions** - Vectors stored with document metadata atomically
- ✅ **SQL queries** - Join vectors with documents, metadata, operations
- ✅ **Simple integration** - Just add a column to existing tables
- ✅ **Cost-effective** - No additional service costs
- ✅ **Good performance** - Suitable for up to millions of vectors
- ✅ **Mature and stable** - Well-tested PostgreSQL extension

**Cons:**
- ⚠️ **PostgreSQL only** - Requires PostgreSQL (not SQLite)
- ⚠️ **Scaling limits** - May struggle with 100M+ vectors
- ⚠️ **No specialized features** - Lacks some advanced vector DB features

**Performance:**
- Good for: < 10M vectors
- Acceptable for: 10M - 100M vectors
- May struggle with: > 100M vectors

**Integration with DocEX:**
```python
# Add vector column to documents table
ALTER TABLE documents ADD COLUMN embedding vector(1536);

# Create index for similarity search
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops);

# Query with SQL
SELECT id, name, embedding <=> %s AS distance
FROM documents
WHERE basket_id = %s
ORDER BY embedding <=> %s
LIMIT 10;
```

**Cost:** Free (PostgreSQL extension)

---

### 2. Pinecone (Managed Service)

**Best for:** Large-scale production, fully managed solution, high performance requirements

**Pros:**
- ✅ **Fully managed** - No infrastructure to manage
- ✅ **Excellent performance** - Optimized for large-scale vector search
- ✅ **Easy to use** - Simple API
- ✅ **Scalable** - Handles billions of vectors
- ✅ **Production-ready** - Built for production workloads

**Cons:**
- ❌ **Cost** - ~$70/month for starter, scales with usage
- ❌ **External dependency** - Requires internet connection
- ❌ **Vendor lock-in** - Proprietary service
- ❌ **No ACID transactions** - Separate from DocEX database
- ❌ **Additional infrastructure** - Another service to manage

**Performance:**
- Excellent for: Any scale
- Optimized for: Large-scale production

**Integration with DocEX:**
```python
import pinecone

# Separate service, requires sync with DocEX
pinecone.init(api_key="...")
index = pinecone.Index("docex-documents")

# Index document
index.upsert(vectors=[{
    'id': document.id,
    'values': embedding,
    'metadata': {'document_id': document.id, 'basket_id': document.basket_id}
}])

# Search (separate from DocEX database)
results = index.query(vector=query_embedding, top_k=10)
```

**Cost:** ~$70/month (starter), scales with usage

---

### 3. Weaviate (Open Source)

**Best for:** Self-hosted, advanced features, GraphQL API

**Pros:**
- ✅ **Open source** - Free and self-hosted
- ✅ **Advanced features** - GraphQL, hybrid search, etc.
- ✅ **Good performance** - Handles large datasets
- ✅ **Flexible** - Many configuration options

**Cons:**
- ❌ **Additional infrastructure** - Requires separate service
- ❌ **Complex setup** - More complex than pgvector
- ❌ **No ACID transactions** - Separate from DocEX database
- ❌ **Operational overhead** - Need to manage and maintain

**Performance:**
- Good for: Medium to large datasets
- Suitable for: Production workloads

**Integration with DocEX:**
```python
import weaviate

# Separate service
client = weaviate.Client("http://localhost:8080")

# Index document (separate from DocEX)
client.data_object.create({
    'document_id': document.id,
    'basket_id': document.basket_id,
    'embedding': embedding
}, "Document")

# Search (separate from DocEX database)
results = client.query.get("Document", ["document_id"]).with_near_vector({
    "vector": query_embedding
}).do()
```

**Cost:** Free (self-hosted), but requires infrastructure

---

### 4. Qdrant (Open Source)

**Best for:** Self-hosted, high performance, Rust-based

**Pros:**
- ✅ **Open source** - Free and self-hosted
- ✅ **High performance** - Rust-based, very fast
- ✅ **Good features** - Filtering, hybrid search
- ✅ **Docker-friendly** - Easy to deploy

**Cons:**
- ❌ **Additional infrastructure** - Requires separate service
- ❌ **No ACID transactions** - Separate from DocEX database
- ❌ **Operational overhead** - Need to manage and maintain

**Performance:**
- Excellent for: High-performance requirements
- Suitable for: Production workloads

**Cost:** Free (self-hosted), but requires infrastructure

---

### 5. Chroma (Open Source)

**Best for:** Development, prototyping, Python-native

**Pros:**
- ✅ **Open source** - Free
- ✅ **Python-native** - Easy Python integration
- ✅ **Simple** - Easy to get started
- ✅ **Good for dev** - Great for development

**Cons:**
- ❌ **Not production-ready** - May not scale well
- ❌ **Additional infrastructure** - Requires separate service
- ❌ **No ACID transactions** - Separate from DocEX database

**Performance:**
- Good for: Development and small datasets
- May struggle with: Large-scale production

**Cost:** Free, but not recommended for production

---

## Recommendation Matrix

| Use Case | Recommended | Why |
|----------|------------|-----|
| **DocEX with PostgreSQL** | **pgvector** ⭐ | No additional infrastructure, ACID transactions, SQL queries |
| **Small to medium datasets** | **pgvector** ⭐ | Simple, cost-effective, good performance |
| **Large-scale production** | **Pinecone** or **Weaviate** | Better performance, scalability |
| **Self-hosted, advanced features** | **Weaviate** | Open source, GraphQL, hybrid search |
| **High performance requirements** | **Qdrant** | Rust-based, very fast |
| **Development/prototyping** | **Chroma** or **pgvector** | Easy to get started |

---

## Recommended Approach for DocEX

### Phase 1: Start with pgvector (Recommended)

**Why:**
1. DocEX already uses PostgreSQL
2. No additional infrastructure needed
3. Vectors stored alongside document metadata
4. ACID transactions ensure consistency
5. SQL queries join vectors with documents
6. Simple integration

**Implementation:**
```python
# 1. Install pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

# 2. Add embedding column to documents table
ALTER TABLE documents ADD COLUMN embedding vector(1536);

# 3. Create index for similarity search
CREATE INDEX documents_embedding_idx ON documents 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

# 4. Use in DocEX processor
class VectorIndexingProcessor(BaseProcessor):
    async def process(self, document: Document) -> ProcessingResult:
        # Generate embedding
        embedding = self.llm_adapter.generate_embedding(text)
        
        # Store in same database as document
        with self.db.transaction() as session:
            session.execute(
                update(DocumentModel)
                .where(DocumentModel.id == document.id)
                .values(embedding=embedding)
            )
            session.commit()
        
        return ProcessingResult(success=True)
```

**Benefits:**
- ✅ Vectors stored with documents (same transaction)
- ✅ Query documents and vectors together
- ✅ No additional service to manage
- ✅ Cost-effective

### Phase 2: Migrate to Pinecone/Weaviate (If Needed)

**When to migrate:**
- Dataset exceeds 100M vectors
- Performance becomes a bottleneck
- Need advanced features (hybrid search, etc.)
- Need fully managed solution

**Migration strategy:**
- Keep pgvector for transactional consistency
- Use Pinecone/Weaviate for large-scale search
- Sync between systems

---

## Implementation Example: pgvector with DocEX

### 1. Database Schema

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column to documents table
ALTER TABLE documents ADD COLUMN embedding vector(1536);

-- Create index for similarity search
CREATE INDEX documents_embedding_idx ON documents 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Create index for metadata filtering
CREATE INDEX documents_basket_id_idx ON documents(basket_id);
CREATE INDEX documents_status_idx ON documents(status);
```

### 2. DocEX Processor

```python
from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document
from docex.db.models import Document as DocumentModel
from sqlalchemy import update
from pgvector.sqlalchemy import Vector

class VectorIndexingProcessor(BaseProcessor):
    """DocEX processor that indexes documents in pgvector"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.llm_adapter = OpenAIAdapter(config)
        self.embedding_dim = config.get('embedding_dim', 1536)
    
    def can_process(self, document: Document) -> bool:
        # Process all documents for indexing
        return True
    
    async def process(self, document: Document) -> ProcessingResult:
        """Index document in pgvector - DocEX tracks this operation"""
        try:
            # Get content via DocEX
            text = self.get_document_text(document)
            
            # Generate embedding
            embedding = self.llm_adapter.generate_embedding(text)
            
            # Store in same database as document (ACID transaction)
            with self.db.transaction() as session:
                session.execute(
                    update(DocumentModel)
                    .where(DocumentModel.id == document.id)
                    .values(embedding=embedding)
                )
                session.commit()
            
            # Update DocEX metadata
            from docex.services.metadata_service import MetadataService
            MetadataService().update_metadata(document.id, {
                'vector_indexed': True,
                'embedding_model': self.llm_adapter.model,
                'embedding_dim': self.embedding_dim
            })
            
            return ProcessingResult(success=True, metadata={'vector_indexed': True})
        except Exception as e:
            return ProcessingResult(success=False, error=str(e))
```

### 3. Semantic Search Service

```python
from docex import DocEX
from sqlalchemy import select, func
from pgvector.sqlalchemy import Vector

class SemanticSearchService:
    """Semantic search using pgvector and DocEX"""
    
    def __init__(self, doc_ex: DocEX, llm_adapter):
        self.doc_ex = doc_ex
        self.llm_adapter = llm_adapter
        self.db = doc_ex.db
    
    def search(self, query: str, basket_id: str = None, top_k: int = 10):
        """Semantic search using pgvector"""
        # 1. Generate query embedding
        query_embedding = self.llm_adapter.generate_embedding(query)
        
        # 2. Search in same database as documents
        with self.db.transaction() as session:
            query_stmt = select(
                DocumentModel.id,
                DocumentModel.name,
                DocumentModel.basket_id,
                func.cosine_distance(DocumentModel.embedding, query_embedding).label('distance')
            ).where(
                DocumentModel.embedding.isnot(None)
            )
            
            if basket_id:
                query_stmt = query_stmt.where(DocumentModel.basket_id == basket_id)
            
            query_stmt = query_stmt.order_by(
                func.cosine_distance(DocumentModel.embedding, query_embedding)
            ).limit(top_k)
            
            results = session.execute(query_stmt).all()
        
        # 3. Retrieve full documents via DocEX
        documents = []
        for result in results:
            basket = self.doc_ex.get_basket_by_id(result.basket_id)
            doc = basket.get_document(result.id)
            documents.append({
                'document': doc,
                'relevance_score': 1 - result.distance,  # Convert distance to similarity
                'distance': result.distance
            })
        
        return documents
```

### 4. Hybrid Search (Vector + Metadata)

```python
def hybrid_search(self, query: str, filters: Dict = None, top_k: int = 10):
    """Hybrid search: vector similarity + metadata filtering"""
    # 1. Generate query embedding
    query_embedding = self.llm_adapter.generate_embedding(query)
    
    # 2. Build query with metadata filters
    with self.db.transaction() as session:
        query_stmt = select(
            DocumentModel.id,
            DocumentModel.basket_id,
            func.cosine_distance(DocumentModel.embedding, query_embedding).label('distance')
        ).where(
            DocumentModel.embedding.isnot(None)
        )
        
        # Add metadata filters
        if filters:
            # Join with document_metadata table
            from docex.db.models import DocumentMetadata
            query_stmt = query_stmt.join(
                DocumentMetadata,
                DocumentMetadata.document_id == DocumentModel.id
            )
            
            for key, value in filters.items():
                query_stmt = query_stmt.where(
                    DocumentMetadata.key == key,
                    DocumentMetadata.value == str(value)
                )
        
        query_stmt = query_stmt.order_by(
            func.cosine_distance(DocumentModel.embedding, query_embedding)
        ).limit(top_k)
        
        results = session.execute(query_stmt).all()
    
    # 3. Retrieve documents via DocEX
    return [self._get_document(result) for result in results]
```

---

## Performance Considerations

### pgvector Performance

**Index Types:**
1. **ivfflat** (Inverted File Index) - Fast, approximate
   - Good for: < 10M vectors
   - Lists parameter: `sqrt(rows)` for optimal performance

2. **hnsw** (Hierarchical Navigable Small World) - Very fast, approximate
   - Good for: 10M - 100M vectors
   - Better accuracy than ivfflat

**Optimization Tips:**
```sql
-- For ivfflat index
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);  -- Adjust based on dataset size

-- For hnsw index (better for larger datasets)
CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);
```

**When to use each:**
- **ivfflat**: < 10M vectors, faster index creation
- **hnsw**: 10M+ vectors, better query performance

---

## Migration Path

### Start with pgvector → Migrate if Needed

1. **Phase 1: pgvector** (Recommended starting point)
   - Simple integration
   - No additional infrastructure
   - Good for most use cases

2. **Phase 2: Evaluate** (When dataset grows)
   - Monitor performance
   - Measure query latency
   - Track index size

3. **Phase 3: Migrate** (If needed)
   - Consider Pinecone for managed solution
   - Consider Weaviate for self-hosted
   - Keep pgvector for transactional consistency

---

## Final Recommendation

### For DocEX: **Start with pgvector** ⭐

**Reasons:**
1. ✅ DocEX already uses PostgreSQL
2. ✅ No additional infrastructure needed
3. ✅ Vectors stored alongside document metadata
4. ✅ ACID transactions ensure consistency
5. ✅ SQL queries join vectors with documents
6. ✅ Simple integration
7. ✅ Cost-effective
8. ✅ Good performance for most use cases

**When to consider alternatives:**
- Dataset exceeds 100M vectors → Consider Pinecone or Weaviate
- Need fully managed solution → Consider Pinecone
- Need advanced features → Consider Weaviate
- Need maximum performance → Consider Qdrant

---

## Next Steps

1. **Install pgvector extension**
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

2. **Add embedding column to documents table**
   ```sql
   ALTER TABLE documents ADD COLUMN embedding vector(1536);
   ```

3. **Create index for similarity search**
   ```sql
   CREATE INDEX documents_embedding_idx ON documents 
   USING ivfflat (embedding vector_cosine_ops) 
   WITH (lists = 100);
   ```

4. **Implement VectorIndexingProcessor** (see example above)

5. **Implement SemanticSearchService** (see example above)

6. **Test and optimize** based on your dataset size

---

**See Also:**
- `docs/LLM_ADAPTER_PROPOSAL.md` - LLM adapter implementation plan
- `docs/DOCEX_LEVERAGE_SUMMARY.md` - DocEX features to leverage
- pgvector documentation: https://github.com/pgvector/pgvector

