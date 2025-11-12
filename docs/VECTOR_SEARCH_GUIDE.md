# Vector Search and Semantic Search Guide

## Overview

DocEX 2.1.0+ includes vector indexing and semantic search capabilities, enabling you to:
- Generate embeddings for documents using LLM adapters
- Store embeddings in vector databases (pgvector, Pinecone, or in-memory)
- Perform semantic search to find similar documents
- Build RAG (Retrieval-Augmented Generation) applications

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DocEX Document                            │
│                    (Text Content)                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              VectorIndexingProcessor                          │
│  - Generates embeddings using LLM adapter                    │
│  - Stores in vector database                                 │
│  - Updates DocEX metadata                                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    Vector Database                           │
│  - pgvector (PostgreSQL)                                     │
│  - Pinecone (Managed)                                        │
│  - Memory (Testing)                                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              SemanticSearchService                           │
│  - Generates query embeddings                                │
│  - Searches vector database                                  │
│  - Retrieves documents from DocEX                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Index Documents with Vector Embeddings

```python
from docex import DocEX
from docex.processors.llm import OpenAIAdapter
from docex.processors.vector import VectorIndexingProcessor
import asyncio

# Initialize DocEX
docEX = DocEX()
basket = docEX.create_basket('my_basket')

# Add a document
document = basket.add('document.pdf')

# Create LLM adapter for embeddings
llm_adapter = OpenAIAdapter({
    'api_key': os.getenv('OPENAI_API_KEY'),
    'model': 'gpt-4o'
})

# Create vector indexing processor
vector_processor = VectorIndexingProcessor({
    'llm_adapter': llm_adapter,
    'vector_db_type': 'memory',  # or 'pgvector', 'pinecone'
    'store_in_metadata': True
})

# Index the document
result = await vector_processor.process(document)
if result.success:
    print("✅ Document indexed successfully!")
```

### 2. Perform Semantic Search

```python
from docex.processors.vector import SemanticSearchService

# Create search service
search_service = SemanticSearchService(
    doc_ex=docEX,
    llm_adapter=llm_adapter,
    vector_db_type='memory',
    vector_db_config={'vectors': vector_processor.vector_db['vectors']}
)

# Search for similar documents
results = await search_service.search(
    query="What is machine learning?",
    top_k=5,
    basket_id=basket.id
)

# Process results
for result in results:
    print(f"Document: {result.document.name}")
    print(f"Similarity: {result.similarity_score:.4f}")
    print(f"Content preview: {result.document.get_content(mode='text')[:200]}")
```

---

## Vector Database Options

### 1. Memory (Testing/Development)

**Best for:** Testing, development, small datasets

```python
vector_processor = VectorIndexingProcessor({
    'llm_adapter': llm_adapter,
    'vector_db_type': 'memory',
    'store_in_metadata': True
})
```

**Pros:**
- ✅ No setup required
- ✅ Fast for small datasets
- ✅ Good for testing

**Cons:**
- ❌ Not persistent (lost on restart)
- ❌ Doesn't scale beyond memory
- ❌ Not suitable for production

### 2. pgvector (PostgreSQL)

**Best for:** Production with PostgreSQL, ACID transactions, SQL queries

**Setup:**
```sql
-- Install pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column to documents table
ALTER TABLE document ADD COLUMN embedding vector(1536);

-- Create index for similarity search
CREATE INDEX ON document USING ivfflat (embedding vector_cosine_ops);
```

**Usage:**
```python
vector_processor = VectorIndexingProcessor({
    'llm_adapter': llm_adapter,
    'vector_db_type': 'pgvector',
    'vector_db_config': {
        # Uses existing DocEX PostgreSQL connection
    }
})
```

**Pros:**
- ✅ No additional infrastructure
- ✅ ACID transactions
- ✅ SQL queries with joins
- ✅ Stores vectors with document metadata
- ✅ Good performance for < 10M vectors

**Cons:**
- ⚠️ Requires PostgreSQL (not SQLite)
- ⚠️ May struggle with 100M+ vectors

**Installation:**
```bash
pip install pgvector
# Or use optional dependencies:
pip install docex[vector]
```

### 3. Pinecone (Managed Service)

**Best for:** Large-scale production, fully managed solution

**Setup:**
1. Create account at https://www.pinecone.io
2. Get API key
3. Create index

**Usage:**
```python
vector_processor = VectorIndexingProcessor({
    'llm_adapter': llm_adapter,
    'vector_db_type': 'pinecone',
    'vector_db_config': {
        'api_key': os.getenv('PINECONE_API_KEY'),
        'index_name': 'docex-documents',
        'dimension': 1536  # OpenAI embedding dimension
    }
})
```

**Pros:**
- ✅ Fully managed
- ✅ Excellent performance
- ✅ Scales to billions of vectors
- ✅ Production-ready

**Cons:**
- ❌ Cost (~$70/month starter)
- ❌ External dependency
- ❌ No ACID transactions with DocEX

**Installation:**
```bash
pip install pinecone-client
# Or use optional dependencies:
pip install docex[pinecone]
```

---

## Advanced Usage

### Batch Indexing

```python
# Index multiple documents
documents = basket.list()  # Get all documents in basket

for document in documents:
    result = await vector_processor.process(document)
    if result.success:
        print(f"✅ Indexed: {document.name}")
```

### Filtered Search

```python
# Search with metadata filters
results = await search_service.search(
    query="customer support",
    top_k=10,
    basket_id=basket.id,
    filters={
        'category': 'support',
        'status': 'active'
    },
    min_similarity=0.7  # Minimum similarity threshold
)
```

### RAG (Retrieval-Augmented Generation)

```python
# 1. Search for relevant documents
results = await search_service.search(
    query="What are the refund policies?",
    top_k=3
)

# 2. Build context from retrieved documents
context = "\n\n".join([
    result.document.get_content(mode='text')
    for result in results
])

# 3. Use LLM adapter for Q&A with context
llm_adapter = OpenAIAdapter({
    'api_key': os.getenv('OPENAI_API_KEY'),
    'model': 'gpt-4o'
})

answer = await llm_adapter.llm_service.generate_completion(
    prompt=f"""
    Based on the following documents, answer the question:
    
    Documents:
    {context}
    
    Question: What are the refund policies?
    """
)

print(f"Answer: {answer}")
```

---

## Configuration Options

### VectorIndexingProcessor

```python
{
    'llm_adapter': OpenAIAdapter(...),  # Required: LLM adapter instance or config
    'vector_db_type': 'memory',  # 'memory', 'pgvector', or 'pinecone'
    'vector_db_config': {},  # Configuration for vector database
    'store_in_metadata': True,  # Store embeddings in DocEX metadata
    'force_reindex': False  # Re-index even if already indexed
}
```

### SemanticSearchService

```python
{
    'doc_ex': DocEX(),  # Required: DocEX instance
    'llm_adapter': OpenAIAdapter(...),  # Required: LLM adapter
    'vector_db_type': 'memory',  # 'memory', 'pgvector', or 'pinecone'
    'vector_db_config': {}  # Configuration for vector database
}
```

---

## Performance Considerations

### Embedding Generation
- **Cost**: ~$0.0001 per 1K tokens (OpenAI)
- **Time**: ~100-500ms per document
- **Recommendation**: Batch process documents

### Vector Search
- **Memory**: Fast for < 1M vectors
- **pgvector**: Good for < 10M vectors
- **Pinecone**: Excellent for any scale

### Optimization Tips
1. **Index only relevant documents** - Filter before indexing
2. **Use appropriate vector database** - Memory for dev, pgvector/Pinecone for prod
3. **Batch operations** - Process multiple documents together
4. **Cache embeddings** - Store in DocEX metadata for small embeddings

---

## Troubleshooting

### Issue: "pgvector extension not found"
**Solution**: Install pgvector extension in PostgreSQL:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Issue: "Pinecone API key required"
**Solution**: Set `PINECONE_API_KEY` environment variable or provide in config

### Issue: "No vectors found in memory database"
**Solution**: Ensure VectorIndexingProcessor and SemanticSearchService share the same memory database instance

### Issue: Low similarity scores
**Solution**: 
- Check embedding model matches between indexing and search
- Ensure documents have sufficient text content
- Try different embedding models

---

## Examples

See `examples/vector_search_example.py` for a complete working example.

---

## Next Steps

1. **Choose vector database** based on your needs
2. **Index your documents** using VectorIndexingProcessor
3. **Implement semantic search** using SemanticSearchService
4. **Build RAG applications** combining search with LLM adapters

---

**Last Updated**: 2024-11-12  
**Version**: 2.1.0

